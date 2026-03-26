"""Extract JGB yields data from Bloomberg."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from .._legacy import warn_legacy_surface
from ..common.connection import BloombergSession
from ..common.export import build_output_path, export_to_csv, export_to_parquet
from ..common.fields import JGB_FIELDS

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _warn_legacy_path() -> None:
    warn_legacy_surface(
        "bloomberg_scripts.jgb_yields",
        replacement='bbg-extract jgb',
        note='This older modular extractor predates the supported package path and contains stale DataFrame/ticker assumptions.',
        stacklevel=3,
    )

# Standard JGB tenors and their Bloomberg tickers
JGB_TICKERS = {
    "2Y": "GJGB2 Index",
    "5Y": "GJGB5 Index",
    "10Y": "GJGB10 Index",
    "20Y": "GJGB20 Index",
    "30Y": "GJGB30 Index",
    "40Y": "GJGB40 Index",
}

# Additional JGB benchmarks
JGB_BENCHMARKS = {
    "10Y_BENCHMARK": "JGBS10 Index",  # 10Y benchmark
    "SUPER_LONG": "JGBS30 Index",  # 30Y benchmark
}


def get_jgb_tickers(
    tenors: list[str] | None = None,
    include_benchmarks: bool = False,
) -> dict[str, str]:
    """Get JGB tickers for specified tenors.

    Args:
        tenors: List of tenors (2Y, 5Y, 10Y, 20Y, 30Y, 40Y) or None for all
        include_benchmarks: Include benchmark tickers

    Returns:
        Dict mapping tenor/name to Bloomberg ticker
    """
    if tenors is None:
        tickers = dict(JGB_TICKERS)
    else:
        tickers = {t: JGB_TICKERS[t] for t in tenors if t in JGB_TICKERS}
        missing = set(tenors) - set(JGB_TICKERS.keys())
        if missing:
            logger.warning("Unknown tenors ignored: %s", missing)

    if include_benchmarks:
        tickers.update(JGB_BENCHMARKS)

    return tickers


def extract_jgb_yields_snapshot(
    tenors: list[str] | None = None,
    include_benchmarks: bool = False,
) -> pd.DataFrame:
    _warn_legacy_path()
    """Extract current JGB yields.

    Args:
        tenors: List of tenors or None for all
        include_benchmarks: Include benchmark tickers

    Returns:
        DataFrame with yield data
    """
    ticker_map = get_jgb_tickers(tenors, include_benchmarks)
    tickers = list(ticker_map.values())

    with BloombergSession() as session:
        df = session.get_reference_data(tickers, JGB_FIELDS)

    if df.empty:
        logger.warning("No JGB data returned")
        return df

    # Add tenor column from ticker mapping
    reverse_map = {v: k for k, v in ticker_map.items()}
    df["tenor"] = df["ticker"].map(reverse_map)
    df["currency"] = "JPY"
    df["instrument"] = "JGB"
    df["extract_date"] = date.today()

    return df


def extract_jgb_yields_historical(
    start_date: date,
    end_date: date | None = None,
    tenors: list[str] | None = None,
    include_benchmarks: bool = False,
) -> pd.DataFrame:
    _warn_legacy_path()
    """Extract historical JGB yields.

    Args:
        start_date: Start date for historical data
        end_date: End date (default: today)
        tenors: List of tenors or None for all
        include_benchmarks: Include benchmark tickers

    Returns:
        DataFrame with historical yield data
    """
    if end_date is None:
        end_date = date.today()

    ticker_map = get_jgb_tickers(tenors, include_benchmarks)
    tickers = list(ticker_map.values())

    with BloombergSession() as session:
        df = session.get_historical_data(
            tickers,
            ["PX_LAST"],
            start_date,
            end_date,
        )

    if df.empty:
        logger.warning("No historical JGB data returned")
        return df

    # Add tenor column from ticker mapping
    reverse_map = {v: k for k, v in ticker_map.items()}
    df["tenor"] = df["ticker"].map(reverse_map)
    df["currency"] = "JPY"
    df["instrument"] = "JGB"

    # Rename PX_LAST to yield for clarity
    if "PX_LAST" in df.columns:
        df = df.rename(columns={"PX_LAST": "yield"})

    return df


def run_jgb_extraction(
    output_dir: Path | None = None,
    historical: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    tenors: list[str] | None = None,
    include_benchmarks: bool = False,
    output_format: str = "parquet",
) -> list[Path]:
    _warn_legacy_path()
    """Run full JGB yields extraction workflow.

    Args:
        output_dir: Output directory
        historical: Extract historical data
        start_date: Start date for historical
        end_date: End date for historical
        tenors: List of tenors
        include_benchmarks: Include benchmark tickers
        output_format: 'parquet' or 'csv'

    Returns:
        List of output file paths
    """
    logger.info("Extracting JGB yields...")

    if historical:
        if start_date is None:
            raise ValueError("start_date is required for historical extraction")
        df = extract_jgb_yields_historical(
            start_date=start_date,
            end_date=end_date,
            tenors=tenors,
            include_benchmarks=include_benchmarks,
        )
    else:
        df = extract_jgb_yields_snapshot(
            tenors=tenors,
            include_benchmarks=include_benchmarks,
        )

    if df.empty:
        logger.warning("No JGB data to export")
        return []

    # Build output path
    filename = "jgb_yields"
    output_path = build_output_path("jgb", filename, output_dir)

    # Export
    if output_format == "csv":
        output_path = output_path.with_suffix(".csv")
        path = export_to_csv(df, output_path)
    else:
        path = export_to_parquet(df, output_path)

    return [path]
