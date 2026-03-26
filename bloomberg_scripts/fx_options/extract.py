"""Extract FX options data (risk reversals and butterflies) from Bloomberg."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from .._legacy import warn_legacy_surface
from ..common.connection import BloombergSession
from ..common.export import build_output_path, export_to_csv, export_to_parquet
from ..common.fields import FX_OPTION_FIELDS

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _warn_legacy_path() -> None:
    warn_legacy_surface(
        "bloomberg_scripts.fx_options",
        replacement='bbg-extract fx-atm-vol',
        note='This research path targets RR/BF discovery and may be structurally broken with the legacy common session wrapper.',
        stacklevel=3,
    )

# Default currency pairs
DEFAULT_PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "AUDUSD"]

# Standard tenors for FX options
DEFAULT_TENORS = ["1W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y"]

# Delta levels
DEFAULT_DELTAS = ["25", "10"]


def generate_fx_option_tickers(
    pairs: list[str] | None = None,
    tenors: list[str] | None = None,
    deltas: list[str] | None = None,
) -> dict[str, list[str]]:
    """Generate Bloomberg tickers for FX risk reversals and butterflies.

    Args:
        pairs: Currency pairs (e.g., ['EURUSD', 'USDJPY'])
        tenors: Option tenors (e.g., ['1M', '3M', '1Y'])
        deltas: Delta levels (e.g., ['25', '10'])

    Returns:
        Dict with 'risk_reversals' and 'butterflies' ticker lists
    """
    if pairs is None:
        pairs = DEFAULT_PAIRS
    if tenors is None:
        tenors = DEFAULT_TENORS
    if deltas is None:
        deltas = DEFAULT_DELTAS

    risk_reversals = []
    butterflies = []

    for pair in pairs:
        for tenor in tenors:
            for delta in deltas:
                # Risk Reversal: EURUSD1MRR25 BGN Curncy
                rr_ticker = f"{pair}{tenor}{delta}RR BGN Curncy"
                risk_reversals.append(rr_ticker)

                # Butterfly: EURUSD1MBF25 BGN Curncy
                bf_ticker = f"{pair}{tenor}{delta}BF BGN Curncy"
                butterflies.append(bf_ticker)

    return {
        "risk_reversals": risk_reversals,
        "butterflies": butterflies,
    }


def _parse_fx_ticker(ticker: str) -> dict:
    """Parse FX option ticker to extract components.

    Args:
        ticker: Bloomberg ticker like 'EURUSD1M25RR BGN Curncy'

    Returns:
        Dict with pair, tenor, delta, instrument_type
    """
    import re

    # Pattern: EURUSD1M25RR or EURUSD1M25BF
    match = re.match(r"([A-Z]{6})(\d+[WMY])(\d+)(RR|BF)", ticker)
    if match:
        return {
            "pair": match.group(1),
            "tenor": match.group(2),
            "delta": match.group(3),
            "instrument_type": "risk_reversal" if match.group(4) == "RR" else "butterfly",
        }
    return {"pair": "", "tenor": "", "delta": "", "instrument_type": ""}


def extract_fx_options_snapshot(
    pairs: list[str] | None = None,
    tenors: list[str] | None = None,
    deltas: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    _warn_legacy_path()
    """Extract current FX options data.

    Args:
        pairs: Currency pairs
        tenors: Option tenors
        deltas: Delta levels

    Returns:
        Tuple of (risk_reversals_df, butterflies_df)
    """
    ticker_dict = generate_fx_option_tickers(pairs, tenors, deltas)

    with BloombergSession() as session:
        # Get risk reversals
        rr_df = session.get_reference_data(
            ticker_dict["risk_reversals"],
            FX_OPTION_FIELDS,
        )

        # Get butterflies
        bf_df = session.get_reference_data(
            ticker_dict["butterflies"],
            FX_OPTION_FIELDS,
        )

    # Add parsed metadata
    for df in [rr_df, bf_df]:
        if not df.empty:
            parsed = df["ticker"].apply(_parse_fx_ticker)
            df["pair"] = parsed.apply(lambda x: x["pair"])
            df["tenor"] = parsed.apply(lambda x: x["tenor"])
            df["delta"] = parsed.apply(lambda x: x["delta"])
            df["instrument_type"] = parsed.apply(lambda x: x["instrument_type"])
            df["extract_date"] = date.today()

    return rr_df, bf_df


def extract_fx_options_historical(
    start_date: date,
    end_date: date | None = None,
    pairs: list[str] | None = None,
    tenors: list[str] | None = None,
    deltas: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    _warn_legacy_path()
    """Extract historical FX options data.

    Args:
        start_date: Start date for historical data
        end_date: End date (default: today)
        pairs: Currency pairs
        tenors: Option tenors
        deltas: Delta levels

    Returns:
        Tuple of (risk_reversals_df, butterflies_df)
    """
    if end_date is None:
        end_date = date.today()

    ticker_dict = generate_fx_option_tickers(pairs, tenors, deltas)

    with BloombergSession() as session:
        # Get risk reversals
        rr_df = session.get_historical_data(
            ticker_dict["risk_reversals"],
            ["PX_LAST"],
            start_date,
            end_date,
        )

        # Get butterflies
        bf_df = session.get_historical_data(
            ticker_dict["butterflies"],
            ["PX_LAST"],
            start_date,
            end_date,
        )

    # Add parsed metadata
    for df in [rr_df, bf_df]:
        if not df.empty:
            parsed = df["ticker"].apply(_parse_fx_ticker)
            df["pair"] = parsed.apply(lambda x: x["pair"])
            df["tenor"] = parsed.apply(lambda x: x["tenor"])
            df["delta"] = parsed.apply(lambda x: x["delta"])
            df["instrument_type"] = parsed.apply(lambda x: x["instrument_type"])

    return rr_df, bf_df


def run_fx_options_extraction(
    pairs: list[str] | None = None,
    output_dir: Path | None = None,
    historical: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    tenors: list[str] | None = None,
    deltas: list[str] | None = None,
    output_format: str = "parquet",
) -> list[Path]:
    _warn_legacy_path()
    """Run full FX options extraction workflow.

    Args:
        pairs: Currency pairs or None for defaults
        output_dir: Output directory
        historical: Extract historical data
        start_date: Start date for historical
        end_date: End date for historical
        tenors: Option tenors
        deltas: Delta levels
        output_format: 'parquet' or 'csv'

    Returns:
        List of output file paths
    """
    logger.info("Extracting FX options (risk reversals and butterflies)...")

    if historical:
        if start_date is None:
            raise ValueError("start_date is required for historical extraction")
        rr_df, bf_df = extract_fx_options_historical(
            start_date=start_date,
            end_date=end_date,
            pairs=pairs,
            tenors=tenors,
            deltas=deltas,
        )
    else:
        rr_df, bf_df = extract_fx_options_snapshot(
            pairs=pairs,
            tenors=tenors,
            deltas=deltas,
        )

    output_paths = []

    # Export risk reversals
    if not rr_df.empty:
        rr_path = build_output_path("fx_options", "fx_risk_reversals", output_dir)
        if output_format == "csv":
            rr_path = rr_path.with_suffix(".csv")
            path = export_to_csv(rr_df, rr_path)
        else:
            path = export_to_parquet(rr_df, rr_path)
        output_paths.append(path)
    else:
        logger.warning("No risk reversal data to export")

    # Export butterflies
    if not bf_df.empty:
        bf_path = build_output_path("fx_options", "fx_butterflies", output_dir)
        if output_format == "csv":
            bf_path = bf_path.with_suffix(".csv")
            path = export_to_csv(bf_df, bf_path)
        else:
            path = export_to_parquet(bf_df, bf_path)
        output_paths.append(path)
    else:
        logger.warning("No butterfly data to export")

    return output_paths
