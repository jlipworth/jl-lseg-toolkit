"""
DuckDB schema definitions and initialization.

This module contains the SQL schema for all tables and the init_db function.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from lseg_toolkit.exceptions import StorageError

from .connection import DEFAULT_DUCKDB_PATH

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

-- Equity instrument details (stocks)
CREATE TABLE IF NOT EXISTS instrument_equity (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    exchange VARCHAR,  -- 'NYSE', 'NASDAQ', 'LSE', 'XETRA', 'TSE'
    country VARCHAR NOT NULL,  -- 'US', 'GB', 'DE', 'JP'
    currency VARCHAR NOT NULL,  -- 'USD', 'GBP', 'EUR', 'JPY'
    sector VARCHAR,  -- 'Technology', 'Healthcare', 'Financials'
    industry VARCHAR,  -- 'Software', 'Semiconductors', 'Banks'
    isin VARCHAR,  -- International Securities Identification Number
    cusip VARCHAR,  -- US/Canada identifier
    sedol VARCHAR,  -- UK identifier
    market_cap_category VARCHAR  -- 'large', 'mid', 'small', 'micro'
);

-- ETF instrument details
CREATE TABLE IF NOT EXISTS instrument_etf (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    exchange VARCHAR,  -- 'NYSE', 'NASDAQ', 'LSE'
    country VARCHAR NOT NULL,  -- 'US', 'IE', 'LU'
    currency VARCHAR NOT NULL,
    asset_class_focus VARCHAR,  -- 'equity', 'fixed_income', 'commodity', 'multi_asset'
    geography_focus VARCHAR,  -- 'US', 'Europe', 'EM', 'Global'
    benchmark_index VARCHAR,  -- 'S&P 500', 'MSCI World'
    expense_ratio DOUBLE,
    isin VARCHAR,
    cusip VARCHAR,
    is_leveraged BOOLEAN DEFAULT FALSE,
    is_inverse BOOLEAN DEFAULT FALSE
);

-- Index instrument details (spot indices like .SPX, .DJI)
CREATE TABLE IF NOT EXISTS instrument_index (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    index_family VARCHAR,  -- 'S&P', 'MSCI', 'FTSE', 'Stoxx'
    country VARCHAR,  -- 'US', 'GB', 'DE', 'JP', 'Global'
    calculation_method VARCHAR,  -- 'price_weighted', 'market_cap_weighted', 'equal_weighted'
    currency VARCHAR NOT NULL,
    num_constituents INTEGER,
    base_date DATE,
    base_value DOUBLE
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
