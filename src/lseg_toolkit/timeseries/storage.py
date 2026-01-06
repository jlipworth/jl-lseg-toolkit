"""
SQLite storage layer for time series data.

Provides functions to store and retrieve time series data,
instruments, and roll events in SQLite format.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.constants import DEFAULT_DB_PATH
from lseg_toolkit.timeseries.enums import AssetClass, Granularity

if TYPE_CHECKING:
    from collections.abc import Generator

# =============================================================================
# SQLite Schema
# =============================================================================

SCHEMA_SQL = """
-- Instruments master table
CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    lseg_ric TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_asset_class ON instruments(asset_class);

-- Futures contract details (extends instruments)
CREATE TABLE IF NOT EXISTS futures_contracts (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying TEXT NOT NULL,
    expiry_date DATE,
    expiry_month TEXT,
    expiry_year INTEGER,
    continuous_type TEXT DEFAULT 'discrete',
    tick_size REAL,
    point_value REAL
);

-- FX spot details (extends instruments)
CREATE TABLE IF NOT EXISTS fx_spots (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    pip_size REAL DEFAULT 0.0001
);

-- OIS rate details (extends instruments)
CREATE TABLE IF NOT EXISTS ois_rates (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    currency TEXT NOT NULL,
    tenor TEXT NOT NULL,
    reference_rate TEXT
);

-- Government yield details (extends instruments)
CREATE TABLE IF NOT EXISTS govt_yields (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    country TEXT NOT NULL,
    tenor TEXT NOT NULL
);

-- Daily OHLCV data
CREATE TABLE IF NOT EXISTS ohlcv_daily (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume REAL,
    open_interest REAL,
    settle REAL,
    adjustment_factor REAL DEFAULT 1.0,
    source_contract TEXT,
    PRIMARY KEY (instrument_id, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_daily_date ON ohlcv_daily(instrument_id, date DESC);

-- Intraday OHLCV data (separate table for performance)
CREATE TABLE IF NOT EXISTS ohlcv_intraday (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    timestamp TIMESTAMP NOT NULL,
    granularity TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume REAL,
    PRIMARY KEY (instrument_id, timestamp, granularity)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_intraday_ts ON ohlcv_intraday(instrument_id, timestamp DESC);

-- Roll events for continuous contracts
CREATE TABLE IF NOT EXISTS roll_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    continuous_id INTEGER NOT NULL REFERENCES instruments(id),
    roll_date DATE NOT NULL,
    from_contract TEXT NOT NULL,
    to_contract TEXT NOT NULL,
    from_price REAL NOT NULL,
    to_price REAL NOT NULL,
    price_gap REAL NOT NULL,
    adjustment_factor REAL NOT NULL,
    roll_method TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_roll_events_continuous ON roll_events(continuous_id, roll_date DESC);

-- Data extraction metadata
CREATE TABLE IF NOT EXISTS extraction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    granularity TEXT NOT NULL,
    rows_fetched INTEGER NOT NULL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# =============================================================================
# Connection Management
# =============================================================================


def init_db(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Initialize SQLite database with schema.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Database connection.

    Raises:
        StorageError: If database initialization fails.
    """
    try:
        # Create parent directory if needed
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Connect and create schema
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return conn
    except sqlite3.Error as e:
        raise StorageError(f"Failed to initialize database: {e}") from e


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection]:
    """
    Context manager for database connection.

    Args:
        db_path: Path to SQLite database file.

    Yields:
        Database connection.
    """
    conn = init_db(db_path)
    try:
        yield conn
    finally:
        conn.close()


# =============================================================================
# Instrument CRUD
# =============================================================================


def save_instrument(
    conn: sqlite3.Connection,
    symbol: str,
    name: str,
    asset_class: AssetClass,
    lseg_ric: str,
    **kwargs,
) -> int:
    """
    Save or update an instrument.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        name: Human-readable name.
        asset_class: Asset class.
        lseg_ric: LSEG RIC code.
        **kwargs: Additional fields for specific instrument types.

    Returns:
        Instrument ID.

    Raises:
        StorageError: If save fails.
    """
    try:
        cursor = conn.cursor()

        # Upsert main instrument record
        cursor.execute(
            """
            INSERT INTO instruments (symbol, name, asset_class, lseg_ric, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET
                name = excluded.name,
                asset_class = excluded.asset_class,
                lseg_ric = excluded.lseg_ric,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (symbol, name, asset_class.value, lseg_ric),
        )
        instrument_id = cursor.fetchone()[0]

        # Save type-specific details
        if asset_class == AssetClass.BOND_FUTURES:
            _save_futures_details(cursor, instrument_id, **kwargs)
        elif asset_class == AssetClass.FX_SPOT:
            _save_fx_details(cursor, instrument_id, **kwargs)
        elif asset_class == AssetClass.OIS:
            _save_ois_details(cursor, instrument_id, **kwargs)
        elif asset_class == AssetClass.GOVT_YIELD:
            _save_govt_yield_details(cursor, instrument_id, **kwargs)

        conn.commit()
        return instrument_id
    except sqlite3.Error as e:
        conn.rollback()
        raise StorageError(f"Failed to save instrument {symbol}: {e}") from e


def _save_futures_details(cursor: sqlite3.Cursor, instrument_id: int, **kwargs) -> None:
    """Save futures-specific details."""
    cursor.execute(
        """
        INSERT INTO futures_contracts (
            instrument_id, underlying, expiry_date, expiry_month, expiry_year,
            continuous_type, tick_size, point_value
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument_id) DO UPDATE SET
            underlying = excluded.underlying,
            expiry_date = excluded.expiry_date,
            expiry_month = excluded.expiry_month,
            expiry_year = excluded.expiry_year,
            continuous_type = excluded.continuous_type,
            tick_size = excluded.tick_size,
            point_value = excluded.point_value
        """,
        (
            instrument_id,
            kwargs.get("underlying", ""),
            kwargs.get("expiry_date"),
            kwargs.get("expiry_month"),
            kwargs.get("expiry_year"),
            kwargs.get("continuous_type", "discrete"),
            kwargs.get("tick_size"),
            kwargs.get("point_value"),
        ),
    )


def _save_fx_details(cursor: sqlite3.Cursor, instrument_id: int, **kwargs) -> None:
    """Save FX-specific details."""
    cursor.execute(
        """
        INSERT INTO fx_spots (instrument_id, base_currency, quote_currency, pip_size)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(instrument_id) DO UPDATE SET
            base_currency = excluded.base_currency,
            quote_currency = excluded.quote_currency,
            pip_size = excluded.pip_size
        """,
        (
            instrument_id,
            kwargs.get("base_currency", ""),
            kwargs.get("quote_currency", ""),
            kwargs.get("pip_size", 0.0001),
        ),
    )


def _save_ois_details(cursor: sqlite3.Cursor, instrument_id: int, **kwargs) -> None:
    """Save OIS-specific details."""
    cursor.execute(
        """
        INSERT INTO ois_rates (instrument_id, currency, tenor, reference_rate)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(instrument_id) DO UPDATE SET
            currency = excluded.currency,
            tenor = excluded.tenor,
            reference_rate = excluded.reference_rate
        """,
        (
            instrument_id,
            kwargs.get("currency", ""),
            kwargs.get("tenor", ""),
            kwargs.get("reference_rate", ""),
        ),
    )


def _save_govt_yield_details(
    cursor: sqlite3.Cursor, instrument_id: int, **kwargs
) -> None:
    """Save government yield-specific details."""
    cursor.execute(
        """
        INSERT INTO govt_yields (instrument_id, country, tenor)
        VALUES (?, ?, ?)
        ON CONFLICT(instrument_id) DO UPDATE SET
            country = excluded.country,
            tenor = excluded.tenor
        """,
        (
            instrument_id,
            kwargs.get("country", ""),
            kwargs.get("tenor", ""),
        ),
    )


def get_instrument(conn: sqlite3.Connection, symbol: str) -> dict | None:
    """
    Get instrument by symbol.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.

    Returns:
        Instrument dict or None if not found.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM instruments WHERE symbol = ?",
        (symbol,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_instrument_id(conn: sqlite3.Connection, symbol: str) -> int | None:
    """
    Get instrument ID by symbol.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.

    Returns:
        Instrument ID or None if not found.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM instruments WHERE symbol = ?", (symbol,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_instruments(
    conn: sqlite3.Connection, asset_class: AssetClass | None = None
) -> list[dict]:
    """
    Get all instruments, optionally filtered by asset class.

    Args:
        conn: Database connection.
        asset_class: Optional asset class filter.

    Returns:
        List of instrument dicts.
    """
    cursor = conn.cursor()
    if asset_class:
        cursor.execute(
            "SELECT * FROM instruments WHERE asset_class = ? ORDER BY symbol",
            (asset_class.value,),
        )
    else:
        cursor.execute("SELECT * FROM instruments ORDER BY symbol")
    return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Time Series CRUD
# =============================================================================


def save_timeseries(
    conn: sqlite3.Connection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity = Granularity.DAILY,
    source_contract: str | None = None,
    adjustment_factor: float = 1.0,
) -> int:
    """
    Save time series data to database.

    Args:
        conn: Database connection.
        instrument_id: Instrument ID.
        data: DataFrame with DatetimeIndex and OHLCV columns.
        granularity: Data granularity.
        source_contract: Source contract for continuous series.
        adjustment_factor: Adjustment factor for continuous series.

    Returns:
        Number of rows saved.

    Raises:
        StorageError: If save fails.
    """
    if data.empty:
        return 0

    try:
        cursor = conn.cursor()

        if granularity == Granularity.DAILY:
            rows_saved = _save_daily_data(
                cursor, instrument_id, data, source_contract, adjustment_factor
            )
        else:
            rows_saved = _save_intraday_data(cursor, instrument_id, data, granularity)

        conn.commit()
        return rows_saved
    except sqlite3.Error as e:
        conn.rollback()
        raise StorageError(f"Failed to save time series: {e}") from e


def _save_daily_data(
    cursor: sqlite3.Cursor,
    instrument_id: int,
    data: pd.DataFrame,
    source_contract: str | None,
    adjustment_factor: float,
) -> int:
    """Save daily OHLCV data."""
    rows = []
    for idx, row in data.iterrows():
        # Convert index to date for ISO format string
        if hasattr(idx, "date"):
            dt: date = idx.date()
        else:
            dt = date.fromisoformat(str(idx)) if not isinstance(idx, date) else idx

        # Determine close price with fallbacks:
        # 1. close (futures)
        # 2. settle (futures)
        # 3. mid price from bid/ask (FX)
        close_price = row.get("close")
        if close_price is None or pd.isna(close_price):
            close_price = row.get("settle")
        if close_price is None or pd.isna(close_price):
            # Calculate mid price from bid/ask for FX data
            bid = row.get("bid")
            ask = row.get("ask")
            if (
                bid is not None
                and ask is not None
                and not pd.isna(bid)
                and not pd.isna(ask)
            ):
                close_price = (float(bid) + float(ask)) / 2

        rows.append(
            (
                instrument_id,
                dt.isoformat(),
                row.get("open"),
                row.get("high"),
                row.get("low"),
                close_price,
                row.get("volume"),
                row.get("open_interest"),
                row.get("settle"),
                adjustment_factor,
                source_contract,
            )
        )

    cursor.executemany(
        """
        INSERT INTO ohlcv_daily (
            instrument_id, date, open, high, low, close,
            volume, open_interest, settle, adjustment_factor, source_contract
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument_id, date) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume,
            open_interest = excluded.open_interest,
            settle = excluded.settle,
            adjustment_factor = excluded.adjustment_factor,
            source_contract = excluded.source_contract
        """,
        rows,
    )
    return len(rows)


def _save_intraday_data(
    cursor: sqlite3.Cursor,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save intraday OHLCV data."""
    rows = []
    for idx, row in data.iterrows():
        # Convert timestamp to ISO format string
        ts_str = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
        rows.append(
            (
                instrument_id,
                ts_str,
                granularity.value,
                row.get("open"),
                row.get("high"),
                row.get("low"),
                row.get("close"),
                row.get("volume"),
            )
        )

    cursor.executemany(
        """
        INSERT INTO ohlcv_intraday (
            instrument_id, timestamp, granularity, open, high, low, close, volume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument_id, timestamp, granularity) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume
        """,
        rows,
    )
    return len(rows)


def load_timeseries(
    conn: sqlite3.Connection,
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: Granularity = Granularity.DAILY,
) -> pd.DataFrame:
    """
    Load time series data from database.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        start_date: Start date filter.
        end_date: End date filter.
        granularity: Data granularity.

    Returns:
        DataFrame with DatetimeIndex and OHLCV columns.

    Raises:
        StorageError: If load fails.
    """
    instrument_id = get_instrument_id(conn, symbol)
    if instrument_id is None:
        return pd.DataFrame()

    try:
        if granularity == Granularity.DAILY:
            return _load_daily_data(conn, instrument_id, start_date, end_date)
        else:
            return _load_intraday_data(
                conn, instrument_id, start_date, end_date, granularity
            )
    except sqlite3.Error as e:
        raise StorageError(f"Failed to load time series for {symbol}: {e}") from e


def _load_daily_data(
    conn: sqlite3.Connection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """Load daily OHLCV data."""
    query = """
        SELECT date, open, high, low, close, volume, open_interest, settle,
               adjustment_factor, source_contract
        FROM ohlcv_daily
        WHERE instrument_id = ?
    """
    params: list = [instrument_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND date <= ?"
        params.append(end_date.isoformat())

    query += " ORDER BY date ASC"

    df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])
    if not df.empty:
        df.set_index("date", inplace=True)
    return df


def _load_intraday_data(
    conn: sqlite3.Connection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
    granularity: Granularity,
) -> pd.DataFrame:
    """Load intraday OHLCV data."""
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv_intraday
        WHERE instrument_id = ? AND granularity = ?
    """
    params: list = [instrument_id, granularity.value]

    if start_date:
        query += " AND timestamp >= ?"
        params.append(f"{start_date.isoformat()}T00:00:00")
    if end_date:
        query += " AND timestamp <= ?"
        params.append(f"{end_date.isoformat()}T23:59:59")

    query += " ORDER BY timestamp ASC"

    df = pd.read_sql_query(query, conn, params=params, parse_dates=["timestamp"])
    if not df.empty:
        df.set_index("timestamp", inplace=True)
    return df


def get_data_range(
    conn: sqlite3.Connection, symbol: str, granularity: Granularity = Granularity.DAILY
) -> tuple[date | None, date | None]:
    """
    Get date range of stored data for an instrument.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        granularity: Data granularity.

    Returns:
        Tuple of (min_date, max_date) or (None, None) if no data.
    """
    instrument_id = get_instrument_id(conn, symbol)
    if instrument_id is None:
        return None, None

    cursor = conn.cursor()
    if granularity == Granularity.DAILY:
        cursor.execute(
            """
            SELECT MIN(date), MAX(date)
            FROM ohlcv_daily
            WHERE instrument_id = ?
            """,
            (instrument_id,),
        )
    else:
        cursor.execute(
            """
            SELECT MIN(DATE(timestamp)), MAX(DATE(timestamp))
            FROM ohlcv_intraday
            WHERE instrument_id = ? AND granularity = ?
            """,
            (instrument_id, granularity.value),
        )

    row = cursor.fetchone()
    if row and row[0] and row[1]:
        return date.fromisoformat(row[0]), date.fromisoformat(row[1])
    return None, None


# =============================================================================
# Roll Events
# =============================================================================


def save_roll_event(
    conn: sqlite3.Connection,
    continuous_symbol: str,
    roll_date: date,
    from_contract: str,
    to_contract: str,
    from_price: float,
    to_price: float,
    roll_method: str,
) -> int:
    """
    Save a roll event for a continuous contract.

    Args:
        conn: Database connection.
        continuous_symbol: Symbol of continuous contract.
        roll_date: Date of the roll.
        from_contract: Contract being rolled out of.
        to_contract: Contract being rolled into.
        from_price: Price of from_contract at roll.
        to_price: Price of to_contract at roll.
        roll_method: Method used to determine roll.

    Returns:
        Roll event ID.

    Raises:
        StorageError: If save fails.
    """
    instrument_id = get_instrument_id(conn, continuous_symbol)
    if instrument_id is None:
        raise StorageError(f"Instrument not found: {continuous_symbol}")

    price_gap = to_price - from_price
    adjustment_factor = to_price / from_price if from_price != 0 else 1.0

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO roll_events (
                continuous_id, roll_date, from_contract, to_contract,
                from_price, to_price, price_gap, adjustment_factor, roll_method
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                instrument_id,
                roll_date.isoformat(),
                from_contract,
                to_contract,
                from_price,
                to_price,
                price_gap,
                adjustment_factor,
                roll_method,
            ),
        )
        roll_id = cursor.fetchone()[0]
        conn.commit()
        return roll_id
    except sqlite3.Error as e:
        conn.rollback()
        raise StorageError(f"Failed to save roll event: {e}") from e


def get_roll_events(conn: sqlite3.Connection, continuous_symbol: str) -> list[dict]:
    """
    Get roll events for a continuous contract.

    Args:
        conn: Database connection.
        continuous_symbol: Symbol of continuous contract.

    Returns:
        List of roll event dicts.
    """
    instrument_id = get_instrument_id(conn, continuous_symbol)
    if instrument_id is None:
        return []

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT roll_date, from_contract, to_contract,
               from_price, to_price, price_gap, adjustment_factor, roll_method
        FROM roll_events
        WHERE continuous_id = ?
        ORDER BY roll_date ASC
        """,
        (instrument_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# Extraction Logging
# =============================================================================


def log_extraction(
    conn: sqlite3.Connection,
    symbol: str,
    start_date: date,
    end_date: date,
    granularity: Granularity,
    rows_fetched: int,
) -> None:
    """
    Log an extraction event.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        start_date: Extraction start date.
        end_date: Extraction end date.
        granularity: Data granularity.
        rows_fetched: Number of rows fetched.
    """
    instrument_id = get_instrument_id(conn, symbol)
    if instrument_id is None:
        return

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO extraction_log (
            instrument_id, start_date, end_date, granularity, rows_fetched
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            instrument_id,
            start_date.isoformat(),
            end_date.isoformat(),
            granularity.value,
            rows_fetched,
        ),
    )
    conn.commit()
