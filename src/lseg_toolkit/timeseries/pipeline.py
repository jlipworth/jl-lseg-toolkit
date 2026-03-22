"""
Time series extraction pipeline.

Orchestrates fetching, processing, and storage of time series data.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from lseg_toolkit.client import SessionManager
from lseg_toolkit.timeseries.client import get_client
from lseg_toolkit.timeseries.config import TimeSeriesConfig
from lseg_toolkit.timeseries.enums import AssetClass
from lseg_toolkit.timeseries.fed_funds import (
    fetch_fed_funds_daily,
    fetch_fed_funds_hourly,
    get_ff_continuous_symbol,
    parse_ff_continuous_rank,
)
from lseg_toolkit.timeseries.fetch import (
    fetch_fras,
    fetch_govt_yields,
    fetch_futures,
    fetch_fx,
    fetch_ois,
    parse_govt_yield_symbol,
    resolve_ric,
)
from lseg_toolkit.timeseries.rolling import build_continuous
from lseg_toolkit.timeseries.storage import (
    get_connection,
    log_extraction,
    save_instrument,
    save_roll_event,
    save_timeseries,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@contextmanager
def timer(description: str, verbose: bool = True):
    """Context manager to time code blocks."""
    start = time.time()
    yield
    elapsed = time.time() - start
    if verbose:
        print(f"  {description}: {elapsed:.2f}s")


@dataclass
class ExtractionResult:
    """Result of a time series extraction."""

    symbol: str
    rows_fetched: int
    start_date: date | None
    end_date: date | None
    success: bool
    error: str | None = None
    roll_events: int = 0
    parquet_path: Path | None = None


@dataclass
class PipelineResult:
    """Result of the full pipeline run."""

    config: TimeSeriesConfig
    results: list[ExtractionResult] = field(default_factory=list)
    total_rows: int = 0
    elapsed_seconds: float = 0.0
    db_path: Path | None = None
    parquet_files: list[Path] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        """Number of successful extractions."""
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        """Number of failed extractions."""
        return sum(1 for r in self.results if not r.success)


class TimeSeriesExtractionPipeline:
    """
    Pipeline for extracting time series data from LSEG.

    Orchestrates the full workflow:
    1. Resolve symbols to LSEG RICs
    2. Fetch time series data
    3. Build continuous contracts (optional)
    4. Store to SQLite
    5. Export to Parquet (optional)
    """

    def __init__(self, config: TimeSeriesConfig, verbose: bool = True):
        """
        Initialize extraction pipeline.

        Args:
            config: Extraction configuration.
            verbose: Print progress messages.
        """
        self.config = config
        self.verbose = verbose
        self.session: SessionManager | None = None

    def run(self) -> PipelineResult:
        """
        Execute the full extraction pipeline.

        Returns:
            PipelineResult with extraction details.
        """
        start_time = time.time()
        result = PipelineResult(config=self.config)

        if self.verbose:
            self._print_config()

        # Open LSEG session
        with timer("Opening LSEG session", self.verbose):
            self.session = SessionManager()

        try:
            # Determine asset class (auto-detect if not specified)
            asset_class = self.config.asset_class
            if asset_class is None:
                asset_class = self._detect_asset_class(self.config.symbols)

            # Fetch data based on asset class
            if asset_class == AssetClass.BOND_FUTURES:
                extraction_results = self._extract_futures()
            elif asset_class == AssetClass.FX_SPOT:
                extraction_results = self._extract_fx()
            elif asset_class == AssetClass.STIR_FUTURES:
                extraction_results = self._extract_stir_futures()
            elif asset_class == AssetClass.OIS:
                extraction_results = self._extract_ois()
            elif asset_class == AssetClass.GOVT_YIELD:
                extraction_results = self._extract_treasury_yields()
            elif asset_class == AssetClass.FRA:
                extraction_results = self._extract_fras()
            else:
                # Generic extraction
                extraction_results = self._extract_generic()

            result.results = extraction_results
            result.total_rows = sum(r.rows_fetched for r in extraction_results)

            # Export to Parquet if requested
            # Note: Parquet export is deprecated pending refactor to PostgreSQL
            if self.config.export_parquet:
                logger.warning(
                    "Parquet export is temporarily disabled during PostgreSQL migration"
                )

            result.db_path = None

        finally:
            if self.session:
                self.session.close_session()

        result.elapsed_seconds = time.time() - start_time

        if self.verbose:
            self._print_summary(result)

        return result

    def _detect_asset_class(self, symbols: list[str]) -> AssetClass:
        """Auto-detect asset class from symbols."""
        if not symbols:
            return AssetClass.BOND_FUTURES

        sample = symbols[0].upper()

        # Check for OIS pattern
        if "OIS" in sample:
            return AssetClass.OIS

        # Check for FX pattern (6 letters like EURUSD)
        if len(sample) == 6 and sample.isalpha():
            return AssetClass.FX_SPOT

        if parse_ff_continuous_rank(sample) is not None:
            return AssetClass.STIR_FUTURES

        # Check for FRA pattern (contains X)
        if "X" in sample and sample.endswith("F"):
            return AssetClass.FRA

        # Check for Treasury yield pattern
        if sample.endswith("T") or "YT" in sample:
            return AssetClass.GOVT_YIELD

        # Default to futures
        return AssetClass.BOND_FUTURES

    def _extract_stir_futures(self) -> list[ExtractionResult]:
        """Extract STIR futures. Currently supports Fed Funds continuous ranks."""
        results: list[ExtractionResult] = []

        client = get_client()

        for symbol in self.config.symbols:
            rank = parse_ff_continuous_rank(symbol)
            if rank is None:
                results.append(
                    ExtractionResult(
                        symbol=symbol,
                        rows_fetched=0,
                        start_date=None,
                        end_date=None,
                        success=False,
                        error=(
                            "Unsupported STIR symbol "
                            "(currently only FF_CONTINUOUS / FF_CONTINUOUS_<rank>)"
                        ),
                    )
                )
                continue

            canonical_symbol = get_ff_continuous_symbol(rank)
            ric = f"FFc{rank}"
            instrument_name = (
                "30-Day Fed Funds Continuous"
                if rank == 1
                else f"30-Day Fed Funds Continuous Rank {rank}"
            )

            if self.config.granularity.value == "daily":
                df = fetch_fed_funds_daily(
                    client,
                    self.config.start_date,
                    self.config.end_date,
                    rank=rank,
                )
            elif self.config.granularity.value == "hourly":
                df = fetch_fed_funds_hourly(
                    client,
                    self.config.start_date,
                    self.config.end_date,
                    rank=rank,
                )
            else:
                results.append(
                    ExtractionResult(
                        symbol=canonical_symbol,
                        rows_fetched=0,
                        start_date=None,
                        end_date=None,
                        success=False,
                        error=(
                            f"{canonical_symbol} currently supports only "
                            "daily/hourly extraction"
                        ),
                    )
                )
                continue

            result = self._store_timeseries(
                symbol=canonical_symbol,
                df=df,
                asset_class=AssetClass.STIR_FUTURES,
                ric=ric,
                name=instrument_name,
                underlying="FF",
                exchange="CME",
                continuous_type="continuous",
            )
            results.append(result)

        return results

    def _extract_futures(self) -> list[ExtractionResult]:
        """Extract futures data."""
        results: list[ExtractionResult] = []

        with timer("Fetching futures data", self.verbose):
            data = fetch_futures(
                self.config.symbols,
                self.config.start_date,
                self.config.end_date,
                self.config.granularity,
                continuous=not self.config.continuous,  # If continuous, we fetch discrete
            )

        if self.config.continuous:
            # Build continuous contracts
            for symbol in self.config.symbols:
                result = self._build_and_store_continuous(symbol, data)
                results.append(result)
        else:
            # Store discrete contracts
            for symbol, df in data.items():
                result = self._store_timeseries(
                    symbol=symbol,
                    df=df,
                    asset_class=AssetClass.BOND_FUTURES,
                    ric=resolve_ric(symbol, AssetClass.BOND_FUTURES),
                )
                results.append(result)

        return results

    def _build_and_store_continuous(
        self, symbol: str, data: dict[str, pd.DataFrame]
    ) -> ExtractionResult:
        """Build continuous contract and store."""
        try:
            with timer(f"Building continuous {symbol}", self.verbose):
                continuous_df, roll_events = build_continuous(
                    data,
                    roll_method=self.config.roll_method,
                    continuous_type=self.config.continuous_type,
                )

            # Store to database
            result = self._store_timeseries(
                symbol=symbol,
                df=continuous_df,
                asset_class=AssetClass.BOND_FUTURES,
                ric=resolve_ric(symbol, AssetClass.BOND_FUTURES),
                continuous_type=self.config.continuous_type.value,
            )

            # Store roll events
            with get_connection() as conn:
                for event in roll_events:
                    save_roll_event(
                        conn,
                        symbol,
                        event.roll_date,
                        event.from_contract,
                        event.to_contract,
                        event.from_price,
                        event.to_price,
                        event.roll_method,
                    )

            result.roll_events = len(roll_events)
            return result

        except Exception as e:
            logger.error(f"Failed to build continuous for {symbol}: {e}")
            return ExtractionResult(
                symbol=symbol,
                rows_fetched=0,
                start_date=None,
                end_date=None,
                success=False,
                error=str(e),
            )

    def _extract_fx(self) -> list[ExtractionResult]:
        """Extract FX data."""
        results: list[ExtractionResult] = []

        with timer("Fetching FX data", self.verbose):
            data = fetch_fx(
                self.config.symbols,
                self.config.start_date,
                self.config.end_date,
                self.config.granularity,
            )

        for pair, df in data.items():
            result = self._store_timeseries(
                symbol=pair,
                df=df,
                asset_class=AssetClass.FX_SPOT,
                ric=resolve_ric(pair, AssetClass.FX_SPOT),
                base_currency=pair[:3],
                quote_currency=pair[3:6],
            )
            results.append(result)

        return results

    def _extract_ois(self) -> list[ExtractionResult]:
        """Extract OIS curve data."""
        results: list[ExtractionResult] = []

        # Parse symbols as tenors (e.g., ['1M', '3M', '1Y'])
        tenors = self.config.symbols

        with timer("Fetching OIS data", self.verbose):
            data = fetch_ois(
                "USD",  # TODO: Make configurable
                tenors,
                self.config.start_date,
                self.config.end_date,
            )

        for tenor, df in data.items():
            symbol = f"USD{tenor}OIS"
            result = self._store_timeseries(
                symbol=symbol,
                df=df,
                asset_class=AssetClass.OIS,
                ric=f"{symbol}=",
                currency="USD",
                tenor=tenor,
                reference_rate="SOFR",
            )
            results.append(result)

        return results

    def _extract_treasury_yields(self) -> list[ExtractionResult]:
        """Extract government yield curves, defaulting bare tenors to US Treasuries."""
        results: list[ExtractionResult] = []

        with timer("Fetching Treasury yield data", self.verbose):
            data = fetch_govt_yields(
                self.config.symbols,
                self.config.start_date,
                self.config.end_date,
            )

        for configured_symbol, df in data.items():
            country, tenor, symbol, ric = parse_govt_yield_symbol(configured_symbol)
            result = self._store_timeseries(
                symbol=symbol,
                df=df,
                asset_class=AssetClass.GOVT_YIELD,
                ric=ric,
                country=country,
                tenor=tenor,
            )
            results.append(result)

        return results

    def _extract_fras(self) -> list[ExtractionResult]:
        """Extract FRA data."""
        results: list[ExtractionResult] = []

        # Parse symbols as tenors (e.g., ['1X4', '3X6'])
        tenors = self.config.symbols

        with timer("Fetching FRA data", self.verbose):
            data = fetch_fras(
                "USD",  # TODO: Make configurable
                tenors,
                self.config.start_date,
                self.config.end_date,
            )

        for tenor, df in data.items():
            symbol = f"USD{tenor}F"
            result = self._store_timeseries(
                symbol=symbol,
                df=df,
                asset_class=AssetClass.FRA,
                ric=f"{symbol}=",
                currency="USD",
                tenor=tenor,
            )
            results.append(result)

        return results

    def _extract_generic(self) -> list[ExtractionResult]:
        """Generic extraction for other asset classes."""
        results: list[ExtractionResult] = []

        for symbol in self.config.symbols:
            ric = resolve_ric(symbol, self.config.asset_class)
            result = self._store_timeseries(
                symbol=symbol,
                df=pd.DataFrame(),  # TODO: Implement generic fetch
                asset_class=self.config.asset_class or AssetClass.BOND_FUTURES,
                ric=ric,
            )
            results.append(result)

        return results

    def _store_timeseries(
        self,
        symbol: str,
        df: pd.DataFrame,
        asset_class: AssetClass,
        ric: str,
        **kwargs,
    ) -> ExtractionResult:
        """Store time series data to database."""
        if df.empty:
            return ExtractionResult(
                symbol=symbol,
                rows_fetched=0,
                start_date=None,
                end_date=None,
                success=False,
                error="No data returned",
            )

        try:
            with get_connection() as conn:
                instrument_name = kwargs.pop("name", symbol)
                # Save instrument
                inst_id = save_instrument(
                    conn,
                    symbol=symbol,
                    name=instrument_name,
                    asset_class=asset_class,
                    lseg_ric=ric,
                    **kwargs,
                )

                # Save time series
                rows = save_timeseries(
                    conn,
                    inst_id,
                    df,
                    self.config.granularity,
                )

                # Log extraction
                log_extraction(
                    conn,
                    symbol,
                    self.config.start_date,
                    self.config.end_date,
                    self.config.granularity,
                    rows,
                )

            # Get date range from data
            start_date = (
                df.index.min().date()
                if hasattr(df.index.min(), "date")
                else df.index.min()
            )
            end_date = (
                df.index.max().date()
                if hasattr(df.index.max(), "date")
                else df.index.max()
            )

            return ExtractionResult(
                symbol=symbol,
                rows_fetched=rows,
                start_date=start_date,
                end_date=end_date,
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to store {symbol}: {e}")
            return ExtractionResult(
                symbol=symbol,
                rows_fetched=0,
                start_date=None,
                end_date=None,
                success=False,
                error=str(e),
            )

    def _print_config(self) -> None:
        """Print extraction configuration."""
        print("=" * 80)
        print("TIME SERIES EXTRACTION")
        print("=" * 80)
        print(f"Symbols:      {', '.join(self.config.symbols)}")
        print(
            f"Asset Class:  {self.config.asset_class.value if self.config.asset_class else 'auto'}"
        )
        print(f"Date Range:   {self.config.start_date} to {self.config.end_date}")
        print(f"Granularity:  {self.config.granularity.value}")
        if self.config.continuous:
            print(f"Continuous:   {self.config.continuous_type.value}")
            print(f"Roll Method:  {self.config.roll_method.value}")
        print("Database:     PostgreSQL (via TSDB_* env vars)")
        if self.config.export_parquet:
            print(f"Parquet Dir:  {self.config.parquet_dir}")
        print("=" * 80)
        print()

    def _print_summary(self, result: PipelineResult) -> None:
        """Print extraction summary."""
        print()
        print("=" * 80)
        print("EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Total Rows:   {result.total_rows:,}")
        print(f"Successful:   {result.success_count}/{len(result.results)}")
        print(f"Elapsed:      {result.elapsed_seconds:.2f}s")
        print(f"Database:     {result.db_path}")
        if result.parquet_files:
            print(f"Parquet:      {len(result.parquet_files)} files")

        if result.failure_count > 0:
            print("\nFailed extractions:")
            for r in result.results:
                if not r.success:
                    print(f"  {r.symbol}: {r.error}")

        print("=" * 80)
