"""
Supported Bloomberg JGB yields workflow.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from lseg_toolkit.exceptions import ConfigurationError

from .connection import BloombergSession
from .normalize import add_extraction_metadata

if TYPE_CHECKING:
    from collections.abc import Sequence


JGB_TICKERS = {
    "1Y": "GJGB1 Index",
    "2Y": "GJGB2 Index",
    "3Y": "GJGB3 Index",
    "4Y": "GJGB4 Index",
    "5Y": "GJGB5 Index",
    "6Y": "GJGB6 Index",
    "7Y": "GJGB7 Index",
    "8Y": "GJGB8 Index",
    "9Y": "GJGB9 Index",
    "10Y": "GJGB10 Index",
    "15Y": "GJGB15 Index",
    "20Y": "GJGB20 Index",
    "25Y": "GJGB25 Index",
    "30Y": "GJGB30 Index",
    "40Y": "GJGB40 Index",
}
JGB_FIELDS = ["PX_LAST", "NAME", "LAST_UPDATE"]
JGB_TENOR_ORDER = list(JGB_TICKERS)
JGB_CURRENCY = "JPY"
JGB_INSTRUMENT = "jgb_yield"
JGB_SOURCE = "bloomberg"


def _normalize_requested_tenors(tenors: Sequence[str] | None = None) -> list[str]:
    """Validate and normalize supported JGB tenors."""
    if tenors is None:
        return list(JGB_TENOR_ORDER)

    normalized = [tenor.upper() for tenor in tenors]
    invalid = [tenor for tenor in normalized if tenor not in JGB_TICKERS]
    if invalid:
        valid = ", ".join(JGB_TENOR_ORDER)
        invalid_str = ", ".join(invalid)
        raise ConfigurationError(
            f"Unsupported JGB tenor(s): {invalid_str}. Valid tenors: {valid}."
        )

    return normalized


def get_jgb_tickers(tenors: Sequence[str] | None = None) -> dict[str, str]:
    """Return the configured JGB tickers for the requested tenors."""
    normalized_tenors = _normalize_requested_tenors(tenors)
    return {tenor: JGB_TICKERS[tenor] for tenor in normalized_tenors}


def _sort_by_tenor(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "tenor" not in df.columns:
        return df

    tenor_rank = {tenor: i for i, tenor in enumerate(JGB_TENOR_ORDER)}
    result = df.copy()
    result["_tenor_rank"] = result["tenor"].map(tenor_rank)

    sort_columns = ["_tenor_rank"]
    if "date" in result.columns:
        sort_columns = ["date", "_tenor_rank"]

    result = result.sort_values(sort_columns).drop(columns=["_tenor_rank"])
    return result.reset_index(drop=True)


def extract_jgb_snapshot(tenors: Sequence[str] | None = None) -> pd.DataFrame:
    """Fetch current JGB yields from Bloomberg."""
    ticker_map = get_jgb_tickers(tenors)
    reverse_map = {ticker: tenor for tenor, ticker in ticker_map.items()}

    with BloombergSession() as session:
        df = session.get_reference_data(list(ticker_map.values()), JGB_FIELDS)

    if df.empty:
        return df

    result = df.copy()
    result["ticker"] = result["security"]
    result["tenor"] = result["ticker"].map(reverse_map)
    result["yield"] = result["PX_LAST"]
    result["name"] = result["NAME"]
    result["last_update"] = result["LAST_UPDATE"]
    result["currency"] = JGB_CURRENCY
    result["instrument"] = JGB_INSTRUMENT
    result["source"] = JGB_SOURCE
    result = add_extraction_metadata(result)
    result = _sort_by_tenor(result)

    columns = [
        "tenor",
        "yield",
        "name",
        "last_update",
        "currency",
        "instrument",
        "source",
        "ticker",
        "extract_date",
        "_security_error",
    ]
    return result[[column for column in columns if column in result.columns]]



def extract_jgb_historical(
    start_date: date,
    end_date: date | None = None,
    tenors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch historical JGB yields from Bloomberg."""
    ticker_map = get_jgb_tickers(tenors)
    reverse_map = {ticker: tenor for tenor, ticker in ticker_map.items()}

    with BloombergSession() as session:
        df = session.get_historical_data(
            list(ticker_map.values()),
            ["PX_LAST"],
            start_date=start_date,
            end_date=end_date,
        )

    if df.empty:
        return df

    result = df.copy()
    result["ticker"] = result["security"]
    result["tenor"] = result["ticker"].map(reverse_map)
    result["yield"] = result["PX_LAST"]
    result["currency"] = JGB_CURRENCY
    result["instrument"] = JGB_INSTRUMENT
    result["source"] = JGB_SOURCE
    result = _sort_by_tenor(result)

    columns = [
        "date",
        "tenor",
        "yield",
        "currency",
        "instrument",
        "source",
        "ticker",
        "_security_error",
    ]
    return result[[column for column in columns if column in result.columns]]
