"""
Supported Bloomberg FX ATM implied volatility workflow.
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


DEFAULT_PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCHF", "USDCAD"]
DEFAULT_TENORS = ["1W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y"]
FX_ATM_VOL_FIELDS = ["PX_LAST", "NAME", "LAST_UPDATE"]
FX_ATM_VOL_SOURCE = "bloomberg"
FX_ATM_VOL_QUOTE_TYPE = "atm_vol"


def _normalize_pairs(pairs: Sequence[str] | None = None) -> list[str]:
    if pairs is None:
        return list(DEFAULT_PAIRS)

    normalized = [pair.upper() for pair in pairs]
    invalid = [pair for pair in normalized if pair not in DEFAULT_PAIRS]
    if invalid:
        valid = ", ".join(DEFAULT_PAIRS)
        invalid_str = ", ".join(invalid)
        raise ConfigurationError(
            f"Unsupported FX ATM vol pair(s): {invalid_str}. Valid pairs: {valid}."
        )

    return normalized


def _normalize_tenors(tenors: Sequence[str] | None = None) -> list[str]:
    if tenors is None:
        return list(DEFAULT_TENORS)

    normalized = [tenor.upper() for tenor in tenors]
    invalid = [tenor for tenor in normalized if tenor not in DEFAULT_TENORS]
    if invalid:
        valid = ", ".join(DEFAULT_TENORS)
        invalid_str = ", ".join(invalid)
        raise ConfigurationError(
            f"Unsupported FX ATM vol tenor(s): {invalid_str}. Valid tenors: {valid}."
        )

    return normalized


def generate_fx_atm_vol_tickers(
    pairs: Sequence[str] | None = None,
    tenors: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    """Generate supported Bloomberg FX ATM vol tickers."""
    normalized_pairs = _normalize_pairs(pairs)
    normalized_tenors = _normalize_tenors(tenors)

    tickers: list[dict[str, str]] = []
    for pair in normalized_pairs:
        for tenor in normalized_tenors:
            tickers.append(
                {
                    "ticker": f"{pair}V{tenor} BGN Curncy",
                    "pair": pair,
                    "tenor": tenor,
                }
            )
    return tickers


def _sort_surface(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    pair_rank = {pair: i for i, pair in enumerate(DEFAULT_PAIRS)}
    tenor_rank = {tenor: i for i, tenor in enumerate(DEFAULT_TENORS)}

    result = df.copy()
    result["_pair_rank"] = result["pair"].map(pair_rank)
    result["_tenor_rank"] = result["tenor"].map(tenor_rank)

    sort_columns = ["_pair_rank", "_tenor_rank"]
    if "date" in result.columns:
        sort_columns = ["date", "_pair_rank", "_tenor_rank"]

    result = result.sort_values(sort_columns).drop(
        columns=["_pair_rank", "_tenor_rank"]
    )
    return result.reset_index(drop=True)


def extract_fx_atm_vol_snapshot(
    pairs: Sequence[str] | None = None,
    tenors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch current FX ATM implied vol from Bloomberg."""
    ticker_info = generate_fx_atm_vol_tickers(pairs=pairs, tenors=tenors)
    ticker_map = {item["ticker"]: item for item in ticker_info}

    with BloombergSession() as session:
        df = session.get_reference_data(
            list(ticker_map.keys()),
            FX_ATM_VOL_FIELDS,
        )

    if df.empty:
        return df

    rows: list[dict[str, object]] = []
    for _, row in df.iterrows():
        ticker = row["security"]
        info = ticker_map.get(ticker, {})
        if pd.isna(row.get("PX_LAST")):
            continue

        rows.append(
            {
                "pair": info.get("pair", ""),
                "tenor": info.get("tenor", ""),
                "atm_vol": row.get("PX_LAST"),
                "name": row.get("NAME"),
                "last_update": row.get("LAST_UPDATE"),
                "source": FX_ATM_VOL_SOURCE,
                "quote_type": FX_ATM_VOL_QUOTE_TYPE,
                "ticker": ticker,
                "_security_error": row.get("_security_error"),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    result = add_extraction_metadata(result)
    result = _sort_surface(result)
    columns = [
        "pair",
        "tenor",
        "atm_vol",
        "name",
        "last_update",
        "source",
        "quote_type",
        "ticker",
        "extract_date",
        "_security_error",
    ]
    return result[[column for column in columns if column in result.columns]]


def extract_fx_atm_vol_historical(
    start_date: date,
    end_date: date | None = None,
    pairs: Sequence[str] | None = None,
    tenors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Fetch historical FX ATM implied vol from Bloomberg."""
    ticker_info = generate_fx_atm_vol_tickers(pairs=pairs, tenors=tenors)
    ticker_map = {item["ticker"]: item for item in ticker_info}

    with BloombergSession() as session:
        df = session.get_historical_data(
            list(ticker_map.keys()),
            ["PX_LAST"],
            start_date=start_date,
            end_date=end_date,
        )

    if df.empty:
        return df

    rows: list[dict[str, object]] = []
    for _, row in df.iterrows():
        ticker = row["security"]
        info = ticker_map.get(ticker, {})
        rows.append(
            {
                "date": row.get("date"),
                "pair": info.get("pair", ""),
                "tenor": info.get("tenor", ""),
                "atm_vol": row.get("PX_LAST"),
                "source": FX_ATM_VOL_SOURCE,
                "quote_type": FX_ATM_VOL_QUOTE_TYPE,
                "ticker": ticker,
                "_security_error": row.get("_security_error"),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    result = _sort_surface(result)
    columns = [
        "date",
        "pair",
        "tenor",
        "atm_vol",
        "source",
        "quote_type",
        "ticker",
        "_security_error",
    ]
    return result[[column for column in columns if column in result.columns]]
