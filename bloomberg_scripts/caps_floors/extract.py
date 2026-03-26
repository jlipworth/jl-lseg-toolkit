"""Extract interest rate caps/floors data from Bloomberg."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from .._legacy import warn_legacy_surface
from ..common.connection import BloombergSession
from ..common.export import build_output_path, export_to_csv, export_to_parquet
from ..common.fields import CAP_FLOOR_FIELDS

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _warn_legacy_path() -> None:
    warn_legacy_surface(
        "bloomberg_scripts.caps_floors",
        replacement=None,
        note='This research path is retained because Bloomberg caps/floors tickers are not yet validated.',
        stacklevel=3,
    )

# Standard tenors for caps/floors
DEFAULT_TENORS = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]

# Strike offsets (basis points from ATM)
DEFAULT_STRIKES = ["-100", "-50", "ATM", "+50", "+100", "+150", "+200"]

# Currency configurations
CURRENCY_CONFIG = {
    "USD": {
        "rate": "SOFR",
        "ticker_prefix": "USCP",
        "source": "ICAP",
    },
    "EUR": {
        "rate": "ESTR",
        "ticker_prefix": "EUCP",
        "source": "ICAP",
    },
    "GBP": {
        "rate": "SONIA",
        "ticker_prefix": "BPCP",
        "source": "ICAP",
    },
}


def generate_cap_floor_tickers(
    currency: str,
    tenors: list[str] | None = None,
    strikes: list[str] | None = None,
    instrument_type: str = "cap",
) -> list[str]:
    """Generate Bloomberg tickers for caps or floors.

    Args:
        currency: Currency code (USD, EUR, GBP)
        tenors: List of tenors (default: 1Y to 30Y)
        strikes: List of strike offsets (default: -100bp to +200bp)
        instrument_type: 'cap' or 'floor'

    Returns:
        List of Bloomberg tickers
    """
    if tenors is None:
        tenors = DEFAULT_TENORS
    if strikes is None:
        strikes = DEFAULT_STRIKES

    config = CURRENCY_CONFIG.get(currency.upper())
    if config is None:
        raise ValueError(f"Unsupported currency: {currency}. Supported: {list(CURRENCY_CONFIG.keys())}")

    prefix = config["ticker_prefix"]
    source = config["source"]

    # Adjust prefix for floors
    if instrument_type.lower() == "floor":
        prefix = prefix.replace("CP", "FL")

    tickers = []
    for tenor in tenors:
        for strike in strikes:
            if strike == "ATM":
                # ATM ticker: USCP5YA ICAP Curncy
                ticker = f"{prefix}{tenor}A {source} Curncy"
            else:
                # Struck ticker: USCP5Y+150 ICAP Curncy
                ticker = f"{prefix}{tenor}{strike} {source} Curncy"
            tickers.append(ticker)

    return tickers


def extract_caps_floors_snapshot(
    currency: str,
    tenors: list[str] | None = None,
    strikes: list[str] | None = None,
    instrument_type: str = "cap",
) -> pd.DataFrame:
    _warn_legacy_path()
    """Extract current caps/floors data.

    Args:
        currency: Currency code
        tenors: List of tenors
        strikes: List of strike offsets
        instrument_type: 'cap' or 'floor'

    Returns:
        DataFrame with volatility data pivoted by tenor and strike
    """
    if tenors is None:
        tenors = DEFAULT_TENORS
    if strikes is None:
        strikes = DEFAULT_STRIKES

    tickers = generate_cap_floor_tickers(currency, tenors, strikes, instrument_type)

    with BloombergSession() as session:
        df = session.get_reference_data(tickers, CAP_FLOOR_FIELDS)

    if df.empty:
        logger.warning("No data returned for %s %ss", currency, instrument_type)
        return df

    # Parse ticker to extract tenor and strike
    df["tenor"] = df["ticker"].apply(_parse_tenor)
    df["strike"] = df["ticker"].apply(_parse_strike)
    df["currency"] = currency.upper()
    df["instrument_type"] = instrument_type
    df["extract_date"] = date.today()

    return df


def _parse_tenor(ticker: str) -> str:
    """Extract tenor from ticker like 'USCP5Y+150 ICAP Curncy' -> '5Y'."""
    import re

    # Match pattern like USCP5Y or EUCP10Y
    match = re.search(r"[A-Z]{4}(\d+Y)", ticker)
    if match:
        return match.group(1)
    return ""


def _parse_strike(ticker: str) -> str:
    """Extract strike from ticker like 'USCP5Y+150 ICAP Curncy' -> '+150'."""
    import re

    # Check for ATM
    if re.search(r"\d+YA\s", ticker):
        return "ATM"

    # Match strike offset like +150 or -50
    match = re.search(r"(\d+Y)([+-]\d+)", ticker)
    if match:
        return match.group(2)
    return ""


def extract_caps_floors_historical(
    currency: str,
    start_date: date,
    end_date: date | None = None,
    tenors: list[str] | None = None,
    strikes: list[str] | None = None,
    instrument_type: str = "cap",
) -> pd.DataFrame:
    _warn_legacy_path()
    """Extract historical caps/floors data.

    Args:
        currency: Currency code
        start_date: Start date for historical data
        end_date: End date (default: today)
        tenors: List of tenors
        strikes: List of strike offsets
        instrument_type: 'cap' or 'floor'

    Returns:
        DataFrame with historical volatility data
    """
    if end_date is None:
        end_date = date.today()
    if tenors is None:
        tenors = DEFAULT_TENORS
    if strikes is None:
        strikes = DEFAULT_STRIKES

    tickers = generate_cap_floor_tickers(currency, tenors, strikes, instrument_type)

    with BloombergSession() as session:
        df = session.get_historical_data(
            tickers,
            ["PX_LAST"],
            start_date,
            end_date,
        )

    if df.empty:
        logger.warning("No historical data returned for %s %ss", currency, instrument_type)
        return df

    # Parse ticker metadata
    df["tenor"] = df["ticker"].apply(_parse_tenor)
    df["strike"] = df["ticker"].apply(_parse_strike)
    df["currency"] = currency.upper()
    df["instrument_type"] = instrument_type

    return df


def run_caps_floors_extraction(
    currency: str = "USD",
    output_dir: Path | None = None,
    historical: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    instrument_type: str = "cap",
    output_format: str = "parquet",
) -> list[Path]:
    _warn_legacy_path()
    """Run full caps/floors extraction workflow.

    Args:
        currency: Currency code or 'all'
        output_dir: Output directory
        historical: Extract historical data
        start_date: Start date for historical
        end_date: End date for historical
        instrument_type: 'cap', 'floor', or 'both'
        output_format: 'parquet' or 'csv'

    Returns:
        List of output file paths
    """
    currencies = list(CURRENCY_CONFIG.keys()) if currency.lower() == "all" else [currency.upper()]
    instrument_types = ["cap", "floor"] if instrument_type.lower() == "both" else [instrument_type.lower()]

    output_paths = []

    for ccy in currencies:
        for inst_type in instrument_types:
            logger.info("Extracting %s %ss...", ccy, inst_type)

            if historical:
                df = extract_caps_floors_historical(
                    ccy,
                    start_date=start_date,
                    end_date=end_date,
                    instrument_type=inst_type,
                )
            else:
                df = extract_caps_floors_snapshot(ccy, instrument_type=inst_type)

            if df.empty:
                logger.warning("No data for %s %ss, skipping export", ccy, inst_type)
                continue

            # Build output path
            config = CURRENCY_CONFIG[ccy]
            rate = config["rate"].lower()
            filename = f"{ccy.lower()}_{rate}_{inst_type}s"
            output_path = build_output_path("caps_floors", filename, output_dir)

            # Export
            if output_format == "csv":
                output_path = output_path.with_suffix(".csv")
                path = export_to_csv(df, output_path)
            else:
                path = export_to_parquet(df, output_path)

            output_paths.append(path)

    return output_paths
