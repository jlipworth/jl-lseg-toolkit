"""
Time series data reading operations for TimescaleDB storage.

This module provides functions for loading time series data from the database,
with support for all data shapes (OHLCV, Quote, Rate, Bond, Fixing).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd
import psycopg

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.enums import DataShape, Granularity


def load_timeseries(
    conn: psycopg.Connection,
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: Granularity = Granularity.DAILY,
    data_shape: DataShape | None = None,
) -> pd.DataFrame:
    """
    Load time series data from database.

    Routes to the correct timeseries table based on data_shape:
    - OHLCV: timeseries_ohlcv (futures, equities, commodities)
    - QUOTE: timeseries_quote (FX spot, FX forwards)
    - RATE: timeseries_rate (OIS, IRS, FRA, repo)
    - BOND: timeseries_bond (govt yields, corp bonds)
    - FIXING: timeseries_fixing (SOFR, ESTR, SONIA)

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        start_date: Start date filter.
        end_date: End date filter.
        granularity: Data granularity.
        data_shape: Data shape for routing (auto-detected from instrument if None).

    Returns:
        DataFrame with DatetimeIndex and appropriate columns for the data shape.

    Raises:
        StorageError: If load fails.
    """
    # Get instrument info
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, data_shape FROM instruments WHERE symbol = %s", [symbol]
        )
        result = cur.fetchone()

    if result is None:
        return pd.DataFrame()

    instrument_id = result["id"]
    instr_data_shape = result["data_shape"]

    # Auto-detect data_shape from instrument if not provided
    if data_shape is None:
        data_shape = (
            DataShape(instr_data_shape) if instr_data_shape else DataShape.OHLCV
        )

    try:
        # Route to appropriate load function based on data_shape
        if data_shape == DataShape.OHLCV:
            return _load_ohlcv_data(
                conn, instrument_id, start_date, end_date, granularity
            )
        elif data_shape == DataShape.QUOTE:
            return _load_quote_data(
                conn, instrument_id, start_date, end_date, granularity
            )
        elif data_shape == DataShape.RATE:
            return _load_rate_data(
                conn, instrument_id, start_date, end_date, granularity
            )
        elif data_shape == DataShape.BOND:
            return _load_bond_data(
                conn, instrument_id, start_date, end_date, granularity
            )
        elif data_shape == DataShape.FIXING:
            return _load_fixing_data(conn, instrument_id, start_date, end_date)
        else:
            # Fallback to OHLCV
            return _load_ohlcv_data(
                conn, instrument_id, start_date, end_date, granularity
            )
    except psycopg.Error as e:
        raise StorageError(f"Failed to load time series for {symbol}: {e}") from e


def _execute_to_dataframe(
    conn: psycopg.Connection,
    query: str,
    params: list,
    index_col: str = "ts",
    index_name: str = "timestamp",
) -> pd.DataFrame:
    """Execute query and return DataFrame with index."""
    with conn.cursor() as cur:
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=columns)
    if index_col in df.columns:
        df.set_index(index_col, inplace=True)
        df.index.name = index_name
    return df


def _load_ohlcv_data(
    conn: psycopg.Connection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
    granularity: Granularity,
) -> pd.DataFrame:
    """Load OHLCV data from timeseries_ohlcv."""
    query = """
        SELECT ts, session_date, open, high, low, close, volume, settle,
               open_interest, bid, ask, mid, implied_rate, vwap,
               source_contract, adjustment_factor
        FROM timeseries_ohlcv
        WHERE instrument_id = %s AND granularity = %s
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= %s"
        params.append(datetime.combine(start_date, datetime.min.time(), tzinfo=UTC))
    if end_date:
        query += " AND ts <= %s"
        params.append(datetime.combine(end_date, datetime.max.time(), tzinfo=UTC))

    query += " ORDER BY ts ASC"

    return _execute_to_dataframe(conn, query, params, "ts", "timestamp")


def _load_quote_data(
    conn: psycopg.Connection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
    granularity: Granularity,
) -> pd.DataFrame:
    """Load quote data from timeseries_quote."""
    query = """
        SELECT ts, bid, ask, mid, open_bid, bid_high, bid_low,
               open_ask, ask_high, ask_low, forward_points
        FROM timeseries_quote
        WHERE instrument_id = %s AND granularity = %s
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= %s"
        params.append(datetime.combine(start_date, datetime.min.time(), tzinfo=UTC))
    if end_date:
        query += " AND ts <= %s"
        params.append(datetime.combine(end_date, datetime.max.time(), tzinfo=UTC))

    query += " ORDER BY ts ASC"

    return _execute_to_dataframe(conn, query, params, "ts", "timestamp")


def _load_rate_data(
    conn: psycopg.Connection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
    granularity: Granularity,
) -> pd.DataFrame:
    """Load rate data from timeseries_rate."""
    query = """
        SELECT ts, rate, bid, ask, open_rate, high_rate, low_rate,
               rate_2, spread, reference_rate, side
        FROM timeseries_rate
        WHERE instrument_id = %s AND granularity = %s
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= %s"
        params.append(datetime.combine(start_date, datetime.min.time(), tzinfo=UTC))
    if end_date:
        query += " AND ts <= %s"
        params.append(datetime.combine(end_date, datetime.max.time(), tzinfo=UTC))

    query += " ORDER BY ts ASC"

    return _execute_to_dataframe(conn, query, params, "ts", "timestamp")


def _load_bond_data(
    conn: psycopg.Connection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
    granularity: Granularity,
) -> pd.DataFrame:
    """Load bond data from timeseries_bond."""
    query = """
        SELECT ts, price, dirty_price, accrued_interest, bid, ask,
               open_price, open_yield,
               yield, yield_bid, yield_ask, yield_high, yield_low,
               mac_duration, mod_duration, convexity, dv01,
               z_spread, oas
        FROM timeseries_bond
        WHERE instrument_id = %s AND granularity = %s
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= %s"
        params.append(datetime.combine(start_date, datetime.min.time(), tzinfo=UTC))
    if end_date:
        query += " AND ts <= %s"
        params.append(datetime.combine(end_date, datetime.max.time(), tzinfo=UTC))

    query += " ORDER BY ts ASC"

    return _execute_to_dataframe(conn, query, params, "ts", "timestamp")


def _load_fixing_data(
    conn: psycopg.Connection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """Load fixing data from timeseries_fixing.

    Note: Fixings are daily only, no granularity parameter.
    """
    query = """
        SELECT date, value, volume
        FROM timeseries_fixing
        WHERE instrument_id = %s
    """
    params: list = [instrument_id]

    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    query += " ORDER BY date ASC"

    df = _execute_to_dataframe(conn, query, params, "date", "date")
    if not df.empty and df.index.dtype != "datetime64[ns]":
        df.index = pd.to_datetime(df.index)
    return df


def get_data_range(
    conn: psycopg.Connection,
    symbol: str,
    granularity: Granularity = Granularity.DAILY,
    data_shape: DataShape | None = None,
) -> tuple[date | None, date | None]:
    """
    Get date range of stored data for an instrument.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        granularity: Data granularity.
        data_shape: Data shape (auto-detected from instrument if None).

    Returns:
        Tuple of (min_date, max_date) or (None, None) if no data.
    """
    # Get instrument info
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, data_shape FROM instruments WHERE symbol = %s", [symbol]
        )
        result = cur.fetchone()

    if result is None:
        return None, None

    instrument_id = result["id"]
    instr_data_shape = result["data_shape"]

    # Auto-detect data_shape from instrument if not provided
    if data_shape is None:
        data_shape = (
            DataShape(instr_data_shape) if instr_data_shape else DataShape.OHLCV
        )

    # Route to correct table based on data_shape
    with conn.cursor() as cur:
        if data_shape == DataShape.OHLCV:
            cur.execute(
                """
                SELECT MIN(ts)::DATE, MAX(ts)::DATE
                FROM timeseries_ohlcv
                WHERE instrument_id = %s AND granularity = %s
                """,
                [instrument_id, granularity.value],
            )
        elif data_shape == DataShape.QUOTE:
            cur.execute(
                """
                SELECT MIN(ts)::DATE, MAX(ts)::DATE
                FROM timeseries_quote
                WHERE instrument_id = %s AND granularity = %s
                """,
                [instrument_id, granularity.value],
            )
        elif data_shape == DataShape.RATE:
            cur.execute(
                """
                SELECT MIN(ts)::DATE, MAX(ts)::DATE
                FROM timeseries_rate
                WHERE instrument_id = %s AND granularity = %s
                """,
                [instrument_id, granularity.value],
            )
        elif data_shape == DataShape.BOND:
            cur.execute(
                """
                SELECT MIN(ts)::DATE, MAX(ts)::DATE
                FROM timeseries_bond
                WHERE instrument_id = %s AND granularity = %s
                """,
                [instrument_id, granularity.value],
            )
        elif data_shape == DataShape.FIXING:
            cur.execute(
                """
                SELECT MIN(date), MAX(date)
                FROM timeseries_fixing
                WHERE instrument_id = %s
                """,
                [instrument_id],
            )
        else:
            # Fallback to OHLCV
            cur.execute(
                """
                SELECT MIN(ts)::DATE, MAX(ts)::DATE
                FROM timeseries_ohlcv
                WHERE instrument_id = %s AND granularity = %s
                """,
                [instrument_id, granularity.value],
            )
        result = cur.fetchone()

    if result and result["min"] and result["max"]:
        min_date = result["min"]
        max_date = result["max"]
        # Convert to date if needed
        if isinstance(min_date, datetime):
            min_date = min_date.date()
        if isinstance(max_date, datetime):
            max_date = max_date.date()
        return min_date, max_date
    return None, None


def get_data_coverage(conn: psycopg.Connection) -> pd.DataFrame:
    """
    Get data coverage summary from the view.

    Args:
        conn: Database connection.

    Returns:
        DataFrame with coverage information.
    """
    return _execute_to_dataframe(
        conn,
        "SELECT * FROM data_coverage ORDER BY symbol",
        [],
        index_col="symbol",
        index_name="symbol",
    )


def get_instrument(conn: psycopg.Connection, symbol: str) -> dict | None:
    """
    Get instrument details by symbol.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.

    Returns:
        Dict with instrument details or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, symbol, name, asset_class, data_shape, lseg_ric,
                   exchange, currency, description, created_at, updated_at
            FROM instruments
            WHERE symbol = %s
            """,
            [symbol],
        )
        result = cur.fetchone()

    return dict(result) if result else None


def get_instrument_by_id(conn: psycopg.Connection, instrument_id: int) -> dict | None:
    """
    Get instrument details by ID.

    Args:
        conn: Database connection.
        instrument_id: Instrument ID.

    Returns:
        Dict with instrument details or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, symbol, name, asset_class, data_shape, lseg_ric,
                   exchange, currency, description, created_at, updated_at
            FROM instruments
            WHERE id = %s
            """,
            [instrument_id],
        )
        result = cur.fetchone()

    return dict(result) if result else None


def list_instruments(
    conn: psycopg.Connection,
    asset_class: str | None = None,
    data_shape: str | None = None,
) -> pd.DataFrame:
    """
    List all instruments, optionally filtered.

    Args:
        conn: Database connection.
        asset_class: Filter by asset class.
        data_shape: Filter by data shape.

    Returns:
        DataFrame with instrument list.
    """
    query = "SELECT id, symbol, name, asset_class, data_shape, lseg_ric FROM instruments WHERE 1=1"
    params: list = []

    if asset_class:
        query += " AND asset_class = %s"
        params.append(asset_class)
    if data_shape:
        query += " AND data_shape = %s"
        params.append(data_shape)

    query += " ORDER BY symbol"

    return _execute_to_dataframe(conn, query, params, index_col="id", index_name="id")
