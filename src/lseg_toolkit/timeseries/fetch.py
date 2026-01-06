"""
LSEG data fetch layer for time series extraction.

Provides functions to fetch time series data from LSEG Data Library.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import lseg.data as rd
import pandas as pd

from lseg_toolkit.exceptions import DataRetrievalError, InstrumentNotFoundError
from lseg_toolkit.timeseries.constants import (
    ALL_FUTURES_MAPPING,
    COLUMN_MAPPING,
    FUTURES_OHLCV_FIELDS,
    FX_SPOT_FIELDS,
    FX_SPOT_RICS,
    VALID_INTERVALS,
    get_fra_ric,
    get_ois_ric,
    get_treasury_yield_ric,
)
from lseg_toolkit.timeseries.enums import AssetClass, Granularity

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


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

    # Check if it's already a RIC (ends with = or contains c1/c2)
    if symbol.endswith("=") or "c1" in symbol or "c2" in symbol:
        return symbol

    # Try futures mapping first (e.g., ZN -> TYc1)
    if symbol_upper in ALL_FUTURES_MAPPING:
        lseg_root = ALL_FUTURES_MAPPING[symbol_upper]
        return f"{lseg_root}c1"  # Default to front month continuous

    # Try FX spot (e.g., EURUSD -> EUR=)
    if symbol_upper in FX_SPOT_RICS:
        return FX_SPOT_RICS[symbol_upper]

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
    if len(symbol) >= 3 and symbol[-2] == "c" and symbol[-1].isdigit():
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
) -> pd.DataFrame:
    """
    Fetch time series data for one or more RICs.

    This is the core fetch function that wraps rd.get_history().

    Args:
        rics: List of LSEG RIC codes.
        start_date: Start date.
        end_date: End date.
        fields: List of fields to retrieve (default: OHLCV).
        granularity: Data granularity.

    Returns:
        DataFrame with DatetimeIndex and OHLCV columns.

    Raises:
        DataRetrievalError: If fetch fails.
    """
    if not rics:
        return pd.DataFrame()

    # Default fields for OHLCV
    if fields is None:
        fields = FUTURES_OHLCV_FIELDS

    # Map granularity to LSEG interval
    interval = GRANULARITY_TO_INTERVAL.get(granularity, "daily")
    if interval not in VALID_INTERVALS:
        raise DataRetrievalError(f"Invalid interval: {interval}")

    try:
        df = rd.get_history(
            universe=rics,
            fields=fields,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=interval,
        )

        if df is None or df.empty:
            logger.warning(f"No data returned for {rics}")
            return pd.DataFrame()

        # Normalize column names
        df = _normalize_columns(df)

        return df
    except Exception as e:
        raise DataRetrievalError(f"Failed to fetch data for {rics}: {e}") from e


def fetch_futures(
    symbols: list[str],
    start_date: date,
    end_date: date,
    granularity: Granularity = Granularity.DAILY,
    continuous: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Fetch futures time series data.

    Args:
        symbols: List of CME symbols (e.g., ['ZN', 'ZB']) or LSEG RICs.
        start_date: Start date.
        end_date: End date.
        granularity: Data granularity.
        continuous: If True, fetch continuous contracts (c1).

    Returns:
        Dict mapping symbol to DataFrame.
    """
    results: dict[str, pd.DataFrame] = {}

    for symbol in symbols:
        if continuous:
            ric = resolve_ric(symbol, AssetClass.BOND_FUTURES)
        else:
            ric = symbol  # Assume already a RIC for discrete

        try:
            df = fetch_timeseries(
                rics=[ric],
                start_date=start_date,
                end_date=end_date,
                fields=FUTURES_OHLCV_FIELDS,
                granularity=granularity,
            )
            if not df.empty:
                results[symbol] = df
                logger.info(f"Fetched {len(df)} rows for {symbol} ({ric})")
        except DataRetrievalError as e:
            logger.error(f"Failed to fetch {symbol}: {e}")

    return results


def fetch_fx(
    pairs: list[str],
    start_date: date,
    end_date: date,
    granularity: Granularity = Granularity.DAILY,
) -> dict[str, pd.DataFrame]:
    """
    Fetch FX spot time series data.

    Args:
        pairs: List of currency pairs (e.g., ['EURUSD', 'USDJPY']).
        start_date: Start date.
        end_date: End date.
        granularity: Data granularity.

    Returns:
        Dict mapping pair to DataFrame.
    """
    results: dict[str, pd.DataFrame] = {}

    for pair in pairs:
        ric = resolve_ric(pair, AssetClass.FX_SPOT)

        try:
            df = fetch_timeseries(
                rics=[ric],
                start_date=start_date,
                end_date=end_date,
                fields=FX_SPOT_FIELDS,
                granularity=granularity,
            )
            if not df.empty:
                results[pair] = df
                logger.info(f"Fetched {len(df)} rows for {pair} ({ric})")
        except DataRetrievalError as e:
            logger.error(f"Failed to fetch {pair}: {e}")

    return results


def fetch_ois(
    currency: str,
    tenors: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, pd.DataFrame]:
    """
    Fetch OIS rate time series.

    Args:
        currency: Currency code (e.g., 'USD', 'EUR').
        tenors: List of tenors (e.g., ['1M', '3M', '1Y', '5Y']).
        start_date: Start date.
        end_date: End date.

    Returns:
        Dict mapping tenor to DataFrame.
    """
    results: dict[str, pd.DataFrame] = {}

    for tenor in tenors:
        ric = get_ois_ric(currency, tenor)

        try:
            df = fetch_timeseries(
                rics=[ric],
                start_date=start_date,
                end_date=end_date,
                fields=["CLOSE"],  # OIS typically just has close
                granularity=Granularity.DAILY,
            )
            if not df.empty:
                results[tenor] = df
                logger.info(f"Fetched {len(df)} rows for {currency}{tenor}OIS ({ric})")
        except DataRetrievalError as e:
            logger.error(f"Failed to fetch {currency}{tenor}OIS: {e}")

    return results


def fetch_treasury_yields(
    tenors: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, pd.DataFrame]:
    """
    Fetch US Treasury yield curve.

    Args:
        tenors: List of tenors (e.g., ['1M', '3M', '2Y', '10Y', '30Y']).
        start_date: Start date.
        end_date: End date.

    Returns:
        Dict mapping tenor to DataFrame.
    """
    results: dict[str, pd.DataFrame] = {}

    for tenor in tenors:
        ric = get_treasury_yield_ric(tenor)

        try:
            df = fetch_timeseries(
                rics=[ric],
                start_date=start_date,
                end_date=end_date,
                fields=["CLOSE"],
                granularity=Granularity.DAILY,
            )
            if not df.empty:
                results[tenor] = df
                logger.info(f"Fetched {len(df)} rows for US{tenor}T ({ric})")
        except DataRetrievalError as e:
            logger.error(f"Failed to fetch US{tenor}T: {e}")

    return results


def fetch_fras(
    currency: str,
    tenors: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, pd.DataFrame]:
    """
    Fetch Forward Rate Agreement rates.

    Args:
        currency: Currency code (e.g., 'USD').
        tenors: List of FRA tenors (e.g., ['1X4', '3X6']).
        start_date: Start date.
        end_date: End date.

    Returns:
        Dict mapping tenor to DataFrame.
    """
    results: dict[str, pd.DataFrame] = {}

    for tenor in tenors:
        ric = get_fra_ric(currency, tenor)

        try:
            df = fetch_timeseries(
                rics=[ric],
                start_date=start_date,
                end_date=end_date,
                fields=["BID", "ASK"],
                granularity=Granularity.DAILY,
            )
            if not df.empty:
                results[tenor] = df
                logger.info(f"Fetched {len(df)} rows for {currency}{tenor}F ({ric})")
        except DataRetrievalError as e:
            logger.error(f"Failed to fetch {currency}{tenor}F: {e}")

    return results


# =============================================================================
# Contract Chain (for roll detection)
# =============================================================================


def get_contract_chain(cme_symbol: str, num_contracts: int = 4) -> list[dict]:
    """
    Get active contract chain for a futures symbol.

    Args:
        cme_symbol: CME symbol (e.g., 'ZN')
        num_contracts: Number of contracts to retrieve.

    Returns:
        List of dicts with contract info:
        - ric: LSEG RIC
        - expiry_date: Expiration date
        - name: Display name

    Raises:
        DataRetrievalError: If fetch fails.
    """
    # Get continuous contract RICs
    rics = [get_continuous_ric(cme_symbol, i + 1) for i in range(num_contracts)]

    try:
        df = rd.get_data(
            universe=rics,
            fields=["DSPLY_NAME", "EXPIR_DATE", "SETTLE", "OPINT_1"],
        )

        if df is None or df.empty:
            raise DataRetrievalError(f"No contract chain data for {cme_symbol}")

        contracts = []
        for ric in rics:
            row = (
                df[df["Instrument"] == ric]
                if "Instrument" in df.columns
                else df.loc[[ric]]
            )
            if not row.empty:
                contracts.append(
                    {
                        "ric": ric,
                        "name": row["DSPLY_NAME"].iloc[0]
                        if "DSPLY_NAME" in row
                        else "",
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
    except Exception as e:
        raise DataRetrievalError(
            f"Failed to get contract chain for {cme_symbol}: {e}"
        ) from e


def get_contract_specs(ric: str) -> dict:
    """
    Get contract specifications for a single RIC.

    Args:
        ric: LSEG RIC code.

    Returns:
        Dict with contract specs.
    """
    try:
        df = rd.get_data(
            universe=[ric],
            fields=[
                "DSPLY_NAME",
                "EXPIR_DATE",
                "SETTLE",
                "OPINT_1",
                "ACVOL_1",
                "CF_LAST",
            ],
        )

        if df is None or df.empty:
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
    except Exception as e:
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
