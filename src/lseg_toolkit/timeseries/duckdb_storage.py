"""
DuckDB storage layer for time series data.

Provides functions to store and retrieve time series data,
instruments, and extraction progress in DuckDB format.

DuckDB advantages over SQLite:
- Native Parquet read/write
- Better analytical query performance
- Larger dataset handling
- Columnar storage
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import pandas as pd

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.enums import AssetClass, Granularity

if TYPE_CHECKING:
    from collections.abc import Generator

# =============================================================================
# Default Paths
# =============================================================================

DEFAULT_DUCKDB_PATH: str = "data/timeseries.duckdb"

# =============================================================================
# DuckDB Schema
# =============================================================================

SCHEMA_SQL = """
-- Instruments master table
CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    asset_class VARCHAR NOT NULL,
    lseg_ric VARCHAR NOT NULL,
    exchange VARCHAR,
    currency VARCHAR,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT current_timestamp,
    updated_at TIMESTAMP DEFAULT current_timestamp
);
CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_asset_class ON instruments(asset_class);

-- Futures contract details (extends instruments)
CREATE TABLE IF NOT EXISTS futures_contracts (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying VARCHAR NOT NULL,
    expiry_date DATE,
    expiry_month VARCHAR,
    expiry_year INTEGER,
    continuous_type VARCHAR DEFAULT 'discrete',
    tick_size DOUBLE,
    point_value DOUBLE
);

-- FX spot details (extends instruments)
CREATE TABLE IF NOT EXISTS fx_spots (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    base_currency VARCHAR NOT NULL,
    quote_currency VARCHAR NOT NULL,
    pip_size DOUBLE DEFAULT 0.0001
);

-- OIS rate details (extends instruments)
CREATE TABLE IF NOT EXISTS ois_rates (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    currency VARCHAR NOT NULL,
    tenor VARCHAR NOT NULL,
    reference_rate VARCHAR
);

-- Government yield details (extends instruments)
CREATE TABLE IF NOT EXISTS govt_yields (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    country VARCHAR NOT NULL,
    tenor VARCHAR NOT NULL
);

-- Daily OHLCV data
CREATE TABLE IF NOT EXISTS ohlcv_daily (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    volume BIGINT,
    open_interest BIGINT,
    settle DOUBLE,
    adjustment_factor DOUBLE DEFAULT 1.0,
    source_contract VARCHAR,
    PRIMARY KEY (instrument_id, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_daily_date ON ohlcv_daily(instrument_id, date DESC);

-- Intraday OHLCV data (separate table for performance)
CREATE TABLE IF NOT EXISTS ohlcv_intraday (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    timestamp TIMESTAMP NOT NULL,
    granularity VARCHAR NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    volume BIGINT,
    PRIMARY KEY (instrument_id, timestamp, granularity)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_intraday_ts ON ohlcv_intraday(instrument_id, timestamp DESC);

-- Roll events for continuous contracts
CREATE TABLE IF NOT EXISTS roll_events (
    id INTEGER PRIMARY KEY,
    continuous_id INTEGER NOT NULL REFERENCES instruments(id),
    roll_date DATE NOT NULL,
    from_contract VARCHAR NOT NULL,
    to_contract VARCHAR NOT NULL,
    from_price DOUBLE NOT NULL,
    to_price DOUBLE NOT NULL,
    price_gap DOUBLE NOT NULL,
    adjustment_factor DOUBLE NOT NULL,
    roll_method VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT current_timestamp
);
CREATE INDEX IF NOT EXISTS idx_roll_events_continuous ON roll_events(continuous_id, roll_date DESC);

-- Data extraction metadata
CREATE TABLE IF NOT EXISTS extraction_log (
    id INTEGER PRIMARY KEY,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    granularity VARCHAR NOT NULL,
    rows_fetched INTEGER NOT NULL,
    extracted_at TIMESTAMP DEFAULT current_timestamp
);

-- Extraction progress tracking (for batch extraction)
CREATE TABLE IF NOT EXISTS extraction_progress (
    id INTEGER PRIMARY KEY,
    asset_class VARCHAR NOT NULL,
    instrument VARCHAR NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR DEFAULT 'pending',
    rows_fetched INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_progress ON extraction_progress(asset_class, instrument, status);

-- Create sequence for auto-increment IDs
CREATE SEQUENCE IF NOT EXISTS seq_instruments START 1;
CREATE SEQUENCE IF NOT EXISTS seq_roll_events START 1;
CREATE SEQUENCE IF NOT EXISTS seq_extraction_log START 1;
CREATE SEQUENCE IF NOT EXISTS seq_extraction_progress START 1;

-- Data coverage view for gap analysis
CREATE OR REPLACE VIEW data_coverage AS
SELECT
    i.symbol,
    i.asset_class,
    MIN(o.date) as earliest,
    MAX(o.date) as latest,
    COUNT(*) as days
FROM instruments i
LEFT JOIN ohlcv_daily o ON i.id = o.instrument_id
GROUP BY i.id, i.symbol, i.asset_class;
"""


# =============================================================================
# Connection Management
# =============================================================================


def init_db(db_path: str = DEFAULT_DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """
    Initialize DuckDB database with schema.

    Args:
        db_path: Path to DuckDB database file.

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
        conn = duckdb.connect(db_path)
        conn.execute(SCHEMA_SQL)
        return conn
    except duckdb.Error as e:
        raise StorageError(f"Failed to initialize database: {e}") from e


@contextmanager
def get_connection(
    db_path: str = DEFAULT_DUCKDB_PATH,
) -> Generator[duckdb.DuckDBPyConnection]:
    """
    Context manager for database connection.

    Args:
        db_path: Path to DuckDB database file.

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
    conn: duckdb.DuckDBPyConnection,
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
        # Check if instrument exists
        result = conn.execute(
            "SELECT id FROM instruments WHERE symbol = ?", [symbol]
        ).fetchone()

        if result:
            # Update existing
            instrument_id = result[0]
            conn.execute(
                """
                UPDATE instruments SET
                    name = ?,
                    asset_class = ?,
                    lseg_ric = ?,
                    updated_at = current_timestamp
                WHERE id = ?
                """,
                [name, asset_class.value, lseg_ric, instrument_id],
            )
        else:
            # Insert new
            instrument_id = conn.execute(
                "SELECT nextval('seq_instruments')"
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO instruments (id, symbol, name, asset_class, lseg_ric, updated_at)
                VALUES (?, ?, ?, ?, ?, current_timestamp)
                """,
                [instrument_id, symbol, name, asset_class.value, lseg_ric],
            )

        # Save type-specific details only when relevant kwargs provided
        if asset_class == AssetClass.BOND_FUTURES and kwargs:
            _save_futures_details(conn, instrument_id, **kwargs)
        elif asset_class == AssetClass.FX_SPOT and kwargs:
            _save_fx_details(conn, instrument_id, **kwargs)
        elif asset_class == AssetClass.OIS and kwargs:
            _save_ois_details(conn, instrument_id, **kwargs)
        elif asset_class == AssetClass.GOVT_YIELD and kwargs:
            _save_govt_yield_details(conn, instrument_id, **kwargs)

        return instrument_id
    except duckdb.Error as e:
        raise StorageError(f"Failed to save instrument {symbol}: {e}") from e


def _save_futures_details(
    conn: duckdb.DuckDBPyConnection, instrument_id: int, **kwargs
) -> None:
    """Save futures-specific details."""
    # Check if exists
    result = conn.execute(
        "SELECT 1 FROM futures_contracts WHERE instrument_id = ?", [instrument_id]
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE futures_contracts SET
                underlying = ?,
                expiry_date = ?,
                expiry_month = ?,
                expiry_year = ?,
                continuous_type = ?,
                tick_size = ?,
                point_value = ?
            WHERE instrument_id = ?
            """,
            [
                kwargs.get("underlying", ""),
                kwargs.get("expiry_date"),
                kwargs.get("expiry_month"),
                kwargs.get("expiry_year"),
                kwargs.get("continuous_type", "discrete"),
                kwargs.get("tick_size"),
                kwargs.get("point_value"),
                instrument_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO futures_contracts (
                instrument_id, underlying, expiry_date, expiry_month, expiry_year,
                continuous_type, tick_size, point_value
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                instrument_id,
                kwargs.get("underlying", ""),
                kwargs.get("expiry_date"),
                kwargs.get("expiry_month"),
                kwargs.get("expiry_year"),
                kwargs.get("continuous_type", "discrete"),
                kwargs.get("tick_size"),
                kwargs.get("point_value"),
            ],
        )


def _save_fx_details(
    conn: duckdb.DuckDBPyConnection, instrument_id: int, **kwargs
) -> None:
    """Save FX-specific details."""
    result = conn.execute(
        "SELECT 1 FROM fx_spots WHERE instrument_id = ?", [instrument_id]
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE fx_spots SET
                base_currency = ?,
                quote_currency = ?,
                pip_size = ?
            WHERE instrument_id = ?
            """,
            [
                kwargs.get("base_currency", ""),
                kwargs.get("quote_currency", ""),
                kwargs.get("pip_size", 0.0001),
                instrument_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO fx_spots (instrument_id, base_currency, quote_currency, pip_size)
            VALUES (?, ?, ?, ?)
            """,
            [
                instrument_id,
                kwargs.get("base_currency", ""),
                kwargs.get("quote_currency", ""),
                kwargs.get("pip_size", 0.0001),
            ],
        )


def _save_ois_details(
    conn: duckdb.DuckDBPyConnection, instrument_id: int, **kwargs
) -> None:
    """Save OIS-specific details."""
    result = conn.execute(
        "SELECT 1 FROM ois_rates WHERE instrument_id = ?", [instrument_id]
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE ois_rates SET
                currency = ?,
                tenor = ?,
                reference_rate = ?
            WHERE instrument_id = ?
            """,
            [
                kwargs.get("currency", ""),
                kwargs.get("tenor", ""),
                kwargs.get("reference_rate", ""),
                instrument_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO ois_rates (instrument_id, currency, tenor, reference_rate)
            VALUES (?, ?, ?, ?)
            """,
            [
                instrument_id,
                kwargs.get("currency", ""),
                kwargs.get("tenor", ""),
                kwargs.get("reference_rate", ""),
            ],
        )


def _save_govt_yield_details(
    conn: duckdb.DuckDBPyConnection, instrument_id: int, **kwargs
) -> None:
    """Save government yield-specific details."""
    result = conn.execute(
        "SELECT 1 FROM govt_yields WHERE instrument_id = ?", [instrument_id]
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE govt_yields SET
                country = ?,
                tenor = ?
            WHERE instrument_id = ?
            """,
            [
                kwargs.get("country", ""),
                kwargs.get("tenor", ""),
                instrument_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO govt_yields (instrument_id, country, tenor)
            VALUES (?, ?, ?)
            """,
            [
                instrument_id,
                kwargs.get("country", ""),
                kwargs.get("tenor", ""),
            ],
        )


def get_instrument(conn: duckdb.DuckDBPyConnection, symbol: str) -> dict | None:
    """
    Get instrument by symbol.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.

    Returns:
        Instrument dict or None if not found.
    """
    result = conn.execute(
        "SELECT * FROM instruments WHERE symbol = ?", [symbol]
    ).fetchone()
    if result:
        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result, strict=True))
    return None


def get_instrument_id(conn: duckdb.DuckDBPyConnection, symbol: str) -> int | None:
    """
    Get instrument ID by symbol.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.

    Returns:
        Instrument ID or None if not found.
    """
    result = conn.execute(
        "SELECT id FROM instruments WHERE symbol = ?", [symbol]
    ).fetchone()
    return result[0] if result else None


def get_instruments(
    conn: duckdb.DuckDBPyConnection, asset_class: AssetClass | None = None
) -> list[dict]:
    """
    Get all instruments, optionally filtered by asset class.

    Args:
        conn: Database connection.
        asset_class: Optional asset class filter.

    Returns:
        List of instrument dicts.
    """
    if asset_class:
        result = conn.execute(
            "SELECT * FROM instruments WHERE asset_class = ? ORDER BY symbol",
            [asset_class.value],
        )
    else:
        result = conn.execute("SELECT * FROM instruments ORDER BY symbol")

    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


# =============================================================================
# Time Series CRUD
# =============================================================================


def save_timeseries(
    conn: duckdb.DuckDBPyConnection,
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
        if granularity == Granularity.DAILY:
            rows_saved = _save_daily_data(
                conn, instrument_id, data, source_contract, adjustment_factor
            )
        else:
            rows_saved = _save_intraday_data(conn, instrument_id, data, granularity)

        return rows_saved
    except duckdb.Error as e:
        raise StorageError(f"Failed to save time series: {e}") from e


def _save_daily_data(
    conn: duckdb.DuckDBPyConnection,
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

        # Determine close price with fallbacks
        close_price = row.get("close")
        if close_price is None or pd.isna(close_price):
            close_price = row.get("settle")
        if close_price is None or pd.isna(close_price):
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
            {
                "instrument_id": instrument_id,
                "date": dt,
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": close_price,
                "volume": row.get("volume"),
                "open_interest": row.get("open_interest"),
                "settle": row.get("settle"),
                "adjustment_factor": adjustment_factor,
                "source_contract": source_contract,
            }
        )

    # Create a DataFrame for bulk insert
    df = pd.DataFrame(rows)

    # Use INSERT OR REPLACE for upsert behavior
    for _, row in df.iterrows():
        conn.execute(
            """
            INSERT OR REPLACE INTO ohlcv_daily (
                instrument_id, date, open, high, low, close,
                volume, open_interest, settle, adjustment_factor, source_contract
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["instrument_id"],
                row["date"],
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"],
                row["open_interest"],
                row["settle"],
                row["adjustment_factor"],
                row["source_contract"],
            ],
        )

    return len(rows)


def _save_intraday_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save intraday OHLCV data."""
    rows: list[dict] = []
    for idx, df_row in data.iterrows():
        # Convert timestamp
        if hasattr(idx, "to_pydatetime"):
            ts = idx.to_pydatetime()
        else:
            ts = datetime.fromisoformat(str(idx))

        rows.append(
            {
                "instrument_id": instrument_id,
                "timestamp": ts,
                "granularity": granularity.value,
                "open": df_row.get("open"),
                "high": df_row.get("high"),
                "low": df_row.get("low"),
                "close": df_row.get("close"),
                "volume": df_row.get("volume"),
            }
        )

    for row in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO ohlcv_intraday (
                instrument_id, timestamp, granularity, open, high, low, close, volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["instrument_id"],
                row["timestamp"],
                row["granularity"],
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"],
            ],
        )

    return len(rows)


def load_timeseries(
    conn: duckdb.DuckDBPyConnection,
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
    except duckdb.Error as e:
        raise StorageError(f"Failed to load time series for {symbol}: {e}") from e


def _load_daily_data(
    conn: duckdb.DuckDBPyConnection,
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


def _load_intraday_data(
    conn: duckdb.DuckDBPyConnection,
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
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND timestamp <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " ORDER BY timestamp ASC"

    df = conn.execute(query, params).fetchdf()
    if not df.empty:
        df.set_index("timestamp", inplace=True)
    return df


def get_data_range(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    granularity: Granularity = Granularity.DAILY,
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

    if granularity == Granularity.DAILY:
        result = conn.execute(
            """
            SELECT MIN(date), MAX(date)
            FROM ohlcv_daily
            WHERE instrument_id = ?
            """,
            [instrument_id],
        ).fetchone()
    else:
        result = conn.execute(
            """
            SELECT CAST(MIN(timestamp) AS DATE), CAST(MAX(timestamp) AS DATE)
            FROM ohlcv_intraday
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


# =============================================================================
# Roll Events
# =============================================================================


def save_roll_event(
    conn: duckdb.DuckDBPyConnection,
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
        roll_id = conn.execute("SELECT nextval('seq_roll_events')").fetchone()[0]
        conn.execute(
            """
            INSERT INTO roll_events (
                id, continuous_id, roll_date, from_contract, to_contract,
                from_price, to_price, price_gap, adjustment_factor, roll_method
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                roll_id,
                instrument_id,
                roll_date,
                from_contract,
                to_contract,
                from_price,
                to_price,
                price_gap,
                adjustment_factor,
                roll_method,
            ],
        )
        return roll_id
    except duckdb.Error as e:
        raise StorageError(f"Failed to save roll event: {e}") from e


def get_roll_events(
    conn: duckdb.DuckDBPyConnection, continuous_symbol: str
) -> list[dict]:
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

    result = conn.execute(
        """
        SELECT roll_date, from_contract, to_contract,
               from_price, to_price, price_gap, adjustment_factor, roll_method
        FROM roll_events
        WHERE continuous_id = ?
        ORDER BY roll_date ASC
        """,
        [instrument_id],
    )
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


# =============================================================================
# Extraction Logging
# =============================================================================


def log_extraction(
    conn: duckdb.DuckDBPyConnection,
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

    log_id = conn.execute("SELECT nextval('seq_extraction_log')").fetchone()[0]
    conn.execute(
        """
        INSERT INTO extraction_log (
            id, instrument_id, start_date, end_date, granularity, rows_fetched
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [log_id, instrument_id, start_date, end_date, granularity.value, rows_fetched],
    )


# =============================================================================
# Extraction Progress Tracking
# =============================================================================


def create_extraction_progress(
    conn: duckdb.DuckDBPyConnection,
    asset_class: str,
    instrument: str,
    start_date: date,
    end_date: date,
) -> int:
    """
    Create an extraction progress record.

    Args:
        conn: Database connection.
        asset_class: Asset class being extracted.
        instrument: Instrument symbol.
        start_date: Extraction start date.
        end_date: Extraction end date.

    Returns:
        Progress record ID.
    """
    progress_id = conn.execute("SELECT nextval('seq_extraction_progress')").fetchone()[
        0
    ]
    conn.execute(
        """
        INSERT INTO extraction_progress (
            id, asset_class, instrument, start_date, end_date, status
        )
        VALUES (?, ?, ?, ?, ?, 'pending')
        """,
        [progress_id, asset_class, instrument, start_date, end_date],
    )
    return progress_id


def update_extraction_progress(
    conn: duckdb.DuckDBPyConnection,
    progress_id: int,
    status: str,
    rows_fetched: int | None = None,
    error_message: str | None = None,
) -> None:
    """
    Update extraction progress record.

    Args:
        conn: Database connection.
        progress_id: Progress record ID.
        status: New status ('running', 'complete', 'failed').
        rows_fetched: Number of rows fetched (optional).
        error_message: Error message if failed (optional).
    """
    if status == "running":
        conn.execute(
            """
            UPDATE extraction_progress
            SET status = ?, started_at = current_timestamp
            WHERE id = ?
            """,
            [status, progress_id],
        )
    elif status == "complete":
        conn.execute(
            """
            UPDATE extraction_progress
            SET status = ?, rows_fetched = ?, completed_at = current_timestamp
            WHERE id = ?
            """,
            [status, rows_fetched, progress_id],
        )
    elif status == "failed":
        conn.execute(
            """
            UPDATE extraction_progress
            SET status = ?, error_message = ?, completed_at = current_timestamp
            WHERE id = ?
            """,
            [status, error_message, progress_id],
        )


def get_extraction_progress(
    conn: duckdb.DuckDBPyConnection,
    asset_class: str | None = None,
    instrument: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """
    Get extraction progress records.

    Args:
        conn: Database connection.
        asset_class: Filter by asset class.
        instrument: Filter by instrument.
        status: Filter by status.

    Returns:
        List of progress record dicts.
    """
    query = "SELECT * FROM extraction_progress WHERE 1=1"
    params = []

    if asset_class:
        query += " AND asset_class = ?"
        params.append(asset_class)
    if instrument:
        query += " AND instrument = ?"
        params.append(instrument)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id"

    result = conn.execute(query, params)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def get_data_coverage(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Get data coverage summary from the view.

    Args:
        conn: Database connection.

    Returns:
        DataFrame with coverage information.
    """
    return conn.execute("SELECT * FROM data_coverage ORDER BY symbol").fetchdf()


# =============================================================================
# Parquet Export
# =============================================================================


def export_to_parquet(
    conn: duckdb.DuckDBPyConnection,
    output_path: str,
    symbol: str | None = None,
    asset_class: AssetClass | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    """
    Export data to Parquet using DuckDB's native COPY.

    Args:
        conn: Database connection.
        output_path: Output file path (should end with .parquet).
        symbol: Filter by instrument symbol.
        asset_class: Filter by asset class.
        start_date: Filter by start date.
        end_date: Filter by end date.

    Returns:
        Path to exported file.

    Raises:
        StorageError: If export fails.
    """
    try:
        # Create output directory if needed
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Build query
        query = """
            SELECT
                i.symbol,
                i.asset_class,
                i.lseg_ric,
                o.date,
                o.open,
                o.high,
                o.low,
                o.close,
                o.volume,
                o.open_interest,
                o.settle
            FROM ohlcv_daily o
            JOIN instruments i ON i.id = o.instrument_id
            WHERE 1=1
        """
        conditions = []

        if symbol:
            conditions.append(f"AND i.symbol = '{symbol}'")
        if asset_class:
            conditions.append(f"AND i.asset_class = '{asset_class.value}'")
        if start_date:
            conditions.append(f"AND o.date >= '{start_date.isoformat()}'")
        if end_date:
            conditions.append(f"AND o.date <= '{end_date.isoformat()}'")

        query += " ".join(conditions)
        query += " ORDER BY i.symbol, o.date"

        # Export to Parquet
        conn.execute(
            f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
        )

        return output_path
    except duckdb.Error as e:
        raise StorageError(f"Failed to export to Parquet: {e}") from e


def export_symbol_to_parquet(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    output_dir: str,
    partition_by_year: bool = True,
) -> list[str]:
    """
    Export a single symbol to Parquet, optionally partitioned by year.

    Args:
        conn: Database connection.
        symbol: Instrument symbol to export.
        output_dir: Output directory.
        partition_by_year: Whether to partition by year.

    Returns:
        List of exported file paths.

    Raises:
        StorageError: If export fails.
    """
    try:
        instrument_id = get_instrument_id(conn, symbol)
        if instrument_id is None:
            raise StorageError(f"Instrument not found: {symbol}")

        output_path = Path(output_dir) / symbol
        output_path.mkdir(parents=True, exist_ok=True)

        exported_files = []

        if partition_by_year:
            # Get distinct years
            years = conn.execute(
                """
                SELECT DISTINCT EXTRACT(YEAR FROM date) as year
                FROM ohlcv_daily
                WHERE instrument_id = ?
                ORDER BY year
                """,
                [instrument_id],
            ).fetchall()

            for (year,) in years:
                file_path = str(output_path / f"{int(year)}.parquet")
                query = f"""
                    SELECT date, open, high, low, close, volume, open_interest, settle
                    FROM ohlcv_daily
                    WHERE instrument_id = {instrument_id}
                    AND EXTRACT(YEAR FROM date) = {int(year)}
                    ORDER BY date
                """
                conn.execute(
                    f"COPY ({query}) TO '{file_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
                )
                exported_files.append(file_path)
        else:
            file_path = str(output_path / f"{symbol}.parquet")
            query = f"""
                SELECT date, open, high, low, close, volume, open_interest, settle
                FROM ohlcv_daily
                WHERE instrument_id = {instrument_id}
                ORDER BY date
            """
            conn.execute(
                f"COPY ({query}) TO '{file_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
            )
            exported_files.append(file_path)

        return exported_files
    except duckdb.Error as e:
        raise StorageError(f"Failed to export {symbol} to Parquet: {e}") from e


# =============================================================================
# Migration from SQLite
# =============================================================================


def migrate_from_sqlite(
    sqlite_path: str,
    duckdb_conn: duckdb.DuckDBPyConnection,
) -> dict[str, int]:
    """
    Migrate data from SQLite to DuckDB.

    Args:
        sqlite_path: Path to SQLite database.
        duckdb_conn: DuckDB connection to migrate into.

    Returns:
        Dict with counts of migrated records per table.

    Raises:
        StorageError: If migration fails.
    """
    try:
        # Install and load SQLite extension
        duckdb_conn.execute("INSTALL sqlite; LOAD sqlite;")

        # Attach SQLite database
        duckdb_conn.execute(f"ATTACH '{sqlite_path}' AS sqlite_db (TYPE SQLITE)")

        counts = {}

        # Migrate instruments
        duckdb_conn.execute("""
            INSERT INTO instruments (id, symbol, name, asset_class, lseg_ric, created_at, updated_at)
            SELECT id, symbol, name, asset_class, lseg_ric, created_at, updated_at
            FROM sqlite_db.instruments
            ON CONFLICT (symbol) DO NOTHING
        """)
        counts["instruments"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM instruments"
        ).fetchone()[0]

        # Update sequence
        max_id = duckdb_conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM instruments"
        ).fetchone()[0]
        if max_id > 0:
            duckdb_conn.execute(f"SELECT setval('seq_instruments', {max_id + 1})")

        # Migrate futures_contracts
        duckdb_conn.execute("""
            INSERT INTO futures_contracts
            SELECT * FROM sqlite_db.futures_contracts
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["futures_contracts"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM futures_contracts"
        ).fetchone()[0]

        # Migrate fx_spots
        duckdb_conn.execute("""
            INSERT INTO fx_spots
            SELECT * FROM sqlite_db.fx_spots
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["fx_spots"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM fx_spots"
        ).fetchone()[0]

        # Migrate ois_rates
        duckdb_conn.execute("""
            INSERT INTO ois_rates
            SELECT * FROM sqlite_db.ois_rates
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["ois_rates"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM ois_rates"
        ).fetchone()[0]

        # Migrate govt_yields
        duckdb_conn.execute("""
            INSERT INTO govt_yields
            SELECT * FROM sqlite_db.govt_yields
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["govt_yields"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM govt_yields"
        ).fetchone()[0]

        # Migrate ohlcv_daily
        duckdb_conn.execute("""
            INSERT INTO ohlcv_daily
            SELECT * FROM sqlite_db.ohlcv_daily
            ON CONFLICT (instrument_id, date) DO NOTHING
        """)
        counts["ohlcv_daily"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM ohlcv_daily"
        ).fetchone()[0]

        # Migrate ohlcv_intraday
        duckdb_conn.execute("""
            INSERT INTO ohlcv_intraday
            SELECT * FROM sqlite_db.ohlcv_intraday
            ON CONFLICT (instrument_id, timestamp, granularity) DO NOTHING
        """)
        counts["ohlcv_intraday"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM ohlcv_intraday"
        ).fetchone()[0]

        # Migrate roll_events
        duckdb_conn.execute("""
            INSERT INTO roll_events
            SELECT * FROM sqlite_db.roll_events
            ON CONFLICT DO NOTHING
        """)
        counts["roll_events"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM roll_events"
        ).fetchone()[0]

        # Update roll_events sequence
        max_roll_id = duckdb_conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM roll_events"
        ).fetchone()[0]
        if max_roll_id > 0:
            duckdb_conn.execute(f"SELECT setval('seq_roll_events', {max_roll_id + 1})")

        # Migrate extraction_log
        duckdb_conn.execute("""
            INSERT INTO extraction_log
            SELECT * FROM sqlite_db.extraction_log
            ON CONFLICT DO NOTHING
        """)
        counts["extraction_log"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM extraction_log"
        ).fetchone()[0]

        # Update extraction_log sequence
        max_log_id = duckdb_conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM extraction_log"
        ).fetchone()[0]
        if max_log_id > 0:
            duckdb_conn.execute(
                f"SELECT setval('seq_extraction_log', {max_log_id + 1})"
            )

        # Detach SQLite database
        duckdb_conn.execute("DETACH sqlite_db")

        return counts
    except duckdb.Error as e:
        raise StorageError(f"Failed to migrate from SQLite: {e}") from e
