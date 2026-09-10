"""
Async Cache Layer for LSEG time series data.

Provides cache-first architecture with:
- Async/await concurrency for parallel multi-RIC fetching
- Granularity-aware gap detection (daily data doesn't satisfy 5min requests)
- Instrument validation against known set from constants.py

Example:
    >>> cache = DataCache()
    >>> df = cache.get_or_fetch(ric="TYc1", start="2024-01-01", end="2024-12-31")

    >>> # Async usage
    >>> results = await cache.async_get_or_fetch_many(
    ...     rics=["TYc1", "USc1", "FVc1"],
    ...     start="2024-01-01",
    ...     end="2024-12-31"
    ... )
"""

from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import pandas as pd

from lseg_toolkit.exceptions import DataRetrievalError
from lseg_toolkit.timeseries import storage
from lseg_toolkit.timeseries.client import LSEGDataClient, get_client
from lseg_toolkit.timeseries.constants import (
    ALL_FUTURES_MAPPING,
    BENCHMARK_FIXINGS,
    EUR_FRA_TENORS,
    EUR_IRS_TENORS,
    EURIBOR_RICS,
    FRA_CURRENCIES,
    FRA_TENORS,
    FX_SPOT_RICS,
    G7_IRS_CURRENCIES,
    G7_IRS_TENORS,
    G7_OIS_CURRENCIES,
    G7_OIS_TENORS,
    GBP_FRA_TENORS,
    GBP_IRS_TENORS,
    GBP_OIS_TENORS,
    SOVEREIGN_YIELD_RICS,
    STIR_FUTURES_RICS,
    TREASURY_FUTURES_MAPPING,
    USD_DEPOSIT_TENORS,
    USD_FRA_TENORS,
    USD_IRS_TENORS,
    USD_OIS_TENORS,
    USD_REPO_RICS,
)
from lseg_toolkit.timeseries.enums import AssetClass, Granularity
from lseg_toolkit.timeseries.storage import (
    get_data_shape,
    get_instrument_id,
    load_timeseries,
    save_instrument,
    save_timeseries,
)
from lseg_toolkit.timeseries.storage.fetch_coverage import (
    load_fetch_coverage,
    save_fetch_coverage,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    import psycopg

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class InstrumentNotFoundError(Exception):
    """Raised when a RIC is not in the known instrument set."""

    pass


class CacheError(Exception):
    """Base exception for cache operations."""

    pass


# =============================================================================
# Result Types
# =============================================================================


class FetchStatus(StrEnum):
    """Status of a fetch operation."""

    SUCCESS = "success"
    FROM_CACHE = "from_cache"
    PARTIAL = "partial"  # Some data from cache, some fetched
    FAILED = "failed"
    NOT_FOUND = "not_found"


@dataclass
class FetchResult:
    """Result of a single RIC fetch operation."""

    ric: str
    status: FetchStatus
    data: pd.DataFrame | None = None
    error: str | None = None
    rows_fetched: int = 0
    rows_from_cache: int = 0
    complete: bool = True
    coverage_verified: bool = False

    @property
    def total_rows(self) -> int:
        """Total rows retrieved (cache + fetched)."""
        return self.rows_from_cache + self.rows_fetched

    @property
    def success(self) -> bool:
        """Whether the operation succeeded."""
        return (
            self.complete
            and self.error is None
            and self.status
            in (
                FetchStatus.SUCCESS,
                FetchStatus.FROM_CACHE,
                FetchStatus.PARTIAL,
            )
        )


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class CacheConfig:
    """Configuration for DataCache."""

    max_concurrent_fetches: int = 5
    executor_workers: int = 4
    validate_instruments: bool = True
    auto_register_instruments: bool = True
    # Explicit market calendars avoid interpreting holidays as missing data.
    exchange_calendars: dict[str, str] = field(default_factory=dict)
    # Optional exact expected bar timestamps, e.g. for an instrument-specific session.
    expected_timestamps: (
        Callable[[str, date, date, Granularity], pd.DatetimeIndex] | None
    ) = None


# =============================================================================
# Instrument Registry
# =============================================================================


class InstrumentRegistry:
    """
    Registry for validating instruments against known set.

    Validates RICs against all known instruments from constants.py:
    - Futures (ALL_FUTURES_MAPPING)
    - FX Spot (FX_SPOT_RICS)
    - OIS tenors
    - IRS tenors
    - FRA tenors
    - Government yields
    - Fixings
    """

    def __init__(self) -> None:
        self._known_instruments: set[str] | None = None
        self._ric_to_asset_class: dict[str, AssetClass] = {}
        self._ric_patterns: list[tuple[re.Pattern, AssetClass]] = []
        self._build_registry()

    def _build_registry(self) -> None:
        """Build the set of known instruments from constants."""
        known: set[str] = set()

        # --- Futures (continuous contracts) ---
        for cme_symbol, lseg_root in ALL_FUTURES_MAPPING.items():
            # Add continuous contract symbols
            for suffix in ["c1", "c2", "c3"]:
                ric = f"{lseg_root}{suffix}"
                known.add(ric)
                known.add(cme_symbol)  # Allow CME symbol too
                # Determine asset class from the mapping source
                if cme_symbol in ("ZT", "Z3N", "ZF", "ZN", "TN", "TWE", "ZB", "UB"):
                    self._ric_to_asset_class[ric] = AssetClass.BOND_FUTURES
                    self._ric_to_asset_class[cme_symbol] = AssetClass.BOND_FUTURES
                elif cme_symbol in ("ES", "NQ", "RTY", "YM", "FESX", "FDAX"):
                    self._ric_to_asset_class[ric] = AssetClass.INDEX_FUTURES
                    self._ric_to_asset_class[cme_symbol] = AssetClass.INDEX_FUTURES
                elif cme_symbol in ("6E", "6B", "6J", "6A", "6C", "6S"):
                    self._ric_to_asset_class[ric] = AssetClass.FX_FUTURES
                    self._ric_to_asset_class[cme_symbol] = AssetClass.FX_FUTURES
                elif cme_symbol in ("CL", "NG", "GC", "SI", "HG", "ZC", "ZW", "ZS"):
                    self._ric_to_asset_class[ric] = AssetClass.COMMODITY
                    self._ric_to_asset_class[cme_symbol] = AssetClass.COMMODITY

        # --- FX Spot ---
        for symbol, ric in FX_SPOT_RICS.items():
            known.add(ric)
            known.add(symbol)
            self._ric_to_asset_class[ric] = AssetClass.FX_SPOT
            self._ric_to_asset_class[symbol] = AssetClass.FX_SPOT

        # --- OIS Tenors (all G7 currencies) ---
        for ccy in G7_OIS_CURRENCIES:
            for tenor in G7_OIS_TENORS:
                ric = f"{ccy}{tenor}OIS="
                known.add(ric)
                self._ric_to_asset_class[ric] = AssetClass.OIS
        # USD OIS extended tenors
        for tenor in USD_OIS_TENORS:
            ric = f"USD{tenor}OIS="
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.OIS
        # GBP OIS extended tenors
        for tenor in GBP_OIS_TENORS:
            ric = f"GBP{tenor}OIS="
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.OIS

        # --- IRS Tenors ---
        # EUR IRS
        for tenor in EUR_IRS_TENORS:
            ric = f"EURIRS{tenor}="
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.IRS
        # USD IRS
        for tenor in USD_IRS_TENORS:
            ric = f"USDIRS{tenor}="
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.IRS
        # GBP IRS (GBPSB6L pattern)
        for tenor in GBP_IRS_TENORS:
            ric = f"GBPSB6L{tenor}="
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.IRS
        # G7 IRS generic pattern
        for ccy in G7_IRS_CURRENCIES:
            for tenor in G7_IRS_TENORS:
                if ccy != "GBP":  # GBP uses different pattern
                    ric = f"{ccy}IRS{tenor}="
                    known.add(ric)
                    self._ric_to_asset_class[ric] = AssetClass.IRS

        # --- FRA Tenors ---
        for ccy in FRA_CURRENCIES:
            tenors = FRA_TENORS
            if ccy == "USD":
                tenors = USD_FRA_TENORS
            elif ccy == "EUR":
                tenors = EUR_FRA_TENORS
            elif ccy == "GBP":
                tenors = GBP_FRA_TENORS
            for tenor in tenors:
                ric = f"{ccy}{tenor}F="
                known.add(ric)
                self._ric_to_asset_class[ric] = AssetClass.FRA

        # --- Deposits ---
        for tenor in USD_DEPOSIT_TENORS:
            ric = f"USD{tenor}D="
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.DEPOSIT

        # --- Repos ---
        for _tenor, ric in USD_REPO_RICS.items():
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.REPO

        # --- Government Yields ---
        for country, tenor_rics in SOVEREIGN_YIELD_RICS.items():
            for _tenor, ric in tenor_rics.items():
                known.add(ric)
                self._ric_to_asset_class[ric] = AssetClass.GOVT_YIELD
                # Also add =RRPS variant for US
                if country == "US":
                    rrps_ric = ric.replace("=RR", "=RRPS")
                    known.add(rrps_ric)
                    self._ric_to_asset_class[rrps_ric] = AssetClass.GOVT_YIELD

        # --- Fixings (SOFR, ESTR, etc.) ---
        for _name, ric in BENCHMARK_FIXINGS.items():
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.FIXING
        for _tenor, ric in EURIBOR_RICS.items():
            known.add(ric)
            self._ric_to_asset_class[ric] = AssetClass.FIXING

        # --- STIR Futures ---
        for _name, ric in STIR_FUTURES_RICS.items():
            if not ric.startswith("0#"):  # Skip chain RICs
                known.add(ric)
                self._ric_to_asset_class[ric] = AssetClass.STIR_FUTURES

        self._known_instruments = known

        # Build regex patterns for flexible matching
        self._ric_patterns = [
            # Futures: {root}c{n} or {root}{month}{year}
            (re.compile(r"^[A-Z]{1,4}c[1-9]$"), AssetClass.BOND_FUTURES),
            # OIS: {CCY}{tenor}OIS=
            (re.compile(r"^[A-Z]{3}[0-9]+[YM]OIS=$"), AssetClass.OIS),
            # IRS: {CCY}IRS{tenor}= or GBPSB6L{tenor}=
            (re.compile(r"^[A-Z]{3}IRS[0-9]+[YM]=$"), AssetClass.IRS),
            (re.compile(r"^GBPSB6L[0-9]+[YM]=$"), AssetClass.IRS),
            # FRA: {CCY}{tenor}F=
            (re.compile(r"^[A-Z]{3}[0-9]+X[0-9]+F=$"), AssetClass.FRA),
            # Govt Yield: {CC}{tenor}T=RR or =RRPS
            (re.compile(r"^[A-Z]{2}[0-9]+[YM]T=RR(PS)?$"), AssetClass.GOVT_YIELD),
            # FX Spot: {CCY}= or {CCYCCY}=
            (re.compile(r"^[A-Z]{3}=$"), AssetClass.FX_SPOT),
            (re.compile(r"^[A-Z]{6}=$"), AssetClass.FX_SPOT),
        ]

    @property
    def known_instruments(self) -> set[str]:
        """Set of all known instrument symbols/RICs."""
        if self._known_instruments is None:
            self._build_registry()
        return self._known_instruments  # type: ignore

    def is_valid(self, ric: str) -> bool:
        """Check if a RIC is in the known instrument set."""
        # Direct lookup
        if ric in self.known_instruments:
            return True

        # Pattern matching for flexible RICs
        for pattern, _ in self._ric_patterns:
            if pattern.match(ric):
                return True

        return False

    def validate(self, ric: str) -> None:
        """
        Validate a RIC against the known instrument set.

        Raises:
            InstrumentNotFoundError: If RIC is not in known set.
        """
        if not self.is_valid(ric):
            raise InstrumentNotFoundError(
                f"Unknown instrument: {ric}. "
                f"RIC must be in the known instrument set from constants.py"
            )

    def get_asset_class(self, ric: str) -> AssetClass | None:
        """Infer asset class from RIC."""
        # Direct lookup
        if ric in self._ric_to_asset_class:
            return self._ric_to_asset_class[ric]

        # Pattern matching
        for pattern, asset_class in self._ric_patterns:
            if pattern.match(ric):
                return asset_class

        return None

    def register_instrument(
        self,
        conn: psycopg.Connection[dict[str, Any]],
        symbol: str,
        ric: str | None = None,
    ) -> int:
        """
        Register an instrument in the database.

        Args:
            conn: Database connection.
            symbol: Symbol to register.
            ric: LSEG RIC (defaults to symbol if not provided).

        Returns:
            Instrument ID.

        Raises:
            InstrumentNotFoundError: If symbol is not in known set.
        """
        self.validate(symbol)

        ric = ric or symbol
        asset_class = self.get_asset_class(symbol) or AssetClass.EQUITY
        data_shape = get_data_shape(asset_class)

        return save_instrument(
            conn=conn,
            symbol=symbol,
            name=symbol,
            asset_class=asset_class,
            lseg_ric=ric,
            data_shape=data_shape,
        )


# Module-level singleton registry
_registry: InstrumentRegistry | None = None


def get_registry() -> InstrumentRegistry:
    """Get the instrument registry singleton."""
    global _registry
    if _registry is None:
        _registry = InstrumentRegistry()
    return _registry


# =============================================================================
# Gap Detection
# =============================================================================


@dataclass
class DateGap:
    """Represents a gap in stored data."""

    start: date
    end: date

    @property
    def days(self) -> int:
        """Number of days in the gap."""
        return (self.end - self.start).days + 1


def _clamp_frame(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Restrict rows to inclusive requested dates without changing their timezone."""
    if df.empty:
        return df
    dates = pd.to_datetime(df.index).date
    return df.loc[(dates >= start) & (dates <= end)]


def detect_gaps(
    conn: psycopg.Connection[dict[str, Any]],
    symbol: str,
    start_date: date,
    end_date: date,
    granularity: Granularity,
    *,
    cached_data: pd.DataFrame | None = None,
    expected_timestamps: pd.DatetimeIndex | None = None,
    exchange_calendar: str | None = None,
    covered_ranges: list[tuple[date, date]] | None = None,
    refresh_mutable: bool = True,
) -> list[DateGap]:
    """Find missing coverage, never infer trading sessions from weekdays alone.

    Daily Treasury futures use the CME calendar. Other markets can supply an
    exchange calendar, or exact expected timestamps for intraday bars. Without
    a known schedule, use successful request intervals (including empty results),
    never min/max rows. Absent coverage metadata, refetch the request.
    All returned gaps are clamped to the requested range.
    """
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")
    if expected_timestamps is None and granularity == Granularity.DAILY:
        root = re.sub(r"c\d+$", "", symbol)
        if exchange_calendar is None and (
            symbol in TREASURY_FUTURES_MAPPING
            or root in TREASURY_FUTURES_MAPPING.values()
        ):
            exchange_calendar = "CME"
        if exchange_calendar:
            import exchange_calendars as xcals

            calendar = xcals.get_calendar(exchange_calendar)
            expected_timestamps = calendar.sessions_in_range(start_date, end_date)

    today = datetime.now(UTC).date()
    if expected_timestamps is not None:
        if cached_data is None:
            cached_data = load_timeseries(
                conn, symbol, start_date, end_date, granularity
            )
        expected = pd.DatetimeIndex(pd.to_datetime(expected_timestamps, utc=True))
        expected = expected[(expected.date >= start_date) & (expected.date <= end_date)]
        if not refresh_mutable:
            # Post-fetch completeness only judges closed dates. An open session
            # or future trading day cannot yet have a complete set of bars.
            expected = expected[expected.date < today]
        actual = pd.DatetimeIndex(pd.to_datetime(cached_data.index, utc=True))
        if granularity == Granularity.DAILY:
            expected, actual = expected.normalize(), actual.normalize()
        missing = set(expected.difference(actual).date)
        if refresh_mutable and end_date >= today:
            missing.update(pd.date_range(max(start_date, today), end_date).date)
        missing_days = sorted(missing)
        gaps: list[DateGap] = []
        for day in missing_days:
            if gaps and day == gaps[-1].end + timedelta(days=1):
                gaps[-1].end = day
            else:
                gaps.append(DateGap(start=day, end=day))
        return gaps

    # Subtract the UNION of covered intervals, retaining all disjoint holes.
    # A cursor also merges overlapping/adjacent ranges without database rewrites.
    if covered_ranges is None:
        instrument_id = get_instrument_id(conn, symbol)
        covered_ranges = (
            load_fetch_coverage(conn, instrument_id, granularity, start_date, end_date)
            if instrument_id is not None
            else []
        )
    cursor = start_date
    gaps = []
    for covered_start, covered_end in sorted(covered_ranges):
        covered_end = min(covered_end, today - timedelta(days=1))
        if covered_end < cursor or covered_start > end_date:
            continue
        if covered_start > cursor:
            gaps.append(DateGap(cursor, covered_start - timedelta(days=1)))
        if covered_end >= end_date:
            return gaps
        cursor = max(cursor, covered_end + timedelta(days=1))
    if cursor <= end_date:
        gaps.append(DateGap(cursor, end_date))
    return gaps


# =============================================================================
# Data Cache
# =============================================================================


class DataCache:
    """
    Cache-first data retrieval with async support.

    Provides:
    - Sync API: get_or_fetch(), get_or_fetch_many()
    - Async API: async_get_or_fetch(), async_get_or_fetch_many()
    - Granularity-aware gap detection
    - Instrument validation against known set
    - Progress tracking

    Example:
        >>> cache = DataCache()
        >>> df = cache.get_or_fetch("TYc1", start="2024-01-01", end="2024-12-31")

        >>> # Async batch fetch
        >>> results = await cache.async_get_or_fetch_many(
        ...     rics=["TYc1", "USc1", "FVc1"],
        ...     start="2024-01-01",
        ...     end="2024-12-31"
        ... )
    """

    def __init__(
        self,
        config: CacheConfig | None = None,
        client: LSEGDataClient | None = None,
    ) -> None:
        """
        Initialize DataCache.

        Args:
            config: Cache configuration (uses defaults if None).
            client: LSEG data client (creates default if None).
        """
        self.config = config or CacheConfig()
        self.client = client or get_client()
        self.registry = get_registry()
        self._executor: ThreadPoolExecutor | None = None
        self._semaphore: asyncio.Semaphore | None = None
        # Per-RIC locks to prevent duplicate fetches for same RIC+granularity
        self._fetch_locks: dict[tuple[str, Granularity], asyncio.Lock] = {}

        # Check connectivity only; schema provisioning is an explicit operator step.
        with storage.get_connection():
            pass

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Lazy initialization of thread pool executor."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self.config.executor_workers,
                thread_name_prefix="cache_fetch",
            )
        return self._executor

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Lazy initialization of concurrency semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_fetches)
        return self._semaphore

    def _get_fetch_lock(self, ric: str, granularity: Granularity) -> asyncio.Lock:
        """Get or create a lock for a specific RIC+granularity combination.

        This prevents duplicate concurrent fetches for the same data.
        """
        key = (ric, granularity)
        if key not in self._fetch_locks:
            self._fetch_locks[key] = asyncio.Lock()
        return self._fetch_locks[key]

    def close(self) -> None:
        """Clean up resources."""
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None

    def __enter__(self) -> DataCache:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # -------------------------------------------------------------------------
    # Sync API
    # -------------------------------------------------------------------------

    def get_or_fetch(
        self,
        ric: str,
        start: str | date,
        end: str | date,
        granularity: Granularity = Granularity.DAILY,
    ) -> pd.DataFrame:
        """
        Get data from cache or fetch from LSEG if missing.

        Args:
            ric: Instrument RIC.
            start: Start date.
            end: End date.
            granularity: Data granularity.

        Returns:
            DataFrame with time series data.

        Raises:
            InstrumentNotFoundError: If RIC is not in known set.
            DataRetrievalError: If fetch fails.
        """
        result = self._get_or_fetch_single(ric, start, end, granularity)
        if result.success and result.data is not None:
            return result.data
        elif result.status == FetchStatus.NOT_FOUND:
            raise InstrumentNotFoundError(result.error or f"Unknown instrument: {ric}")
        elif result.error:
            raise DataRetrievalError(result.error)
        return pd.DataFrame()

    def get_or_fetch_many(
        self,
        rics: list[str],
        start: str | date,
        end: str | date,
        granularity: Granularity = Granularity.DAILY,
    ) -> dict[str, pd.DataFrame]:
        """
        Get data for multiple RICs from cache or fetch if missing.

        Args:
            rics: List of instrument RICs.
            start: Start date.
            end: End date.
            granularity: Data granularity.

        Returns:
            Dict mapping RIC to DataFrame.
        """
        results: dict[str, pd.DataFrame] = {}
        for ric in rics:
            try:
                df = self.get_or_fetch(ric, start, end, granularity)
                results[ric] = df
            except (InstrumentNotFoundError, DataRetrievalError) as e:
                logger.warning(f"Failed to fetch {ric}: {e}")
                results[ric] = pd.DataFrame()
        return results

    def _get_or_fetch_single(
        self,
        ric: str,
        start: str | date,
        end: str | date,
        granularity: Granularity,
    ) -> FetchResult:
        """Internal implementation of get_or_fetch."""
        # Normalize dates
        if isinstance(start, str):
            start_date = date.fromisoformat(start)
        else:
            start_date = start
        if isinstance(end, str):
            end_date = date.fromisoformat(end)
        else:
            end_date = end

        # Validate instrument
        if self.config.validate_instruments:
            try:
                self.registry.validate(ric)
            except InstrumentNotFoundError as e:
                return FetchResult(
                    ric=ric,
                    status=FetchStatus.NOT_FOUND,
                    error=str(e),
                )

        with storage.get_connection() as conn:
            # Ensure instrument is registered
            instrument_id = get_instrument_id(conn, ric)
            if instrument_id is None and self.config.auto_register_instruments:
                instrument_id = self.registry.register_instrument(conn, ric)

            # Load once, then assess coverage using the instrument's actual schedule.
            cached_df = _clamp_frame(
                load_timeseries(conn, ric, start_date, end_date, granularity),
                start_date,
                end_date,
            )
            expected = (
                self.config.expected_timestamps(ric, start_date, end_date, granularity)
                if self.config.expected_timestamps
                else None
            )
            exchange_calendar = self.config.exchange_calendars.get(ric)
            known_schedule = expected is not None or (
                granularity == Granularity.DAILY
                and (
                    exchange_calendar is not None
                    or ric in TREASURY_FUTURES_MAPPING
                    or re.sub(r"c\d+$", "", ric) in TREASURY_FUTURES_MAPPING.values()
                )
            )
            coverage = (
                load_fetch_coverage(
                    conn, instrument_id, granularity, start_date, end_date
                )
                if instrument_id is not None and not known_schedule
                else []
            )
            gaps = detect_gaps(
                conn,
                ric,
                start_date,
                end_date,
                granularity,
                cached_data=cached_df,
                expected_timestamps=expected,
                exchange_calendar=exchange_calendar,
                covered_ranges=coverage,
            )
            rows_from_cache = len(cached_df) if not cached_df.empty else 0

            # If no gaps, return cached data
            if not gaps:
                return FetchResult(
                    ric=ric,
                    status=FetchStatus.FROM_CACHE,
                    data=cached_df,
                    rows_from_cache=rows_from_cache,
                    coverage_verified=known_schedule,
                )

            # Fetch missing data
            rows_fetched = 0
            fetched_dfs: list[pd.DataFrame] = []
            errors: list[str] = []
            completed_gaps: list[DateGap] = []

            for gap in gaps:
                try:
                    df = _clamp_frame(
                        self._fetch_from_lseg(ric, gap.start, gap.end, granularity),
                        gap.start,
                        gap.end,
                    )
                    if not df.empty:
                        # Save to database
                        if instrument_id is not None:
                            save_timeseries(conn, instrument_id, df, granularity)
                        fetched_dfs.append(df)
                        rows_fetched += len(df)
                    completed_gaps.append(gap)
                except DataRetrievalError as e:
                    logger.warning(f"Failed to fetch {ric} for gap {gap}: {e}")
                    errors.append(f"{gap.start}..{gap.end}: {e}")

            # Combine cached and fetched data
            all_dfs = [cached_df] + fetched_dfs if not cached_df.empty else fetched_dfs
            if all_dfs:
                combined = pd.concat(all_dfs).sort_index()
                # Remove duplicates (prefer most recent)
                combined = combined[~combined.index.duplicated(keep="last")]
            else:
                combined = pd.DataFrame()

            # A known schedule can establish completeness even after an empty
            # provider response. Unknown calendars cannot prove interior coverage.
            if not errors and known_schedule:
                remaining = detect_gaps(
                    conn,
                    ric,
                    start_date,
                    end_date,
                    granularity,
                    cached_data=combined,
                    expected_timestamps=expected,
                    exchange_calendar=exchange_calendar,
                    refresh_mutable=False,
                )
                if remaining:
                    errors.append("Requested coverage remains incomplete after fetch")

            # Unknown schedules use provider-success evidence, including valid
            # empty results. Never persist known-incomplete or failed requests.
            if instrument_id is not None and not (known_schedule and errors):
                for gap in completed_gaps:
                    save_fetch_coverage(
                        conn, instrument_id, granularity, gap.start, gap.end
                    )

            # Determine status
            if errors:
                status = FetchStatus.FAILED
            elif rows_fetched > 0 and rows_from_cache > 0:
                status = FetchStatus.PARTIAL
            elif rows_fetched > 0:
                status = FetchStatus.SUCCESS
            elif rows_from_cache > 0:
                status = FetchStatus.FROM_CACHE
            else:
                status = FetchStatus.SUCCESS  # Successful empty provider response

            return FetchResult(
                ric=ric,
                status=status,
                data=combined,
                rows_fetched=rows_fetched,
                rows_from_cache=rows_from_cache,
                coverage_verified=known_schedule and not errors,
                complete=not errors,
                error="; ".join(errors) if errors else None,
            )

    def _fetch_from_lseg(
        self,
        ric: str,
        start_date: date,
        end_date: date,
        granularity: Granularity,
    ) -> pd.DataFrame:
        """Fetch data from LSEG API."""
        interval = granularity.value

        logger.info(f"Fetching {ric} from {start_date} to {end_date} ({interval})")

        df = self.client.get_history(
            rics=ric,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=interval,
        )

        return df

    # -------------------------------------------------------------------------
    # Async API
    # -------------------------------------------------------------------------

    async def async_get_or_fetch(
        self,
        ric: str,
        start: str | date,
        end: str | date,
        granularity: Granularity = Granularity.DAILY,
    ) -> pd.DataFrame:
        """
        Async version of get_or_fetch.

        Wraps the sync LSEG client with run_in_executor for async compatibility.

        Args:
            ric: Instrument RIC.
            start: Start date.
            end: End date.
            granularity: Data granularity.

        Returns:
            DataFrame with time series data.

        Raises:
            InstrumentNotFoundError: If RIC is not in known set.
            DataRetrievalError: If fetch fails.
        """
        result = await self._async_get_or_fetch_single(ric, start, end, granularity)
        if result.success and result.data is not None:
            return result.data
        elif result.status == FetchStatus.NOT_FOUND:
            raise InstrumentNotFoundError(result.error or f"Unknown instrument: {ric}")
        elif result.error:
            raise DataRetrievalError(result.error)
        return pd.DataFrame()

    async def async_get_or_fetch_many(
        self,
        rics: list[str],
        start: str | date,
        end: str | date,
        granularity: Granularity = Granularity.DAILY,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, pd.DataFrame]:
        """
        Async version of get_or_fetch_many with parallel fetching.

        Uses asyncio.gather for concurrent fetching with semaphore-based
        rate limiting.

        Args:
            rics: List of instrument RICs.
            start: Start date.
            end: End date.
            granularity: Data granularity.
            progress_callback: Optional callback(ric, completed, total).

        Returns:
            Dict mapping RIC to DataFrame.
        """
        total = len(rics)
        completed = 0
        results: dict[str, pd.DataFrame] = {}

        async def fetch_one(ric: str) -> tuple[str, FetchResult]:
            async with self.semaphore:
                result = await self._async_get_or_fetch_single(
                    ric, start, end, granularity
                )
                return ric, result

        # Launch all fetches in parallel
        tasks = [fetch_one(ric) for ric in rics]
        for coro in asyncio.as_completed(tasks):
            ric, result = await coro
            completed += 1

            if result.success and result.data is not None:
                results[ric] = result.data
            else:
                results[ric] = pd.DataFrame()
                if result.error:
                    logger.warning(f"Failed to fetch {ric}: {result.error}")

            if progress_callback:
                progress_callback(ric, completed, total)

        return results

    async def async_iter_fetch(
        self,
        rics: list[str],
        start: str | date,
        end: str | date,
        granularity: Granularity = Granularity.DAILY,
    ) -> AsyncIterator[FetchResult]:
        """
        Async iterator that yields results as they complete.

        Args:
            rics: List of instrument RICs.
            start: Start date.
            end: End date.
            granularity: Data granularity.

        Yields:
            FetchResult for each RIC as it completes.
        """

        async def fetch_one(ric: str) -> FetchResult:
            async with self.semaphore:
                return await self._async_get_or_fetch_single(
                    ric, start, end, granularity
                )

        tasks = [fetch_one(ric) for ric in rics]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            yield result

    async def _async_get_or_fetch_single(
        self,
        ric: str,
        start: str | date,
        end: str | date,
        granularity: Granularity,
    ) -> FetchResult:
        """Async wrapper around sync _get_or_fetch_single using executor.

        Uses per-RIC locking to prevent duplicate concurrent fetches for the
        same RIC+granularity combination. If multiple coroutines request the
        same data, the first one fetches while others wait and then get cached data.
        """
        # Acquire per-RIC lock to prevent duplicate fetches
        lock = self._get_fetch_lock(ric, granularity)
        async with lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self.executor,
                self._get_or_fetch_single,
                ric,
                start,
                end,
                granularity,
            )
