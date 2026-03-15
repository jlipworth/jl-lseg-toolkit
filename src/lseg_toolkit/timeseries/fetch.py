"""
LSEG data fetch layer for time series extraction.

Provides functions to fetch time series data from LSEG Data Library.
Uses LSEGDataClient for batched requests, retry logic, and input validation.
"""

from __future__ import annotations

import logging
from datetime import date
import re
from typing import TYPE_CHECKING

import pandas as pd

from lseg_toolkit.exceptions import DataRetrievalError, InstrumentNotFoundError
from lseg_toolkit.timeseries.client import LSEGDataClient, get_client
from lseg_toolkit.timeseries.fed_funds import parse_ff_continuous_rank
from lseg_toolkit.timeseries.constants import (
    ALL_FUTURES_MAPPING,
    COLUMN_MAPPING,
    FUTURES_OHLCV_FIELDS,
    FX_SPOT_FIELDS,
    FX_SPOT_RICS,
    STIR_FUTURES_RICS,
    USD_OIS_FIELDS,
    UST_YIELD_FIELDS,
    get_fra_ric,
    get_ois_ric,
    get_treasury_yield_ric,
)
from lseg_toolkit.timeseries.enums import AssetClass, Granularity

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
CONTINUOUS_RIC_PATTERN = re.compile(r"^[A-Za-z]+c\d+$")


# =============================================================================
# Interval Mapping
# =============================================================================

GRANULARITY_TO_INTERVAL: dict[Granularity, str] = {
    Granularity.TICK: "tick",
    Granularity.MINUTE_1: "1min",
    Granularity.MINUTE_5: "5min",
    Granularity.MINUTE_10: "10min",
    Granularity.MINUTE_30: "30min",
    Granularity.HOURLY: "hourly",
    Granularity.DAILY: "daily",
    Granularity.WEEKLY: "weekly",
    Granularity.MONTHLY: "monthly",
}


# =============================================================================
# Symbol Resolution
# =============================================================================


def resolve_ric(symbol: str, asset_class: AssetClass | None = None) -> str:
    """
    Resolve a user symbol to LSEG RIC.

    Args:
        symbol: User-facing symbol (e.g., 'ZN', 'EURUSD', 'USD1MOIS')
        asset_class: Asset class hint for disambiguation.

    Returns:
        LSEG RIC code.

    Raises:
        InstrumentNotFoundError: If symbol cannot be resolved.

    Examples:
        >>> resolve_ric('ZN')  # -> 'TYc1'
        >>> resolve_ric('EURUSD')  # -> 'EUR='
        >>> resolve_ric('USD1MOIS')  # -> 'USD1MOIS='
    """
    symbol_upper = symbol.upper()

    # Check if it's already a RIC
    if symbol.endswith("=") or CONTINUOUS_RIC_PATTERN.match(symbol):
        return symbol

    # Try futures mapping first (e.g., ZN -> TYc1)
    if symbol_upper in ALL_FUTURES_MAPPING:
        lseg_root = ALL_FUTURES_MAPPING[symbol_upper]
        return f"{lseg_root}c1"  # Default to front month continuous

    # Try FX spot (e.g., EURUSD -> EUR=)
    if symbol_upper in FX_SPOT_RICS:
        return FX_SPOT_RICS[symbol_upper]

    # Try STIR futures symbolic mapping (e.g., FF_CONTINUOUS -> FFc1)
    if symbol_upper in STIR_FUTURES_RICS:
        return STIR_FUTURES_RICS[symbol_upper]

    ff_rank = parse_ff_continuous_rank(symbol_upper)
    if ff_rank is not None:
        return f"FFc{ff_rank}"

    # Auto-detect asset class patterns
    if asset_class == AssetClass.OIS or "OIS" in symbol_upper:
        # Already formatted as USD1MOIS, just add =
        if not symbol.endswith("="):
            return f"{symbol}="
        return symbol

    if asset_class == AssetClass.GOVT_YIELD or symbol_upper.endswith("T"):
        # Treasury yield (e.g., US10YT -> US10YT=RRPS)
        return f"{symbol_upper}=RRPS"

    if asset_class == AssetClass.FRA or "X" in symbol_upper and "F" in symbol_upper:
        # FRA format already correct, add =
        if not symbol.endswith("="):
            return f"{symbol}="
        return symbol

    # If symbol looks like a continuous futures RIC pattern
    # (root + c + number), pass through
    if CONTINUOUS_RIC_PATTERN.match(symbol):
        return symbol

    # Pass through if we can't identify it
    logger.warning(f"Could not resolve symbol {symbol}, passing through as-is")
    return symbol


def get_continuous_ric(cme_symbol: str, rank: int = 1) -> str:
    """
    Get continuous contract RIC for a CME symbol.

    Args:
        cme_symbol: CME symbol (e.g., 'ZN', 'ZB')
        rank: Contract rank (1=front, 2=second, etc.)

    Returns:
        LSEG continuous RIC (e.g., 'TYc1', 'TYc2')
    """
    symbol_upper = cme_symbol.upper()
    if symbol_upper in ALL_FUTURES_MAPPING:
        lseg_root = ALL_FUTURES_MAPPING[symbol_upper]
        return f"{lseg_root}c{rank}"
    raise InstrumentNotFoundError(f"Unknown CME symbol: {cme_symbol}")


def get_discrete_ric(cme_symbol: str, month_code: str, year: int) -> str:
    """
    Get discrete contract RIC for a CME symbol.

    Args:
        cme_symbol: CME symbol (e.g., 'ZN', 'ZB')
        month_code: Futures month code (H, M, U, Z)
        year: Two-digit year

    Returns:
        LSEG discrete RIC (e.g., 'TYH5', 'TYM6')
    """
    symbol_upper = cme_symbol.upper()
    if symbol_upper in ALL_FUTURES_MAPPING:
        lseg_root = ALL_FUTURES_MAPPING[symbol_upper]
        return f"{lseg_root}{month_code}{year % 100}"
    raise InstrumentNotFoundError(f"Unknown CME symbol: {cme_symbol}")


# =============================================================================
# Fetch Functions
# =============================================================================


def fetch_timeseries(
    rics: list[str],
    start_date: date,
    end_date: date,
    fields: list[str] | None = None,
    granularity: Granularity = Granularity.DAILY,
    client: LSEGDataClient | None = None,
) -> pd.DataFrame:
    """
    Fetch time series data for one or more RICs.

    This is the core fetch function that uses LSEGDataClient for
    batched requests, retry logic, and input validation.

    Args:
        rics: List of LSEG RIC codes.
        start_date: Start date.
        end_date: End date.
        fields: List of fields to retrieve (default: OHLCV).
        granularity: Data granularity.
        client: Optional LSEGDataClient instance (uses singleton if not provided).

    Returns:
        DataFrame with DatetimeIndex and requested columns.
        Returns empty DataFrame if no data available.

    Raises:
        DataRetrievalError: If fetch fails after retries.
        DataValidationError: If inputs are invalid.
        SessionError: If LSEG session is not open.
    """
    if not rics:
        return pd.DataFrame()

    # Use singleton client if not provided
    if client is None:
        client = get_client()

    # Default fields for OHLCV
    if fields is None:
        fields = FUTURES_OHLCV_FIELDS

    # Map granularity to LSEG interval
    interval = GRANULARITY_TO_INTERVAL.get(granularity, "daily")

    # Client handles batching, retries, and validation
    df = client.get_history(
        rics=rics,
        start=start_date,
        end=end_date,
        fields=fields,
        interval=interval,
    )

    if df.empty:
        logger.warning(f"No data returned for {rics}")
        return pd.DataFrame()

    # Normalize column names
    df = _normalize_columns(df)

    return df


def fetch_futures(
    symbols: list[str],
    start_date: date,
    end_date: date,
    granularity: Granularity = Granularity.DAILY,
    continuous: bool = True,
    client: LSEGDataClient | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch futures time series data.

    Makes a single batched API call for all symbols, then splits results.
    This is more efficient than making individual calls per symbol.

    Args:
        symbols: List of CME symbols (e.g., ['ZN', 'ZB']) or LSEG RICs.
        start_date: Start date.
        end_date: End date.
        granularity: Data granularity.
        continuous: If True, fetch continuous contracts (c1).
        client: Optional LSEGDataClient instance.

    Returns:
        Dict mapping symbol to DataFrame.
    """
    if not symbols:
        return {}

    # Build symbol -> RIC mapping
    symbol_to_ric: dict[str, str] = {}
    for symbol in symbols:
        if continuous:
            ric = resolve_ric(symbol, AssetClass.BOND_FUTURES)
        else:
            ric = symbol
        symbol_to_ric[symbol] = ric

    # Fetch all RICs in one batched call
    all_rics = list(symbol_to_ric.values())
    try:
        df = fetch_timeseries(
            rics=all_rics,
            start_date=start_date,
            end_date=end_date,
            fields=FUTURES_OHLCV_FIELDS,
            granularity=granularity,
            client=client,
        )
    except DataRetrievalError as e:
        logger.error(f"Failed to fetch futures: {e}")
        return {}

    if df.empty:
        return {}

    # Split results by symbol using shared utility
    return _split_multi_ric_response(df, symbol_to_ric)


def fetch_fx(
    pairs: list[str],
    start_date: date,
    end_date: date,
    granularity: Granularity = Granularity.DAILY,
    client: LSEGDataClient | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch FX spot time series data.

    Makes a single batched API call for all pairs, then splits results.

    Args:
        pairs: List of currency pairs (e.g., ['EURUSD', 'USDJPY']).
        start_date: Start date.
        end_date: End date.
        granularity: Data granularity.
        client: Optional LSEGDataClient instance.

    Returns:
        Dict mapping pair to DataFrame.
    """
    if not pairs:
        return {}

    # Build pair -> RIC mapping
    pair_to_ric: dict[str, str] = {}
    for pair in pairs:
        ric = resolve_ric(pair, AssetClass.FX_SPOT)
        pair_to_ric[pair] = ric

    # Fetch all RICs in one batched call
    all_rics = list(pair_to_ric.values())
    try:
        df = fetch_timeseries(
            rics=all_rics,
            start_date=start_date,
            end_date=end_date,
            fields=FX_SPOT_FIELDS,
            granularity=granularity,
            client=client,
        )
    except DataRetrievalError as e:
        logger.error(f"Failed to fetch FX pairs: {e}")
        return {}

    if df.empty:
        return {}

    # Split results by pair
    return _split_multi_ric_response(df, pair_to_ric)


def fetch_ois(
    currency: str,
    tenors: list[str],
    start_date: date,
    end_date: date,
    client: LSEGDataClient | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch OIS rate time series.

    Makes a single batched API call for all tenors, then splits results.

    Args:
        currency: Currency code (e.g., 'USD', 'EUR').
        tenors: List of tenors (e.g., ['1M', '3M', '1Y', '5Y']).
        start_date: Start date.
        end_date: End date.
        client: Optional LSEGDataClient instance.

    Returns:
        Dict mapping tenor to DataFrame.
    """
    if not tenors:
        return {}

    # Build tenor -> RIC mapping
    tenor_to_ric: dict[str, str] = {}
    for tenor in tenors:
        ric = get_ois_ric(currency, tenor)
        tenor_to_ric[tenor] = ric

    # Fetch all RICs in one batched call
    all_rics = list(tenor_to_ric.values())
    try:
        df = fetch_timeseries(
            rics=all_rics,
            start_date=start_date,
            end_date=end_date,
            fields=USD_OIS_FIELDS,
            granularity=Granularity.DAILY,
            client=client,
        )
    except DataRetrievalError as e:
        logger.error(f"Failed to fetch {currency} OIS: {e}")
        return {}

    if df.empty:
        return {}

    return _split_multi_ric_response(df, tenor_to_ric)


def fetch_treasury_yields(
    tenors: list[str],
    start_date: date,
    end_date: date,
    client: LSEGDataClient | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch US Treasury yield curve.

    Makes a single batched API call for all tenors, then splits results.

    Args:
        tenors: List of tenors (e.g., ['1M', '3M', '2Y', '10Y', '30Y']).
        start_date: Start date.
        end_date: End date.
        client: Optional LSEGDataClient instance.

    Returns:
        Dict mapping tenor to DataFrame.
    """
    if not tenors:
        return {}

    # Build tenor -> RIC mapping
    tenor_to_ric: dict[str, str] = {}
    for tenor in tenors:
        ric = get_treasury_yield_ric(tenor)
        tenor_to_ric[tenor] = ric

    # Fetch all RICs in one batched call
    all_rics = list(tenor_to_ric.values())
    try:
        df = fetch_timeseries(
            rics=all_rics,
            start_date=start_date,
            end_date=end_date,
            fields=UST_YIELD_FIELDS,
            granularity=Granularity.DAILY,
            client=client,
        )
    except DataRetrievalError as e:
        logger.error(f"Failed to fetch US Treasury yields: {e}")
        return {}

    if df.empty:
        return {}

    return _split_multi_ric_response(df, tenor_to_ric)


def fetch_fras(
    currency: str,
    tenors: list[str],
    start_date: date,
    end_date: date,
    client: LSEGDataClient | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch Forward Rate Agreement rates.

    Makes a single batched API call for all tenors, then splits results.

    Args:
        currency: Currency code (e.g., 'USD').
        tenors: List of FRA tenors (e.g., ['1X4', '3X6']).
        start_date: Start date.
        end_date: End date.
        client: Optional LSEGDataClient instance.

    Returns:
        Dict mapping tenor to DataFrame.
    """
    if not tenors:
        return {}

    # Build tenor -> RIC mapping
    tenor_to_ric: dict[str, str] = {}
    for tenor in tenors:
        ric = get_fra_ric(currency, tenor)
        tenor_to_ric[tenor] = ric

    # Fetch all RICs in one batched call
    all_rics = list(tenor_to_ric.values())
    try:
        df = fetch_timeseries(
            rics=all_rics,
            start_date=start_date,
            end_date=end_date,
            fields=["BID", "ASK"],
            granularity=Granularity.DAILY,
            client=client,
        )
    except DataRetrievalError as e:
        logger.error(f"Failed to fetch {currency} FRAs: {e}")
        return {}

    if df.empty:
        return {}

    return _split_multi_ric_response(df, tenor_to_ric)


# =============================================================================
# Contract Chain (for roll detection)
# =============================================================================


def get_contract_chain(
    cme_symbol: str,
    num_contracts: int = 4,
    client: LSEGDataClient | None = None,
) -> list[dict]:
    """
    Get active contract chain for a futures symbol.

    Args:
        cme_symbol: CME symbol (e.g., 'ZN')
        num_contracts: Number of contracts to retrieve.
        client: Optional LSEGDataClient instance.

    Returns:
        List of dicts with contract info:
        - ric: LSEG RIC
        - expiry_date: Expiration date
        - name: Display name

    Raises:
        DataRetrievalError: If fetch fails.
    """
    if client is None:
        client = get_client()

    # Get continuous contract RICs
    rics = [get_continuous_ric(cme_symbol, i + 1) for i in range(num_contracts)]

    df = client.get_data(
        rics=rics,
        fields=["DSPLY_NAME", "EXPIR_DATE", "SETTLE", "OPINT_1"],
    )

    if df.empty:
        raise DataRetrievalError(f"No contract chain data for {cme_symbol}")

    contracts = []
    for ric in rics:
        row = (
            df[df["Instrument"] == ric] if "Instrument" in df.columns else df.loc[[ric]]
        )
        if not row.empty:
            contracts.append(
                {
                    "ric": ric,
                    "name": row["DSPLY_NAME"].iloc[0] if "DSPLY_NAME" in row else "",
                    "expiry_date": row["EXPIR_DATE"].iloc[0]
                    if "EXPIR_DATE" in row
                    else None,
                    "settle": row["SETTLE"].iloc[0] if "SETTLE" in row else None,
                    "open_interest": row["OPINT_1"].iloc[0]
                    if "OPINT_1" in row
                    else None,
                }
            )

    return contracts


def get_contract_specs(
    ric: str,
    client: LSEGDataClient | None = None,
) -> dict:
    """
    Get contract specifications for a single RIC.

    Args:
        ric: LSEG RIC code.
        client: Optional LSEGDataClient instance.

    Returns:
        Dict with contract specs.
    """
    if client is None:
        client = get_client()

    try:
        df = client.get_data(
            rics=[ric],
            fields=[
                "DSPLY_NAME",
                "EXPIR_DATE",
                "SETTLE",
                "OPINT_1",
                "ACVOL_1",
                "CF_LAST",
            ],
        )

        if df.empty:
            return {}

        row = df.iloc[0]
        return {
            "ric": ric,
            "name": row.get("DSPLY_NAME"),
            "expiry_date": row.get("EXPIR_DATE"),
            "settle": row.get("SETTLE"),
            "open_interest": row.get("OPINT_1"),
            "volume": row.get("ACVOL_1"),
            "last_price": row.get("CF_LAST"),
        }
    except DataRetrievalError as e:
        logger.error(f"Failed to get specs for {ric}: {e}")
        return {}


# =============================================================================
# Column Normalization
# =============================================================================


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize LSEG column names to standard format.

    Args:
        df: DataFrame with LSEG column names.

    Returns:
        DataFrame with normalized column names.
    """
    if df.empty:
        return df

    # Rename columns using mapping
    rename_map = {}
    for col in df.columns:
        col_upper = col.upper() if isinstance(col, str) else col
        if col_upper in COLUMN_MAPPING:
            rename_map[col] = COLUMN_MAPPING[col_upper]

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def _split_multi_ric_response(
    df: pd.DataFrame,
    key_to_ric: dict[str, str],
) -> dict[str, pd.DataFrame]:
    """
    Split a multi-RIC response DataFrame into individual DataFrames.

    LSEG API returns different formats depending on request:
    - Single RIC: Simple DataFrame with date index
    - Multiple RICs: DataFrame with 'Instrument' column or MultiIndex

    Args:
        df: Combined DataFrame from LSEG API.
        key_to_ric: Mapping from user key (symbol/pair/tenor) to RIC.

    Returns:
        Dict mapping user key to individual DataFrame.
    """
    if df.empty:
        return {}

    results: dict[str, pd.DataFrame] = {}
    ric_to_key = {v: k for k, v in key_to_ric.items()}
    all_rics = list(key_to_ric.values())

    # Single RIC case
    if len(all_rics) == 1:
        key = list(key_to_ric.keys())[0]
        results[key] = df
        logger.info(f"Fetched {len(df)} rows for {key}")
        return results

    # Multi-RIC with 'Instrument' column
    if "Instrument" in df.columns:
        for ric in all_rics:
            key = ric_to_key.get(ric, ric)
            ric_df = df[df["Instrument"] == ric].drop(columns=["Instrument"])
            if not ric_df.empty:
                results[key] = ric_df
                logger.info(f"Fetched {len(ric_df)} rows for {key}")
        return results

    # Multi-RIC with MultiIndex (date, ric)
    if isinstance(df.index, pd.MultiIndex):
        level_values = df.index.get_level_values(1)
        for ric in all_rics:
            key = ric_to_key.get(ric, ric)
            if ric in level_values:
                try:
                    xs_result = df.xs(ric, level=1)
                    # xs can return Series or DataFrame; ensure DataFrame
                    ric_df = (
                        xs_result.to_frame().T
                        if isinstance(xs_result, pd.Series)
                        else xs_result
                    )
                    if not ric_df.empty:
                        results[key] = ric_df
                        logger.info(f"Fetched {len(ric_df)} rows for {key}")
                except KeyError:
                    pass
        return results

    # Multi-RIC with MultiIndex columns (ric, field)
    if isinstance(df.columns, pd.MultiIndex):
        rics_in_data = df.columns.get_level_values(0).unique()
        for ric in all_rics:
            key = ric_to_key.get(ric, ric)
            if ric in rics_in_data:
                # Extract columns for this RIC and flatten
                ric_data = df[ric].copy()
                # Ensure we have a DataFrame (single field returns Series)
                ric_df = (
                    ric_data.to_frame() if isinstance(ric_data, pd.Series) else ric_data
                )
                if not ric_df.empty:
                    results[key] = ric_df
                    logger.info(f"Fetched {len(ric_df)} rows for {key}")
        return results

    # Fallback: single format, return for first key
    if not df.empty:
        key = list(key_to_ric.keys())[0]
        results[key] = df
        logger.info(f"Fetched {len(df)} rows")

    return results
