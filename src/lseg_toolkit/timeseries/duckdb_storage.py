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
from lseg_toolkit.timeseries.enums import AssetClass, DataShape, Granularity

if TYPE_CHECKING:
    from collections.abc import Generator

# =============================================================================
# Asset Class to Data Shape Mapping
# =============================================================================

ASSET_CLASS_TO_DATA_SHAPE: dict[AssetClass, DataShape] = {
    # OHLCV (exchange-traded)
    AssetClass.BOND_FUTURES: DataShape.OHLCV,
    AssetClass.STIR_FUTURES: DataShape.OHLCV,
    AssetClass.INDEX_FUTURES: DataShape.OHLCV,
    AssetClass.FX_FUTURES: DataShape.OHLCV,
    AssetClass.COMMODITY: DataShape.OHLCV,
    AssetClass.EQUITY: DataShape.OHLCV,
    # Quote (dealer-quoted)
    AssetClass.FX_SPOT: DataShape.QUOTE,
    AssetClass.FX_FORWARD: DataShape.QUOTE,
    # Rate (IR derivatives)
    AssetClass.OIS: DataShape.RATE,
    AssetClass.IRS: DataShape.RATE,
    AssetClass.FRA: DataShape.RATE,
    AssetClass.DEPOSIT: DataShape.RATE,
    AssetClass.REPO: DataShape.RATE,
    AssetClass.CDS: DataShape.RATE,
    # Bond (govt/corp yields)
    AssetClass.GOVT_YIELD: DataShape.BOND,
    AssetClass.CORP_BOND: DataShape.BOND,
    # Fixing (daily benchmark rates)
    AssetClass.FIXING: DataShape.FIXING,
}


def get_data_shape(asset_class: AssetClass) -> DataShape:
    """Get the data shape for an asset class."""
    return ASSET_CLASS_TO_DATA_SHAPE.get(asset_class, DataShape.OHLCV)


# =============================================================================
# Default Paths
# =============================================================================

DEFAULT_DUCKDB_PATH: str = "data/timeseries.duckdb"

# =============================================================================
# DuckDB Schema
# =============================================================================

SCHEMA_SQL = """
-- =============================================================================
-- Instruments master table
-- =============================================================================
CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    asset_class VARCHAR NOT NULL,
    data_shape VARCHAR NOT NULL,  -- 'ohlcv', 'quote', 'rate', 'bond', 'fixing'
    lseg_ric VARCHAR NOT NULL,
    exchange VARCHAR,
    currency VARCHAR,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT current_timestamp,
    updated_at TIMESTAMP DEFAULT current_timestamp
);
CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_asset_class ON instruments(asset_class);
CREATE INDEX IF NOT EXISTS idx_instruments_data_shape ON instruments(data_shape);

-- =============================================================================
-- Instrument Detail Tables
-- =============================================================================

-- Futures contract details
CREATE TABLE IF NOT EXISTS instrument_futures (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying VARCHAR NOT NULL,
    exchange VARCHAR,
    expiry_date DATE,
    contract_month VARCHAR,  -- 'H5', 'M5'
    continuous_type VARCHAR DEFAULT 'discrete',
    tick_size DOUBLE,
    point_value DOUBLE
);

-- FX spot details
CREATE TABLE IF NOT EXISTS instrument_fx (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    base_currency VARCHAR NOT NULL,
    quote_currency VARCHAR NOT NULL,
    pip_size DOUBLE DEFAULT 0.0001,
    tenor VARCHAR  -- NULL for spot, '1W', '1M' for forwards
);

-- Rate instrument details (OIS, IRS, FRA, Repo)
CREATE TABLE IF NOT EXISTS instrument_rate (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    rate_type VARCHAR NOT NULL,  -- 'OIS', 'IRS', 'FRA', 'REPO', 'DEPOSIT'
    currency VARCHAR NOT NULL,
    tenor VARCHAR NOT NULL,
    reference_rate VARCHAR,  -- 'SOFR', 'EURIBOR', 'SONIA'
    day_count VARCHAR,  -- 'ACT/360', 'ACT/365', 'ACT/ACT'
    payment_frequency VARCHAR,  -- 'annual', 'semiannual', 'quarterly', 'monthly'
    business_day_conv VARCHAR,  -- 'modified_following', 'following', 'preceding'
    calendar VARCHAR,  -- 'TARGET', 'US', 'UK', 'JP'
    settlement_days INTEGER DEFAULT 2,  -- T+2 for most swaps
    paired_instrument_id INTEGER REFERENCES instruments(id)
);

-- Bond instrument details (govt/corp yields)
CREATE TABLE IF NOT EXISTS instrument_bond (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    issuer_type VARCHAR NOT NULL,  -- 'GOVT', 'CORP', 'MUNI', 'AGENCY'
    country VARCHAR,
    tenor VARCHAR NOT NULL,
    coupon_rate DOUBLE,
    coupon_frequency VARCHAR,  -- 'semiannual' (UST), 'annual' (Bunds), 'quarterly'
    day_count VARCHAR,  -- 'ACT/ACT', '30/360', 'ACT/365'
    maturity_date DATE,
    settlement_days INTEGER DEFAULT 1,  -- T+1 for UST, T+2 for most others
    credit_rating VARCHAR,
    sector VARCHAR
);

-- Fixing instrument details (SOFR, ESTR, SONIA)
CREATE TABLE IF NOT EXISTS instrument_fixing (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    rate_name VARCHAR NOT NULL,  -- 'SOFR', 'ESTR', 'SONIA', 'EURIBOR'
    tenor VARCHAR,  -- NULL for overnight, '3M' for EURIBOR3M
    fixing_time VARCHAR,  -- '08:00 NY', '11:00 London'
    administrator VARCHAR  -- 'Fed', 'ECB', 'BoE'
);

-- =============================================================================
-- Timeseries Tables (by data shape)
-- =============================================================================

-- OHLCV data (futures, equities, commodities, indices)
CREATE TABLE IF NOT EXISTS timeseries_ohlcv (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMP NOT NULL,
    granularity VARCHAR NOT NULL,  -- 'minute', '5min', '30min', 'hourly', 'daily'
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    volume DOUBLE,
    settle DOUBLE,
    open_interest DOUBLE,
    vwap DOUBLE,
    source_contract VARCHAR,
    adjustment_factor DOUBLE DEFAULT 1.0,
    PRIMARY KEY (instrument_id, ts, granularity)
);
CREATE INDEX IF NOT EXISTS idx_timeseries_ohlcv_ts ON timeseries_ohlcv(instrument_id, ts DESC);

-- Quote data (FX spot, FX forwards)
CREATE TABLE IF NOT EXISTS timeseries_quote (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMP NOT NULL,
    granularity VARCHAR NOT NULL,
    bid DOUBLE,
    ask DOUBLE,
    mid DOUBLE,
    open_bid DOUBLE,
    bid_high DOUBLE,
    bid_low DOUBLE,
    open_ask DOUBLE,
    ask_high DOUBLE,
    ask_low DOUBLE,
    forward_points DOUBLE,
    PRIMARY KEY (instrument_id, ts, granularity)
);
CREATE INDEX IF NOT EXISTS idx_timeseries_quote_ts ON timeseries_quote(instrument_id, ts DESC);

-- Rate data (OIS, IRS, FRA, Repo, CDS)
CREATE TABLE IF NOT EXISTS timeseries_rate (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMP NOT NULL,
    granularity VARCHAR NOT NULL,
    rate DOUBLE NOT NULL,
    bid DOUBLE,
    ask DOUBLE,
    open_rate DOUBLE,  -- Opening rate (OPEN_BID/ASK mid)
    high_rate DOUBLE,  -- High rate of day
    low_rate DOUBLE,   -- Low rate of day
    rate_2 DOUBLE,  -- Secondary rate (floating leg / reverse repo)
    spread DOUBLE,
    reference_rate VARCHAR,
    side VARCHAR,  -- 'PAY_FIXED', 'RECEIVE_FIXED', 'REPO', 'REVERSE'
    PRIMARY KEY (instrument_id, ts, granularity)
);
CREATE INDEX IF NOT EXISTS idx_timeseries_rate_ts ON timeseries_rate(instrument_id, ts DESC);

-- Bond data (govt yields, corp bonds)
CREATE TABLE IF NOT EXISTS timeseries_bond (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMP NOT NULL,
    granularity VARCHAR NOT NULL,
    price DOUBLE,  -- Clean price
    dirty_price DOUBLE,  -- Full price (clean + accrued)
    accrued_interest DOUBLE,  -- Accrued interest
    bid DOUBLE,
    ask DOUBLE,
    open_price DOUBLE,  -- Opening price
    open_yield DOUBLE,  -- Opening yield
    yield DOUBLE NOT NULL,
    yield_bid DOUBLE,
    yield_ask DOUBLE,
    yield_high DOUBLE,
    yield_low DOUBLE,
    mac_duration DOUBLE,  -- Macaulay duration (for immunization)
    mod_duration DOUBLE,  -- Modified duration
    convexity DOUBLE,
    dv01 DOUBLE,
    z_spread DOUBLE,
    oas DOUBLE,
    PRIMARY KEY (instrument_id, ts, granularity)
);
CREATE INDEX IF NOT EXISTS idx_timeseries_bond_ts ON timeseries_bond(instrument_id, ts DESC);

-- Fixing data (SOFR, ESTR, SONIA, EURIBOR)
CREATE TABLE IF NOT EXISTS timeseries_fixing (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    value DOUBLE NOT NULL,
    volume DOUBLE,
    PRIMARY KEY (instrument_id, date)
);
CREATE INDEX IF NOT EXISTS idx_timeseries_fixing_date ON timeseries_fixing(instrument_id, date DESC);

-- =============================================================================
-- Legacy Tables (for backwards compatibility during migration)
-- =============================================================================

-- Daily OHLCV data (legacy - use timeseries_ohlcv instead)
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

-- Intraday OHLCV data (legacy - use timeseries_ohlcv instead)
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

-- Legacy detail tables (keep for migration)
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

CREATE TABLE IF NOT EXISTS fx_spots (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    base_currency VARCHAR NOT NULL,
    quote_currency VARCHAR NOT NULL,
    pip_size DOUBLE DEFAULT 0.0001
);

CREATE TABLE IF NOT EXISTS ois_rates (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    currency VARCHAR NOT NULL,
    tenor VARCHAR NOT NULL,
    reference_rate VARCHAR
);

CREATE TABLE IF NOT EXISTS govt_yields (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    country VARCHAR NOT NULL,
    tenor VARCHAR NOT NULL
);

-- =============================================================================
-- Metadata Tables
-- =============================================================================

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

-- =============================================================================
-- Sequences
-- =============================================================================
CREATE SEQUENCE IF NOT EXISTS seq_instruments START 1;
CREATE SEQUENCE IF NOT EXISTS seq_roll_events START 1;
CREATE SEQUENCE IF NOT EXISTS seq_extraction_log START 1;
CREATE SEQUENCE IF NOT EXISTS seq_extraction_progress START 1;

-- =============================================================================
-- Views
-- =============================================================================

-- Data coverage view for gap analysis (uses new timeseries_ohlcv table)
CREATE OR REPLACE VIEW data_coverage AS
SELECT
    i.symbol,
    i.asset_class,
    i.data_shape,
    CASE i.data_shape
        WHEN 'ohlcv' THEN (SELECT MIN(ts)::DATE FROM timeseries_ohlcv WHERE instrument_id = i.id)
        WHEN 'quote' THEN (SELECT MIN(ts)::DATE FROM timeseries_quote WHERE instrument_id = i.id)
        WHEN 'rate' THEN (SELECT MIN(ts)::DATE FROM timeseries_rate WHERE instrument_id = i.id)
        WHEN 'bond' THEN (SELECT MIN(ts)::DATE FROM timeseries_bond WHERE instrument_id = i.id)
        WHEN 'fixing' THEN (SELECT MIN(date) FROM timeseries_fixing WHERE instrument_id = i.id)
    END as earliest,
    CASE i.data_shape
        WHEN 'ohlcv' THEN (SELECT MAX(ts)::DATE FROM timeseries_ohlcv WHERE instrument_id = i.id)
        WHEN 'quote' THEN (SELECT MAX(ts)::DATE FROM timeseries_quote WHERE instrument_id = i.id)
        WHEN 'rate' THEN (SELECT MAX(ts)::DATE FROM timeseries_rate WHERE instrument_id = i.id)
        WHEN 'bond' THEN (SELECT MAX(ts)::DATE FROM timeseries_bond WHERE instrument_id = i.id)
        WHEN 'fixing' THEN (SELECT MAX(date) FROM timeseries_fixing WHERE instrument_id = i.id)
    END as latest,
    CASE i.data_shape
        WHEN 'ohlcv' THEN (SELECT COUNT(*) FROM timeseries_ohlcv WHERE instrument_id = i.id)
        WHEN 'quote' THEN (SELECT COUNT(*) FROM timeseries_quote WHERE instrument_id = i.id)
        WHEN 'rate' THEN (SELECT COUNT(*) FROM timeseries_rate WHERE instrument_id = i.id)
        WHEN 'bond' THEN (SELECT COUNT(*) FROM timeseries_bond WHERE instrument_id = i.id)
        WHEN 'fixing' THEN (SELECT COUNT(*) FROM timeseries_fixing WHERE instrument_id = i.id)
    END as row_count
FROM instruments i;
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
    data_shape: DataShape | None = None,
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
        data_shape: Data shape (auto-inferred from asset_class if not provided).
        **kwargs: Additional fields for specific instrument types.

    Returns:
        Instrument ID.

    Raises:
        StorageError: If save fails.
    """
    # Auto-infer data_shape from asset_class if not provided
    if data_shape is None:
        data_shape = get_data_shape(asset_class)

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
                    data_shape = ?,
                    lseg_ric = ?,
                    updated_at = current_timestamp
                WHERE id = ?
                """,
                [name, asset_class.value, data_shape.value, lseg_ric, instrument_id],
            )
        else:
            # Insert new
            instrument_id = conn.execute(
                "SELECT nextval('seq_instruments')"
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO instruments (id, symbol, name, asset_class, data_shape, lseg_ric, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, current_timestamp)
                """,
                [
                    instrument_id,
                    symbol,
                    name,
                    asset_class.value,
                    data_shape.value,
                    lseg_ric,
                ],
            )

        # Save type-specific details based on data_shape
        if data_shape == DataShape.OHLCV and kwargs:
            _save_futures_details(conn, instrument_id, **kwargs)
        elif data_shape == DataShape.QUOTE and kwargs:
            _save_fx_details(conn, instrument_id, **kwargs)
        elif data_shape == DataShape.RATE and kwargs:
            _save_rate_details(conn, instrument_id, **kwargs)
        elif data_shape == DataShape.BOND and kwargs:
            _save_bond_details(conn, instrument_id, **kwargs)
        elif data_shape == DataShape.FIXING and kwargs:
            _save_fixing_details(conn, instrument_id, **kwargs)

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


def _save_rate_details(
    conn: duckdb.DuckDBPyConnection, instrument_id: int, **kwargs
) -> None:
    """Save rate instrument details (OIS, IRS, FRA, Repo)."""
    result = conn.execute(
        "SELECT 1 FROM instrument_rate WHERE instrument_id = ?", [instrument_id]
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE instrument_rate SET
                rate_type = ?,
                currency = ?,
                tenor = ?,
                reference_rate = ?,
                day_count = ?,
                payment_frequency = ?,
                business_day_conv = ?,
                calendar = ?,
                settlement_days = ?,
                paired_instrument_id = ?
            WHERE instrument_id = ?
            """,
            [
                kwargs.get("rate_type", "OIS"),
                kwargs.get("currency", ""),
                kwargs.get("tenor", ""),
                kwargs.get("reference_rate"),
                kwargs.get("day_count"),
                kwargs.get("payment_frequency"),
                kwargs.get("business_day_conv"),
                kwargs.get("calendar"),
                kwargs.get("settlement_days", 2),
                kwargs.get("paired_instrument_id"),
                instrument_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO instrument_rate (
                instrument_id, rate_type, currency, tenor,
                reference_rate, day_count, payment_frequency,
                business_day_conv, calendar, settlement_days,
                paired_instrument_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                instrument_id,
                kwargs.get("rate_type", "OIS"),
                kwargs.get("currency", ""),
                kwargs.get("tenor", ""),
                kwargs.get("reference_rate"),
                kwargs.get("day_count"),
                kwargs.get("payment_frequency"),
                kwargs.get("business_day_conv"),
                kwargs.get("calendar"),
                kwargs.get("settlement_days", 2),
                kwargs.get("paired_instrument_id"),
            ],
        )


def _save_bond_details(
    conn: duckdb.DuckDBPyConnection, instrument_id: int, **kwargs
) -> None:
    """Save bond instrument details (govt/corp yields)."""
    result = conn.execute(
        "SELECT 1 FROM instrument_bond WHERE instrument_id = ?", [instrument_id]
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE instrument_bond SET
                issuer_type = ?,
                country = ?,
                tenor = ?,
                coupon_rate = ?,
                coupon_frequency = ?,
                day_count = ?,
                maturity_date = ?,
                settlement_days = ?,
                credit_rating = ?,
                sector = ?
            WHERE instrument_id = ?
            """,
            [
                kwargs.get("issuer_type", "GOVT"),
                kwargs.get("country"),
                kwargs.get("tenor", ""),
                kwargs.get("coupon_rate"),
                kwargs.get("coupon_frequency"),
                kwargs.get("day_count"),
                kwargs.get("maturity_date"),
                kwargs.get("settlement_days", 1),
                kwargs.get("credit_rating"),
                kwargs.get("sector"),
                instrument_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO instrument_bond (
                instrument_id, issuer_type, country, tenor,
                coupon_rate, coupon_frequency, day_count,
                maturity_date, settlement_days, credit_rating, sector
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                instrument_id,
                kwargs.get("issuer_type", "GOVT"),
                kwargs.get("country"),
                kwargs.get("tenor", ""),
                kwargs.get("coupon_rate"),
                kwargs.get("coupon_frequency"),
                kwargs.get("day_count"),
                kwargs.get("maturity_date"),
                kwargs.get("settlement_days", 1),
                kwargs.get("credit_rating"),
                kwargs.get("sector"),
            ],
        )


def _save_fixing_details(
    conn: duckdb.DuckDBPyConnection, instrument_id: int, **kwargs
) -> None:
    """Save fixing instrument details (SOFR, ESTR, SONIA)."""
    result = conn.execute(
        "SELECT 1 FROM instrument_fixing WHERE instrument_id = ?", [instrument_id]
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE instrument_fixing SET
                rate_name = ?,
                tenor = ?,
                fixing_time = ?,
                administrator = ?
            WHERE instrument_id = ?
            """,
            [
                kwargs.get("rate_name", ""),
                kwargs.get("tenor"),
                kwargs.get("fixing_time"),
                kwargs.get("administrator"),
                instrument_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO instrument_fixing (
                instrument_id, rate_name, tenor, fixing_time, administrator
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                instrument_id,
                kwargs.get("rate_name", ""),
                kwargs.get("tenor"),
                kwargs.get("fixing_time"),
                kwargs.get("administrator"),
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
    data_shape: DataShape | None = None,
) -> int:
    """
    Save time series data to database.

    Routes data to the correct timeseries table based on data_shape:
    - OHLCV: timeseries_ohlcv (futures, equities, commodities)
    - QUOTE: timeseries_quote (FX spot, FX forwards)
    - RATE: timeseries_rate (OIS, IRS, FRA, repo)
    - BOND: timeseries_bond (govt yields, corp bonds)
    - FIXING: timeseries_fixing (SOFR, ESTR, SONIA)

    Args:
        conn: Database connection.
        instrument_id: Instrument ID.
        data: DataFrame with DatetimeIndex and appropriate columns.
        granularity: Data granularity.
        source_contract: Source contract for continuous series (OHLCV only).
        adjustment_factor: Adjustment factor for continuous series (OHLCV only).
        data_shape: Data shape for routing (auto-detected from instrument if None).

    Returns:
        Number of rows saved.

    Raises:
        StorageError: If save fails.
    """
    if data.empty:
        return 0

    try:
        # Auto-detect data_shape from instrument if not provided
        if data_shape is None:
            result = conn.execute(
                "SELECT data_shape FROM instruments WHERE id = ?", [instrument_id]
            ).fetchone()
            if result:
                data_shape = DataShape(result[0])
            else:
                data_shape = DataShape.OHLCV  # Default fallback

        # Route to appropriate save function based on data_shape
        if data_shape == DataShape.OHLCV:
            rows_saved = _save_ohlcv_data(
                conn,
                instrument_id,
                data,
                granularity,
                source_contract,
                adjustment_factor,
            )
        elif data_shape == DataShape.QUOTE:
            rows_saved = _save_quote_data(conn, instrument_id, data, granularity)
        elif data_shape == DataShape.RATE:
            rows_saved = _save_rate_data(conn, instrument_id, data, granularity)
        elif data_shape == DataShape.BOND:
            rows_saved = _save_bond_data(conn, instrument_id, data, granularity)
        elif data_shape == DataShape.FIXING:
            rows_saved = _save_fixing_data(conn, instrument_id, data)
        else:
            # Fallback to OHLCV for unknown shapes
            rows_saved = _save_ohlcv_data(
                conn,
                instrument_id,
                data,
                granularity,
                source_contract,
                adjustment_factor,
            )

        return rows_saved
    except duckdb.Error as e:
        raise StorageError(f"Failed to save time series: {e}") from e


def _convert_index_to_timestamp(idx) -> datetime:
    """Convert DataFrame index to timestamp."""
    if hasattr(idx, "to_pydatetime"):
        return idx.to_pydatetime()
    elif isinstance(idx, datetime):
        return idx
    elif isinstance(idx, date):
        return datetime.combine(idx, datetime.min.time())
    else:
        return datetime.fromisoformat(str(idx))


def _save_ohlcv_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
    source_contract: str | None,
    adjustment_factor: float,
) -> int:
    """Save OHLCV data (futures, equities, commodities) to timeseries_ohlcv."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Determine close price with fallbacks
        close_price = row.get("close")
        if close_price is None or pd.isna(close_price):
            close_price = row.get("settle")
        if close_price is None or pd.isna(close_price):
            close_price = row.get("TRDPRC_1")  # LSEG field name

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "open": row.get("open") or row.get("OPEN_PRC"),
                "high": row.get("high") or row.get("HIGH_1"),
                "low": row.get("low") or row.get("LOW_1"),
                "close": close_price,
                "volume": row.get("volume") or row.get("ACVOL_UNS"),
                "settle": row.get("settle") or row.get("SETTLE"),
                "open_interest": row.get("open_interest") or row.get("OPINT_1"),
                "vwap": row.get("vwap") or row.get("VWAP"),
                "source_contract": source_contract,
                "adjustment_factor": adjustment_factor,
            }
        )

    for record in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO timeseries_ohlcv (
                instrument_id, ts, granularity, open, high, low, close,
                volume, settle, open_interest, vwap, source_contract, adjustment_factor
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["instrument_id"],
                record["ts"],
                record["granularity"],
                record["open"],
                record["high"],
                record["low"],
                record["close"],
                record["volume"],
                record["settle"],
                record["open_interest"],
                record["vwap"],
                record["source_contract"],
                record["adjustment_factor"],
            ],
        )

    return len(rows)


def _save_quote_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save quote data (FX spot, FX forwards) to timeseries_quote."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Get bid/ask/mid with LSEG field fallbacks
        bid = row.get("bid") or row.get("BID")
        ask = row.get("ask") or row.get("ASK")
        mid = row.get("mid") or row.get("MID_PRICE")

        # Calculate mid if not provided
        if (mid is None or pd.isna(mid)) and bid is not None and ask is not None:
            if not pd.isna(bid) and not pd.isna(ask):
                mid = (float(bid) + float(ask)) / 2

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "open_bid": row.get("open_bid") or row.get("OPEN_BID"),
                "bid_high": row.get("bid_high") or row.get("BID_HIGH_1"),
                "bid_low": row.get("bid_low") or row.get("BID_LOW_1"),
                "open_ask": row.get("open_ask") or row.get("OPEN_ASK"),
                "ask_high": row.get("ask_high") or row.get("ASK_HIGH_1"),
                "ask_low": row.get("ask_low") or row.get("ASK_LOW_1"),
                "forward_points": row.get("forward_points") or row.get("FWD_POINTS"),
            }
        )

    for record in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO timeseries_quote (
                instrument_id, ts, granularity, bid, ask, mid,
                open_bid, bid_high, bid_low, open_ask, ask_high, ask_low, forward_points
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["instrument_id"],
                record["ts"],
                record["granularity"],
                record["bid"],
                record["ask"],
                record["mid"],
                record["open_bid"],
                record["bid_high"],
                record["bid_low"],
                record["open_ask"],
                record["ask_high"],
                record["ask_low"],
                record["forward_points"],
            ],
        )

    return len(rows)


def _save_rate_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save rate data (OIS, IRS, FRA, repo) to timeseries_rate."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Get rate with various field fallbacks
        rate = row.get("rate") or row.get("mid") or row.get("MID_PRICE")
        if rate is None or pd.isna(rate):
            bid = row.get("bid") or row.get("BID")
            ask = row.get("ask") or row.get("ASK")
            if (
                bid is not None
                and ask is not None
                and not pd.isna(bid)
                and not pd.isna(ask)
            ):
                rate = (float(bid) + float(ask)) / 2

        # Calculate open_rate from OPEN_BID/OPEN_ASK
        open_bid = row.get("open_bid") or row.get("OPEN_BID")
        open_ask = row.get("open_ask") or row.get("OPEN_ASK")
        open_rate = row.get("open_rate")
        if open_rate is None or pd.isna(open_rate):
            if (
                open_bid is not None
                and open_ask is not None
                and not pd.isna(open_bid)
                and not pd.isna(open_ask)
            ):
                open_rate = (float(open_bid) + float(open_ask)) / 2

        # Calculate high/low rate from BID_HIGH/BID_LOW (rates typically quoted on bid side)
        high_rate = row.get("high_rate") or row.get("BID_HIGH_1")
        low_rate = row.get("low_rate") or row.get("BID_LOW_1")

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "rate": rate,
                "bid": row.get("bid") or row.get("BID"),
                "ask": row.get("ask") or row.get("ASK"),
                "open_rate": open_rate,
                "high_rate": high_rate,
                "low_rate": low_rate,
                "rate_2": row.get(
                    "rate_2"
                ),  # Secondary rate (reverse repo, floating leg)
                "spread": row.get("spread"),
                "reference_rate": row.get("reference_rate"),
                "side": row.get("side"),
            }
        )

    for record in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO timeseries_rate (
                instrument_id, ts, granularity, rate, bid, ask,
                open_rate, high_rate, low_rate,
                rate_2, spread, reference_rate, side
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["instrument_id"],
                record["ts"],
                record["granularity"],
                record["rate"],
                record["bid"],
                record["ask"],
                record["open_rate"],
                record["high_rate"],
                record["low_rate"],
                record["rate_2"],
                record["spread"],
                record["reference_rate"],
                record["side"],
            ],
        )

    return len(rows)


def _save_bond_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save bond data (govt yields, corp bonds) to timeseries_bond."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Get yield with various field fallbacks
        yld = row.get("yield") or row.get("MID_YLD_1") or row.get("B_YLD_1")
        if yld is None or pd.isna(yld):
            yld_bid = row.get("yield_bid") or row.get("B_YLD_1")
            yld_ask = row.get("yield_ask") or row.get("A_YLD_1")
            if (
                yld_bid is not None
                and yld_ask is not None
                and not pd.isna(yld_bid)
                and not pd.isna(yld_ask)
            ):
                yld = (float(yld_bid) + float(yld_ask)) / 2

        # Get clean price and accrued interest
        clean_price = row.get("price") or row.get("MID_PRICE") or row.get("CLEAN_PRC")
        accrued = row.get("accrued_interest") or row.get("ACCR_INT")
        dirty = row.get("dirty_price") or row.get("DIRTY_PRC")

        # Calculate dirty price if we have clean + accrued but no dirty
        if dirty is None and clean_price is not None and accrued is not None:
            if not pd.isna(clean_price) and not pd.isna(accrued):
                dirty = float(clean_price) + float(accrued)

        # Get opening price/yield
        open_price = row.get("open_price") or row.get("MID_OPEN")
        open_yield = row.get("open_yield") or row.get("OPEN_YLD")

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "price": clean_price,
                "dirty_price": dirty,
                "accrued_interest": accrued,
                "bid": row.get("bid") or row.get("BID"),
                "ask": row.get("ask") or row.get("ASK"),
                "open_price": open_price,
                "open_yield": open_yield,
                "yield": yld,
                "yield_bid": row.get("yield_bid") or row.get("B_YLD_1"),
                "yield_ask": row.get("yield_ask") or row.get("A_YLD_1"),
                "yield_high": row.get("yield_high") or row.get("HIGH_YLD"),
                "yield_low": row.get("yield_low") or row.get("LOW_YLD"),
                "mac_duration": row.get("mac_duration") or row.get("MAC_DURTN"),
                "mod_duration": row.get("mod_duration") or row.get("MOD_DURTN"),
                "convexity": row.get("convexity") or row.get("CONVEXITY"),
                "dv01": row.get("dv01") or row.get("BPV"),
                "z_spread": row.get("z_spread") or row.get("ZSPREAD"),
                "oas": row.get("oas") or row.get("OAS_BID"),
            }
        )

    for record in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO timeseries_bond (
                instrument_id, ts, granularity, price, dirty_price, accrued_interest,
                bid, ask, open_price, open_yield,
                yield, yield_bid, yield_ask, yield_high, yield_low,
                mac_duration, mod_duration, convexity, dv01,
                z_spread, oas
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["instrument_id"],
                record["ts"],
                record["granularity"],
                record["price"],
                record["dirty_price"],
                record["accrued_interest"],
                record["bid"],
                record["ask"],
                record["open_price"],
                record["open_yield"],
                record["yield"],
                record["yield_bid"],
                record["yield_ask"],
                record["yield_high"],
                record["yield_low"],
                record["mac_duration"],
                record["mod_duration"],
                record["convexity"],
                record["dv01"],
                record["z_spread"],
                record["oas"],
            ],
        )

    return len(rows)


def _save_fixing_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
) -> int:
    """Save fixing data (SOFR, ESTR, SONIA) to timeseries_fixing.

    Note: Fixings are daily only, no granularity parameter.
    """
    rows = []
    for idx, row in data.iterrows():
        # Convert index to date
        if hasattr(idx, "date"):
            dt = idx.date()
        elif isinstance(idx, date):
            dt = idx
        else:
            dt = date.fromisoformat(str(idx)[:10])

        # Get fixing value with field fallbacks
        value = row.get("value") or row.get("FIXING_1") or row.get("PRIMACT_1")
        if value is None or pd.isna(value):
            # Try mid price as fallback
            value = row.get("mid") or row.get("MID_PRICE")

        rows.append(
            {
                "instrument_id": instrument_id,
                "date": dt,
                "value": value,
                "volume": row.get("volume") or row.get("ACVOL_UNS"),
            }
        )

    for record in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO timeseries_fixing (
                instrument_id, date, value, volume
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                record["instrument_id"],
                record["date"],
                record["value"],
                record["volume"],
            ],
        )

    return len(rows)


# Legacy save functions (for backwards compatibility during migration)
def _save_daily_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    source_contract: str | None,
    adjustment_factor: float,
) -> int:
    """Save daily OHLCV data to legacy ohlcv_daily table."""
    rows = []
    for idx, row in data.iterrows():
        if hasattr(idx, "date"):
            dt: date = idx.date()
        else:
            dt = date.fromisoformat(str(idx)) if not isinstance(idx, date) else idx

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

    for record in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO ohlcv_daily (
                instrument_id, date, open, high, low, close,
                volume, open_interest, settle, adjustment_factor, source_contract
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["instrument_id"],
                record["date"],
                record["open"],
                record["high"],
                record["low"],
                record["close"],
                record["volume"],
                record["open_interest"],
                record["settle"],
                record["adjustment_factor"],
                record["source_contract"],
            ],
        )

    return len(rows)


def _save_intraday_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save intraday OHLCV data to legacy ohlcv_intraday table."""
    rows: list[dict] = []
    for idx, df_row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

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

    for record in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO ohlcv_intraday (
                instrument_id, timestamp, granularity, open, high, low, close, volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["instrument_id"],
                record["timestamp"],
                record["granularity"],
                record["open"],
                record["high"],
                record["low"],
                record["close"],
                record["volume"],
            ],
        )

    return len(rows)


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


# Legacy load functions (for backwards compatibility during migration)
def _load_daily_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """Load daily OHLCV data from legacy ohlcv_daily table."""
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
    """Load intraday OHLCV data from legacy ohlcv_intraday table."""
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
    data_shape: DataShape | None = None,
    granularity: Granularity = Granularity.DAILY,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    """
    Export data to Parquet using DuckDB's native COPY.

    Supports all data shapes and routes to the correct timeseries table.

    Args:
        conn: Database connection.
        output_path: Output file path (should end with .parquet).
        symbol: Filter by instrument symbol.
        asset_class: Filter by asset class.
        data_shape: Filter by data shape (infers table to export from).
        granularity: Data granularity (default: daily).
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

        # Determine which table to export from
        if data_shape is None:
            data_shape = DataShape.OHLCV  # Default to OHLCV

        # Build query based on data_shape
        if data_shape == DataShape.OHLCV:
            query = """
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.open,
                    t.high,
                    t.low,
                    t.close,
                    t.volume,
                    t.settle,
                    t.open_interest,
                    t.vwap,
                    t.source_contract,
                    t.adjustment_factor
                FROM timeseries_ohlcv t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.QUOTE:
            query = """
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.bid,
                    t.ask,
                    t.mid,
                    t.open_bid,
                    t.bid_high,
                    t.bid_low,
                    t.open_ask,
                    t.ask_high,
                    t.ask_low,
                    t.forward_points
                FROM timeseries_quote t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.RATE:
            query = """
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.rate,
                    t.bid,
                    t.ask,
                    t.open_rate,
                    t.high_rate,
                    t.low_rate,
                    t.rate_2,
                    t.spread,
                    t.reference_rate,
                    t.side
                FROM timeseries_rate t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.BOND:
            query = """
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.price,
                    t.dirty_price,
                    t.accrued_interest,
                    t.bid,
                    t.ask,
                    t.open_price,
                    t.open_yield,
                    t.yield,
                    t.yield_bid,
                    t.yield_ask,
                    t.yield_high,
                    t.yield_low,
                    t.mac_duration,
                    t.mod_duration,
                    t.convexity,
                    t.dv01,
                    t.z_spread,
                    t.oas
                FROM timeseries_bond t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.FIXING:
            query = """
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.date,
                    t.value,
                    t.volume
                FROM timeseries_fixing t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE 1=1
            """
        else:
            raise StorageError(f"Unknown data shape: {data_shape}")

        # Add filters
        conditions = []

        if symbol:
            conditions.append(f"AND i.symbol = '{symbol}'")
        if asset_class:
            conditions.append(f"AND i.asset_class = '{asset_class.value}'")
        if start_date:
            if data_shape == DataShape.FIXING:
                conditions.append(f"AND t.date >= '{start_date.isoformat()}'")
            else:
                conditions.append(f"AND t.ts >= '{start_date.isoformat()}'")
        if end_date:
            if data_shape == DataShape.FIXING:
                conditions.append(f"AND t.date <= '{end_date.isoformat()}'")
            else:
                conditions.append(f"AND t.ts <= '{end_date.isoformat()}'")

        query += " " + " ".join(conditions)
        if data_shape == DataShape.FIXING:
            query += " ORDER BY i.symbol, t.date"
        else:
            query += " ORDER BY i.symbol, t.ts"

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
    granularity: Granularity = Granularity.DAILY,
    partition_by_year: bool = True,
) -> list[str]:
    """
    Export a single symbol to Parquet, optionally partitioned by year.

    Routes to the correct timeseries table based on the instrument's data_shape.

    Args:
        conn: Database connection.
        symbol: Instrument symbol to export.
        output_dir: Output directory.
        granularity: Data granularity (default: daily).
        partition_by_year: Whether to partition by year.

    Returns:
        List of exported file paths.

    Raises:
        StorageError: If export fails.
    """
    try:
        # Get instrument info including data_shape
        result = conn.execute(
            "SELECT id, data_shape FROM instruments WHERE symbol = ?", [symbol]
        ).fetchone()
        if result is None:
            raise StorageError(f"Instrument not found: {symbol}")

        instrument_id, instr_data_shape = result
        data_shape = (
            DataShape(instr_data_shape) if instr_data_shape else DataShape.OHLCV
        )

        output_path = Path(output_dir) / symbol
        output_path.mkdir(parents=True, exist_ok=True)

        exported_files = []

        # Build the SELECT clause based on data_shape
        if data_shape == DataShape.OHLCV:
            select_cols = "ts as timestamp, open, high, low, close, volume, settle, open_interest, vwap"
            table_name = "timeseries_ohlcv"
            time_col = "ts"
        elif data_shape == DataShape.QUOTE:
            select_cols = "ts as timestamp, bid, ask, mid, open_bid, bid_high, bid_low, forward_points"
            table_name = "timeseries_quote"
            time_col = "ts"
        elif data_shape == DataShape.RATE:
            select_cols = (
                "ts as timestamp, rate, bid, ask, open_rate, high_rate, low_rate, "
                "rate_2, spread, reference_rate, side"
            )
            table_name = "timeseries_rate"
            time_col = "ts"
        elif data_shape == DataShape.BOND:
            select_cols = (
                "ts as timestamp, price, dirty_price, accrued_interest, bid, ask, "
                "open_price, open_yield, yield, yield_bid, yield_ask, yield_high, yield_low, "
                "mac_duration, mod_duration, convexity, dv01"
            )
            table_name = "timeseries_bond"
            time_col = "ts"
        elif data_shape == DataShape.FIXING:
            select_cols = "date, value, volume"
            table_name = "timeseries_fixing"
            time_col = "date"
        else:
            raise StorageError(f"Unknown data shape: {data_shape}")

        if partition_by_year:
            # Get distinct years
            if data_shape == DataShape.FIXING:
                year_query = f"""
                    SELECT DISTINCT EXTRACT(YEAR FROM {time_col}) as year
                    FROM {table_name}
                    WHERE instrument_id = ?
                    ORDER BY year
                """
            else:
                year_query = f"""
                    SELECT DISTINCT EXTRACT(YEAR FROM {time_col}) as year
                    FROM {table_name}
                    WHERE instrument_id = ? AND granularity = ?
                    ORDER BY year
                """
            params = (
                [instrument_id]
                if data_shape == DataShape.FIXING
                else [instrument_id, granularity.value]
            )
            years = conn.execute(year_query, params).fetchall()

            for (year,) in years:
                file_path = str(output_path / f"{int(year)}.parquet")
                if data_shape == DataShape.FIXING:
                    query = f"""
                        SELECT {select_cols}
                        FROM {table_name}
                        WHERE instrument_id = {instrument_id}
                        AND EXTRACT(YEAR FROM {time_col}) = {int(year)}
                        ORDER BY {time_col}
                    """
                else:
                    query = f"""
                        SELECT {select_cols}
                        FROM {table_name}
                        WHERE instrument_id = {instrument_id}
                        AND granularity = '{granularity.value}'
                        AND EXTRACT(YEAR FROM {time_col}) = {int(year)}
                        ORDER BY {time_col}
                    """
                conn.execute(
                    f"COPY ({query}) TO '{file_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
                )
                exported_files.append(file_path)
        else:
            file_path = str(output_path / f"{symbol}.parquet")
            if data_shape == DataShape.FIXING:
                query = f"""
                    SELECT {select_cols}
                    FROM {table_name}
                    WHERE instrument_id = {instrument_id}
                    ORDER BY {time_col}
                """
            else:
                query = f"""
                    SELECT {select_cols}
                    FROM {table_name}
                    WHERE instrument_id = {instrument_id}
                    AND granularity = '{granularity.value}'
                    ORDER BY {time_col}
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
