"""
Time series data reading operations for DuckDB storage.

This module provides functions for loading time series data from the database,
with support for all data shapes (OHLCV, Quote, Rate, Bond, Fixing).
"""

from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.enums import DataShape, Granularity


def load_timeseries(
    conn: duckdb.DuckDBPyConnection,
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
    result = conn.execute(
        "SELECT id, data_shape FROM instruments WHERE symbol = ?", [symbol]
    ).fetchone()
    if result is None:
        return pd.DataFrame()

    instrument_id, instr_data_shape = result

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
    except duckdb.Error as e:
        raise StorageError(f"Failed to load time series for {symbol}: {e}") from e


def _load_ohlcv_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
    granularity: Granularity,
) -> pd.DataFrame:
    """Load OHLCV data from timeseries_ohlcv."""
    query = """
        SELECT ts, open, high, low, close, volume, settle, open_interest, vwap,
               source_contract, adjustment_factor
        FROM timeseries_ohlcv
        WHERE instrument_id = ? AND granularity = ?
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " ORDER BY ts ASC"

    df = conn.execute(query, params).fetchdf()
    if not df.empty:
        df.set_index("ts", inplace=True)
        df.index.name = "timestamp"
    return df


def _load_quote_data(
    conn: duckdb.DuckDBPyConnection,
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
        WHERE instrument_id = ? AND granularity = ?
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " ORDER BY ts ASC"

    df = conn.execute(query, params).fetchdf()
    if not df.empty:
        df.set_index("ts", inplace=True)
        df.index.name = "timestamp"
    return df


def _load_rate_data(
    conn: duckdb.DuckDBPyConnection,
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
        WHERE instrument_id = ? AND granularity = ?
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " ORDER BY ts ASC"

    df = conn.execute(query, params).fetchdf()
    if not df.empty:
        df.set_index("ts", inplace=True)
        df.index.name = "timestamp"
    return df


def _load_bond_data(
    conn: duckdb.DuckDBPyConnection,
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
        WHERE instrument_id = ? AND granularity = ?
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " ORDER BY ts ASC"

    df = conn.execute(query, params).fetchdf()
    if not df.empty:
        df.set_index("ts", inplace=True)
        df.index.name = "timestamp"
    return df


def _load_fixing_data(
    conn: duckdb.DuckDBPyConnection,
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
        WHERE instrument_id = ?
    """
    params: list = [instrument_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date ASC"

    df = conn.execute(query, params).fetchdf()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
    return df


def get_data_range(
    conn: duckdb.DuckDBPyConnection,
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
    result = conn.execute(
        "SELECT id, data_shape FROM instruments WHERE symbol = ?", [symbol]
    ).fetchone()
    if result is None:
        return None, None

    instrument_id, instr_data_shape = result

    # Auto-detect data_shape from instrument if not provided
    if data_shape is None:
        data_shape = (
            DataShape(instr_data_shape) if instr_data_shape else DataShape.OHLCV
        )

    # Route to correct table based on data_shape
    if data_shape == DataShape.OHLCV:
        result = conn.execute(
            """
            SELECT CAST(MIN(ts) AS DATE), CAST(MAX(ts) AS DATE)
            FROM timeseries_ohlcv
            WHERE instrument_id = ? AND granularity = ?
            """,
            [instrument_id, granularity.value],
        ).fetchone()
    elif data_shape == DataShape.QUOTE:
        result = conn.execute(
            """
            SELECT CAST(MIN(ts) AS DATE), CAST(MAX(ts) AS DATE)
            FROM timeseries_quote
            WHERE instrument_id = ? AND granularity = ?
            """,
            [instrument_id, granularity.value],
        ).fetchone()
    elif data_shape == DataShape.RATE:
        result = conn.execute(
            """
            SELECT CAST(MIN(ts) AS DATE), CAST(MAX(ts) AS DATE)
            FROM timeseries_rate
            WHERE instrument_id = ? AND granularity = ?
            """,
            [instrument_id, granularity.value],
        ).fetchone()
    elif data_shape == DataShape.BOND:
        result = conn.execute(
            """
            SELECT CAST(MIN(ts) AS DATE), CAST(MAX(ts) AS DATE)
            FROM timeseries_bond
            WHERE instrument_id = ? AND granularity = ?
            """,
            [instrument_id, granularity.value],
        ).fetchone()
    elif data_shape == DataShape.FIXING:
        result = conn.execute(
            """
            SELECT MIN(date), MAX(date)
            FROM timeseries_fixing
            WHERE instrument_id = ?
            """,
            [instrument_id],
        ).fetchone()
    else:
        # Fallback to OHLCV
        result = conn.execute(
            """
            SELECT CAST(MIN(ts) AS DATE), CAST(MAX(ts) AS DATE)
            FROM timeseries_ohlcv
            WHERE instrument_id = ? AND granularity = ?
            """,
            [instrument_id, granularity.value],
        ).fetchone()

    if result and result[0] and result[1]:
        min_date = result[0]
        max_date = result[1]
        # Convert to date if needed
        if isinstance(min_date, datetime):
            min_date = min_date.date()
        if isinstance(max_date, datetime):
            max_date = max_date.date()
        return min_date, max_date
    return None, None


def get_data_coverage(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Get data coverage summary from the view.

    Args:
        conn: Database connection.

    Returns:
        DataFrame with coverage information.
    """
    return conn.execute("SELECT * FROM data_coverage ORDER BY symbol").fetchdf()
