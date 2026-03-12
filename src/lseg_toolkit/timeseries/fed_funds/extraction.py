"""
Fed Funds futures extraction from LSEG.

Provides functions for fetching Fed Funds futures data and storing it
with discrete contract labels and implied rates.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from lseg_toolkit.timeseries.calendars import get_lseg_cme_session_dates
from lseg_toolkit.timeseries.rolling import label_continuous_data
from lseg_toolkit.timeseries.stir_futures.contracts import get_front_month_contract

if TYPE_CHECKING:
    from lseg_toolkit.timeseries.client import LSEGDataClient

logger = logging.getLogger(__name__)

# Default fields for Fed Funds futures
# OPINT_1 = Open interest, IMP_YIELD = Implied yield (100 - price)
FF_DAILY_FIELDS = ["SETTLE", "OPINT_1", "ACVOL_UNS"]
FF_HOURLY_FIELDS = ["BID", "ASK", "TRDPRC_1", "HIGH_1", "LOW_1"]


def _add_daily_session_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add session_date for daily LSEG history rows."""
    result = df.copy()
    result["session_date"] = pd.Series(pd.to_datetime(result.index).date, index=result.index)
    return result


def _add_hourly_session_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add CME/LSEG session_date for hourly LSEG history rows."""
    result = df.copy()
    result["session_date"] = get_lseg_cme_session_dates(result.index)
    return result


def fetch_fed_funds_daily(
    client: LSEGDataClient,
    start: str | date,
    end: str | date,
    label_contracts: bool = True,
    compute_implied_rate: bool = True,
) -> pd.DataFrame:
    """
    Fetch Fed Funds daily continuous contract data.

    Args:
        client: LSEG data client instance.
        start: Start date (ISO format or date object).
        end: End date (ISO format or date object).
        label_contracts: If True, add source_contract column with discrete codes.
        compute_implied_rate: If True, add implied_rate = 100 - settle.

    Returns:
        DataFrame with columns:
        - settle: Settlement price
        - open_interest: Open interest
        - volume: Trading volume
        - source_contract: Discrete contract code (if label_contracts=True)
        - implied_rate: 100 - settle (if compute_implied_rate=True)

    Example:
        >>> client = LSEGDataClient()
        >>> df = fetch_fed_funds_daily(client, "2020-01-01", "2024-12-31")
        >>> df.head()
    """
    logger.info(f"Fetching FF daily data from {start} to {end}")

    df = client.get_history(
        rics="FFc1",
        start=start,
        end=end,
        fields=FF_DAILY_FIELDS,
        interval="daily",
    )

    if df.empty:
        logger.warning("No data returned for FFc1")
        return df

    # Normalize column names to lowercase
    df = df.rename(columns=str.lower)

    # Rename LSEG fields to our schema
    column_map = {
        "opint_1": "open_interest",
        "acvol_uns": "volume",
    }
    df = df.rename(columns=column_map)

    # Daily rows are already on the correct trade/session date.
    df = _add_daily_session_date(df)

    # Add implied rate
    if compute_implied_rate and "settle" in df.columns:
        df["implied_rate"] = 100.0 - df["settle"]

    # Persist a usable close for generic OHLCV storage.
    if "close" not in df.columns and "settle" in df.columns:
        df["close"] = df["settle"]

    # Label with discrete contract codes
    if label_contracts:
        df = label_continuous_data(df, lambda d: get_front_month_contract("FF", d))

    logger.info(f"Fetched {len(df)} daily rows for FFc1")
    return df


def fetch_fed_funds_hourly(
    client: LSEGDataClient,
    start: str | date,
    end: str | date,
    label_contracts: bool = True,
    compute_implied_rate: bool = True,
) -> pd.DataFrame:
    """
    Fetch Fed Funds hourly continuous contract data.

    Hourly data uses BID/ASK instead of SETTLE. We compute MID from these.

    Args:
        client: LSEG data client instance.
        start: Start date (ISO format or date object).
        end: End date (ISO format or date object).
        label_contracts: If True, add source_contract column with discrete codes.
        compute_implied_rate: If True, add implied_rate = 100 - mid.

    Returns:
        DataFrame with columns:
        - bid: Bid price
        - ask: Ask price
        - mid: (bid + ask) / 2
        - high: Intraday high
        - low: Intraday low
        - source_contract: Discrete contract code (if label_contracts=True)
        - implied_rate: 100 - mid (if compute_implied_rate=True)

    Example:
        >>> client = LSEGDataClient()
        >>> df = fetch_fed_funds_hourly(client, "2024-01-01", "2024-12-31")
    """
    logger.info(f"Fetching FF hourly data from {start} to {end}")

    df = client.get_history(
        rics="FFc1",
        start=start,
        end=end,
        fields=FF_HOURLY_FIELDS,
        interval="hourly",
    )

    if df.empty:
        logger.warning("No hourly data returned for FFc1")
        return df

    # Normalize column names to lowercase
    df = df.rename(columns=str.lower)

    # Rename LSEG fields to our schema
    column_map = {
        "trdprc_1": "last",
        "high_1": "high",
        "low_1": "low",
    }
    df = df.rename(columns=column_map)

    # Compute mid price from bid/ask
    if "bid" in df.columns and "ask" in df.columns:
        df["mid"] = (df["bid"] + df["ask"]) / 2

    # Hourly contract labeling must use session_date, not raw UTC calendar date.
    df = _add_hourly_session_date(df)

    # Add implied rate from mid
    if compute_implied_rate and "mid" in df.columns:
        df["implied_rate"] = 100.0 - df["mid"]

    # Persist a usable close for generic OHLCV storage/backtests.
    if "close" not in df.columns and "mid" in df.columns:
        df["close"] = df["mid"]

    # Label with discrete contract codes
    if label_contracts:
        df = label_continuous_data(df, lambda d: get_front_month_contract("FF", d))

    logger.info(f"Fetched {len(df)} hourly rows for FFc1")
    return df


def prepare_for_storage(
    df: pd.DataFrame,
    instrument_id: int,
    granularity: str = "daily",
) -> pd.DataFrame:
    """
    Prepare Fed Funds DataFrame for storage in timeseries_ohlcv table.

    Args:
        df: DataFrame from fetch_fed_funds_daily or fetch_fed_funds_hourly.
        instrument_id: The instrument ID from instruments table.
        granularity: "daily" or "hourly".

    Returns:
        DataFrame ready for insertion with columns matching timeseries_ohlcv schema.
    """
    result = df.copy()

    # Add required columns
    result["instrument_id"] = instrument_id
    result["granularity"] = granularity

    # Rename index to ts
    result = result.reset_index()
    if "Date" in result.columns:
        result = result.rename(columns={"Date": "ts"})
    elif "date" in result.columns:
        result = result.rename(columns={"date": "ts"})
    elif result.columns[0] not in ["ts", "instrument_id", "granularity"]:
        # Assume first column is the timestamp
        result = result.rename(columns={result.columns[0]: "ts"})

    # Ensure ts is timezone-aware
    result["ts"] = pd.to_datetime(result["ts"])
    if result["ts"].dt.tz is None:
        result["ts"] = result["ts"].dt.tz_localize("UTC")

    # Select columns that exist in schema
    schema_columns = [
        "instrument_id",
        "ts",
        "session_date",
        "granularity",
        "open",
        "high",
        "low",
        "close",
        "settle",
        "volume",
        "open_interest",
        "bid",
        "ask",
        "mid",
        "implied_rate",
        "source_contract",
    ]

    # Keep only columns that exist in both df and schema
    available = [c for c in schema_columns if c in result.columns]
    result = result[available]

    return result
