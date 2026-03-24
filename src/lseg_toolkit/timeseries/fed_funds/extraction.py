"""
Fed Funds futures extraction from LSEG.

Provides functions for fetching Fed Funds futures data and storing it
with discrete contract labels and implied rates.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from lseg_toolkit.timeseries.calendars import get_lseg_cme_session_dates
from lseg_toolkit.timeseries.rolling import label_continuous_data
from lseg_toolkit.timeseries.stir_futures.contracts import (
    get_continuous_rank_contract,
    get_continuous_ric,
)

if TYPE_CHECKING:
    from lseg_toolkit.timeseries.client import LSEGDataClient

logger = logging.getLogger(__name__)

# Default fields for Fed Funds futures
# OPINT_1 = Open interest, IMP_YIELD = Implied yield (100 - price)
FF_DAILY_FIELDS = ["SETTLE", "OPINT_1", "ACVOL_UNS"]
FF_HOURLY_FIELDS = ["BID", "ASK", "TRDPRC_1", "HIGH_1", "LOW_1"]
FF_CONTINUOUS_SYMBOL_PATTERN = re.compile(
    r"^FF_CONTINUOUS(?:_(\d{1,2}))?$", re.IGNORECASE
)
FF_CONTINUOUS_RIC_PATTERN = re.compile(r"^FFc(\d{1,2})$", re.IGNORECASE)


def _validate_rank(rank: int) -> int:
    """Validate a Fed Funds continuous rank."""
    if rank < 1:
        raise ValueError(f"rank must be >= 1, got {rank}")
    return rank


def get_ff_continuous_symbol(rank: int = 1) -> str:
    """Return the canonical internal symbol for a Fed Funds continuous rank."""
    rank = _validate_rank(rank)
    return "FF_CONTINUOUS" if rank == 1 else f"FF_CONTINUOUS_{rank}"


def _get_rank_ric(rank: int) -> str:
    """Get the LSEG continuous RIC for a Fed Funds rank."""
    return get_continuous_ric("FF", month=_validate_rank(rank))


def parse_ff_continuous_rank(symbol: str) -> int | None:
    """
    Parse a Fed Funds continuous rank from an internal symbol or LSEG RIC.

    Supported inputs:
    - FF_CONTINUOUS
    - FF_CONTINUOUS_2
    - FF
    - ZQ
    - FFc3
    """
    symbol_upper = symbol.upper()
    if symbol_upper in {"FF", "ZQ"}:
        return 1

    symbol_match = FF_CONTINUOUS_SYMBOL_PATTERN.match(symbol_upper)
    if symbol_match:
        return int(symbol_match.group(1) or 1)

    ric_match = FF_CONTINUOUS_RIC_PATTERN.match(symbol)
    if ric_match:
        return int(ric_match.group(1))

    return None


def _add_daily_session_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add session_date for daily LSEG history rows."""
    result = df.copy()
    result["session_date"] = pd.Series(
        pd.to_datetime(result.index).date, index=result.index
    )
    return result


def _add_hourly_session_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add CME/LSEG session_date for hourly LSEG history rows."""
    result = df.copy()
    result["session_date"] = get_lseg_cme_session_dates(result.index)
    return result


def _drop_rows_without_close(df: pd.DataFrame, ric: str) -> pd.DataFrame:
    """Drop rows that still lack any usable close/price value."""
    if "close" not in df.columns:
        return df

    missing_close = df["close"].isna()
    if not missing_close.any():
        return df

    dropped = int(missing_close.sum())
    logger.warning(f"Dropping {dropped} {ric} rows without usable close price")
    return df.loc[~missing_close].copy()


def fetch_fed_funds_daily(
    client: LSEGDataClient,
    start: str | date,
    end: str | date,
    rank: int = 1,
    label_contracts: bool = True,
    compute_implied_rate: bool = True,
) -> pd.DataFrame:
    """
    Fetch Fed Funds daily continuous contract data.

    Args:
        client: LSEG data client instance.
        start: Start date (ISO format or date object).
        end: End date (ISO format or date object).
        rank: Continuous rank to fetch (1=FFc1, 2=FFc2, ...).
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
    ric = _get_rank_ric(rank)
    logger.info(f"Fetching {ric} daily data from {start} to {end}")

    df = client.get_history(
        rics=ric,
        start=start,
        end=end,
        fields=FF_DAILY_FIELDS,
        interval="daily",
    )

    if df.empty:
        logger.warning(f"No data returned for {ric}")
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

    df = _drop_rows_without_close(df, ric)

    # Label with discrete contract codes
    if label_contracts:
        df = label_continuous_data(
            df,
            lambda d: get_continuous_rank_contract("FF", d, rank=rank),
        )

    logger.info(f"Fetched {len(df)} daily rows for {ric}")
    return df


def fetch_fed_funds_hourly(
    client: LSEGDataClient,
    start: str | date,
    end: str | date,
    rank: int = 1,
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
        rank: Continuous rank to fetch (1=FFc1, 2=FFc2, ...).
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
    ric = _get_rank_ric(rank)
    logger.info(f"Fetching {ric} hourly data from {start} to {end}")

    df = client.get_history(
        rics=ric,
        start=start,
        end=end,
        fields=FF_HOURLY_FIELDS,
        interval="hourly",
    )

    if df.empty:
        logger.warning(f"No hourly data returned for {ric}")
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
    if "close" not in df.columns and "last" in df.columns:
        df["close"] = df["last"]

    df = _drop_rows_without_close(df, ric)

    # Label with discrete contract codes
    if label_contracts:
        df = label_continuous_data(
            df,
            lambda d: get_continuous_rank_contract("FF", d, rank=rank),
        )

    logger.info(f"Fetched {len(df)} hourly rows for {ric}")
    return df


def fetch_fed_funds_strip(
    client: LSEGDataClient,
    start: str | date,
    end: str | date,
    ranks: Iterable[int] = range(1, 13),
    interval: str = "daily",
    label_contracts: bool = True,
    compute_implied_rate: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Fetch a strip of Fed Funds continuous ranks.

    This is intentionally lightweight scaffolding for scraping FFc1..FFcN
    without yet committing to a storage model.

    Args:
        client: LSEG data client instance.
        start: Start date (ISO format or date object).
        end: End date (ISO format or date object).
        ranks: Continuous ranks to fetch.
        interval: "daily" or "hourly".
        label_contracts: If True, add source_contract labels.
        compute_implied_rate: If True, compute implied rates.

    Returns:
        Mapping of continuous RIC (e.g. ``FFc3``) to fetched DataFrame.
    """
    results: dict[str, pd.DataFrame] = {}

    for rank in ranks:
        ric = _get_rank_ric(rank)
        if interval == "daily":
            results[ric] = fetch_fed_funds_daily(
                client,
                start,
                end,
                rank=rank,
                label_contracts=label_contracts,
                compute_implied_rate=compute_implied_rate,
            )
        elif interval == "hourly":
            results[ric] = fetch_fed_funds_hourly(
                client,
                start,
                end,
                rank=rank,
                label_contracts=label_contracts,
                compute_implied_rate=compute_implied_rate,
            )
        else:
            raise ValueError(
                f"Unsupported interval '{interval}'. Use 'daily' or 'hourly'."
            )

    return results


def extract_contract_life_from_strip(
    strip_data: dict[str, pd.DataFrame],
    contract_code: str,
) -> pd.DataFrame:
    """
    Reconstruct the life of one discrete FF contract from rank-series data.

    Args:
        strip_data: Mapping of continuous symbol/RIC -> DataFrame.
        contract_code: Discrete contract code to extract (e.g. ``FFZ24``).

    Returns:
        Concatenated DataFrame containing all rows whose ``source_contract``
        matches ``contract_code``, sorted by timestamp/index. Adds a
        ``continuous_symbol`` column so callers can see which rank each
        segment came from.
    """
    segments: list[pd.DataFrame] = []

    for continuous_symbol, df in strip_data.items():
        if df.empty or "source_contract" not in df.columns:
            continue

        segment = df[df["source_contract"] == contract_code].copy()
        if segment.empty:
            continue

        segment["continuous_symbol"] = continuous_symbol
        segments.append(segment)

    if not segments:
        return pd.DataFrame()

    result = pd.concat(segments).sort_index()
    if result.index.has_duplicates:
        result = result[~result.index.duplicated(keep="last")]
    return result


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
