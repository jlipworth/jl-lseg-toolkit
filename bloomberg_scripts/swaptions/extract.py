"""Swaption volatility surface extraction."""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from bloomberg_scripts._legacy import warn_legacy_surface
from bloomberg_scripts.common.connection import BloombergSession
from bloomberg_scripts.common.export import build_output_path, export_to_parquet
from bloomberg_scripts.common.fields import SWAPTION_FIELDS

from .tickers import generate_swaption_tickers, parse_swaption_ticker

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def _warn_legacy_path() -> None:
    warn_legacy_surface(
        "bloomberg_scripts.swaptions",
        replacement=None,
        note='This research path is retained because Bloomberg Desktop API swaption access is still unresolved.',
        stacklevel=3,
    )


def extract_swaption_surface(
    session: BloombergSession,
    currency: str,
    expiries: list[str] | None = None,
    tenors: list[str] | None = None,
    fields: list[str] | None = None,
) -> pd.DataFrame:
    _warn_legacy_path()
    """Extract swaption volatility surface as a pivot table.

    Args:
        session: Connected Bloomberg session
        currency: Currency code (USD, EUR, GBP)
        expiries: Option expiries (default: standard grid)
        tenors: Swap tenors (default: standard grid)
        fields: Bloomberg fields to retrieve

    Returns:
        DataFrame with expiry as index, tenor as columns, PX_LAST values
    """
    if fields is None:
        fields = SWAPTION_FIELDS

    tickers = generate_swaption_tickers(currency, expiries, tenors)
    logger.info("Extracting %d swaption points for %s", len(tickers), currency)

    # Get reference data
    df = session.get_reference_data(tickers, fields)

    # Parse tickers to get expiry/tenor
    records = []
    for ticker in df.index:
        parsed = parse_swaption_ticker(ticker)
        row = {
            "ticker": ticker,
            "currency": parsed["currency"],
            "expiry": parsed["expiry"],
            "tenor": parsed["tenor"],
        }
        for field in fields:
            if field in df.columns:
                row[field] = df.loc[ticker, field]
        records.append(row)

    result = pd.DataFrame(records)

    # Create pivot table (expiry x tenor)
    if "PX_LAST" in result.columns:
        pivot = result.pivot(index="expiry", columns="tenor", values="PX_LAST")

        # Sort by standard order
        expiry_order = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"]
        tenor_order = ["2Y", "5Y", "10Y", "30Y"]

        existing_expiries = [e for e in expiry_order if e in pivot.index]
        existing_tenors = [t for t in tenor_order if t in pivot.columns]

        pivot = pivot.loc[existing_expiries, existing_tenors]
        return pivot

    return result


def extract_swaption_surface_historical(
    session: BloombergSession,
    currency: str,
    start_date: date,
    end_date: date | None = None,
    expiries: list[str] | None = None,
    tenors: list[str] | None = None,
) -> pd.DataFrame:
    _warn_legacy_path()
    """Extract historical swaption volatility data.

    Args:
        session: Connected Bloomberg session
        currency: Currency code
        start_date: Start date for historical data
        end_date: End date (default: today)
        expiries: Option expiries
        tenors: Swap tenors

    Returns:
        DataFrame with MultiIndex (date, ticker) and PX_LAST values
    """
    if end_date is None:
        end_date = date.today()

    tickers = generate_swaption_tickers(currency, expiries, tenors)
    logger.info(
        "Extracting historical swaptions for %s from %s to %s",
        currency,
        start_date,
        end_date,
    )

    # Historical data request
    df = session.get_historical_data(
        tickers,
        ["PX_LAST"],
        start_date,
        end_date,
    )

    if df.empty:
        return df

    # Add parsed ticker info
    df = df.reset_index()

    parsed_data = []
    for ticker in df["security"].unique():
        parsed = parse_swaption_ticker(ticker)
        parsed["ticker"] = ticker
        parsed_data.append(parsed)

    parsed_df = pd.DataFrame(parsed_data)
    df = df.merge(parsed_df, left_on="security", right_on="ticker", how="left")

    return df


def run_swaption_extraction(
    currency: str | list[str],
    output_dir: Path | None = None,
    historical: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    output_format: str = "parquet",
) -> list[Path]:
    _warn_legacy_path()
    """Run swaption extraction and export to file.

    Args:
        currency: Currency code or list of codes (or "all")
        output_dir: Output directory
        historical: Extract historical data
        start_date: Start date for historical
        end_date: End date for historical
        output_format: Output format (parquet, csv)

    Returns:
        List of output file paths
    """
    from bloomberg_scripts.common.export import export_to_csv
    from bloomberg_scripts.common.fields import SWAPTION_CURRENCY_PREFIXES

    # Handle "all" or list of currencies
    if currency == "all":
        currencies = list(SWAPTION_CURRENCY_PREFIXES.keys())
    elif isinstance(currency, str):
        currencies = [currency]
    else:
        currencies = list(currency)

    output_paths = []

    with BloombergSession() as session:
        for ccy in currencies:
            logger.info("Processing %s swaptions", ccy)

            if historical:
                if start_date is None:
                    raise ValueError("start_date required for historical extraction")

                df = extract_swaption_surface_historical(
                    session,
                    ccy,
                    start_date,
                    end_date,
                )
                name = f"{ccy.lower()}_swaption_vol_historical"
            else:
                df = extract_swaption_surface(session, ccy)
                name = f"{ccy.lower()}_swaption_vol"

            # Export
            base_path = build_output_path("swaptions", name, output_dir)

            if output_format == "csv":
                path = export_to_csv(df, base_path.with_suffix(".csv"))
            else:
                path = export_to_parquet(df, base_path)

            output_paths.append(path)
            logger.info("Exported %s to %s", ccy, path)

    return output_paths
