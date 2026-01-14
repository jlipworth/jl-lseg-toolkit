"""
PostgreSQL/TimescaleDB schema definitions and initialization.

This module contains the SQL schema translated from DuckDB to PostgreSQL,
including TimescaleDB hypertable configuration and compression policies.
"""

from __future__ import annotations

import psycopg

from lseg_toolkit.exceptions import StorageError

# =============================================================================
# PostgreSQL Schema (translated from DuckDB)
# =============================================================================

SCHEMA_SQL = """
-- =============================================================================
-- Extensions
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =============================================================================
-- Instruments master table
-- =============================================================================
CREATE TABLE IF NOT EXISTS instruments (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    data_shape TEXT NOT NULL,  -- 'ohlcv', 'quote', 'rate', 'bond', 'fixing'
    lseg_ric TEXT NOT NULL,
    exchange TEXT,
    currency TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
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
    underlying TEXT NOT NULL,
    exchange TEXT,
    expiry_date DATE,
    contract_month TEXT,  -- 'H5', 'M5'
    continuous_type TEXT DEFAULT 'discrete',
    tick_size DOUBLE PRECISION,
    point_value DOUBLE PRECISION
);

-- FX spot details
CREATE TABLE IF NOT EXISTS instrument_fx (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    pip_size DOUBLE PRECISION DEFAULT 0.0001,
    tenor TEXT  -- NULL for spot, '1W', '1M' for forwards
);

-- Rate instrument details (OIS, IRS, FRA, Repo)
CREATE TABLE IF NOT EXISTS instrument_rate (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    rate_type TEXT NOT NULL,  -- 'OIS', 'IRS', 'FRA', 'REPO', 'DEPOSIT'
    currency TEXT NOT NULL,
    tenor TEXT NOT NULL,
    reference_rate TEXT,  -- 'SOFR', 'EURIBOR', 'SONIA'
    day_count TEXT,  -- 'ACT/360', 'ACT/365', 'ACT/ACT'
    payment_frequency TEXT,  -- 'annual', 'semiannual', 'quarterly', 'monthly'
    business_day_conv TEXT,  -- 'modified_following', 'following', 'preceding'
    calendar TEXT,  -- 'TARGET', 'US', 'UK', 'JP'
    settlement_days INTEGER DEFAULT 2,  -- T+2 for most swaps
    paired_instrument_id INTEGER REFERENCES instruments(id)
);

-- Bond instrument details (govt/corp yields)
CREATE TABLE IF NOT EXISTS instrument_bond (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    issuer_type TEXT NOT NULL,  -- 'GOVT', 'CORP', 'MUNI', 'AGENCY'
    country TEXT,
    tenor TEXT NOT NULL,
    coupon_rate DOUBLE PRECISION,
    coupon_frequency TEXT,  -- 'semiannual' (UST), 'annual' (Bunds), 'quarterly'
    day_count TEXT,  -- 'ACT/ACT', '30/360', 'ACT/365'
    maturity_date DATE,
    settlement_days INTEGER DEFAULT 1,  -- T+1 for UST, T+2 for most others
    credit_rating TEXT,
    sector TEXT
);

-- Fixing instrument details (SOFR, ESTR, SONIA)
CREATE TABLE IF NOT EXISTS instrument_fixing (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    rate_name TEXT NOT NULL,  -- 'SOFR', 'ESTR', 'SONIA', 'EURIBOR'
    tenor TEXT,  -- NULL for overnight, '3M' for EURIBOR3M
    fixing_time TEXT,  -- '08:00 NY', '11:00 London'
    administrator TEXT  -- 'Fed', 'ECB', 'BoE'
);

-- Equity instrument details (stocks)
CREATE TABLE IF NOT EXISTS instrument_equity (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    exchange TEXT,
    country TEXT NOT NULL,
    currency TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    isin TEXT,
    cusip TEXT,
    sedol TEXT,
    market_cap_category TEXT
);

-- ETF instrument details
CREATE TABLE IF NOT EXISTS instrument_etf (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    exchange TEXT,
    country TEXT NOT NULL,
    currency TEXT NOT NULL,
    asset_class_focus TEXT,
    geography_focus TEXT,
    benchmark_index TEXT,
    expense_ratio DOUBLE PRECISION,
    isin TEXT,
    cusip TEXT,
    is_leveraged BOOLEAN DEFAULT FALSE,
    is_inverse BOOLEAN DEFAULT FALSE
);

-- Index instrument details (spot indices like .SPX, .DJI)
CREATE TABLE IF NOT EXISTS instrument_index (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    index_family TEXT,
    country TEXT,
    calculation_method TEXT,
    currency TEXT NOT NULL,
    num_constituents INTEGER,
    base_date DATE,
    base_value DOUBLE PRECISION
);

-- Commodity spot details (precious metals, energy spot)
CREATE TABLE IF NOT EXISTS instrument_commodity (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    commodity_type TEXT NOT NULL,
    unit TEXT,
    currency TEXT NOT NULL,
    quote_convention TEXT
);

-- CDS instrument details (credit default swaps)
CREATE TABLE IF NOT EXISTS instrument_cds (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    index_family TEXT,
    series INTEGER,
    tenor TEXT NOT NULL,
    currency TEXT NOT NULL,
    restructuring_type TEXT,
    reference_entity TEXT
);

-- Option instrument details
CREATE TABLE IF NOT EXISTS instrument_option (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying_symbol TEXT NOT NULL,
    underlying_id INTEGER REFERENCES instruments(id),
    option_type TEXT NOT NULL,
    strike DOUBLE PRECISION NOT NULL,
    expiry_date DATE NOT NULL,
    exercise_style TEXT NOT NULL,
    contract_size INTEGER DEFAULT 100,
    exchange TEXT,
    root_symbol TEXT
);

-- =============================================================================
-- Timeseries Tables (by data shape)
-- NOTE: These must be created BEFORE hypertable conversion
-- =============================================================================

-- OHLCV data (futures, equities, commodities, indices)
CREATE TABLE IF NOT EXISTS timeseries_ohlcv (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMPTZ NOT NULL,
    granularity TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION,
    settle DOUBLE PRECISION,
    open_interest DOUBLE PRECISION,
    vwap DOUBLE PRECISION,
    source_contract TEXT,
    adjustment_factor DOUBLE PRECISION DEFAULT 1.0,
    PRIMARY KEY (instrument_id, ts, granularity)
);

-- Quote data (FX spot, FX forwards)
CREATE TABLE IF NOT EXISTS timeseries_quote (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMPTZ NOT NULL,
    granularity TEXT NOT NULL,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    mid DOUBLE PRECISION,
    open_bid DOUBLE PRECISION,
    bid_high DOUBLE PRECISION,
    bid_low DOUBLE PRECISION,
    open_ask DOUBLE PRECISION,
    ask_high DOUBLE PRECISION,
    ask_low DOUBLE PRECISION,
    forward_points DOUBLE PRECISION,
    PRIMARY KEY (instrument_id, ts, granularity)
);

-- Rate data (OIS, IRS, FRA, Repo, CDS)
CREATE TABLE IF NOT EXISTS timeseries_rate (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMPTZ NOT NULL,
    granularity TEXT NOT NULL,
    rate DOUBLE PRECISION NOT NULL,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    open_rate DOUBLE PRECISION,
    high_rate DOUBLE PRECISION,
    low_rate DOUBLE PRECISION,
    rate_2 DOUBLE PRECISION,
    spread DOUBLE PRECISION,
    reference_rate TEXT,
    side TEXT,
    PRIMARY KEY (instrument_id, ts, granularity)
);

-- Bond data (govt yields, corp bonds)
CREATE TABLE IF NOT EXISTS timeseries_bond (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ts TIMESTAMPTZ NOT NULL,
    granularity TEXT NOT NULL,
    price DOUBLE PRECISION,
    dirty_price DOUBLE PRECISION,
    accrued_interest DOUBLE PRECISION,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    open_price DOUBLE PRECISION,
    open_yield DOUBLE PRECISION,
    yield DOUBLE PRECISION NOT NULL,
    yield_bid DOUBLE PRECISION,
    yield_ask DOUBLE PRECISION,
    yield_high DOUBLE PRECISION,
    yield_low DOUBLE PRECISION,
    mac_duration DOUBLE PRECISION,
    mod_duration DOUBLE PRECISION,
    convexity DOUBLE PRECISION,
    dv01 DOUBLE PRECISION,
    z_spread DOUBLE PRECISION,
    oas DOUBLE PRECISION,
    PRIMARY KEY (instrument_id, ts, granularity)
);

-- Fixing data (SOFR, ESTR, SONIA, EURIBOR)
CREATE TABLE IF NOT EXISTS timeseries_fixing (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION,
    PRIMARY KEY (instrument_id, date)
);

-- =============================================================================
-- Metadata Tables
-- =============================================================================

-- Roll events for continuous contracts
CREATE TABLE IF NOT EXISTS roll_events (
    id SERIAL PRIMARY KEY,
    continuous_id INTEGER NOT NULL REFERENCES instruments(id),
    roll_date DATE NOT NULL,
    from_contract TEXT NOT NULL,
    to_contract TEXT NOT NULL,
    from_price DOUBLE PRECISION NOT NULL,
    to_price DOUBLE PRECISION NOT NULL,
    price_gap DOUBLE PRECISION NOT NULL,
    adjustment_factor DOUBLE PRECISION NOT NULL,
    roll_method TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_roll_events_continuous ON roll_events(continuous_id, roll_date DESC);

-- Data extraction metadata
CREATE TABLE IF NOT EXISTS extraction_log (
    id SERIAL PRIMARY KEY,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    granularity TEXT NOT NULL,
    rows_fetched INTEGER NOT NULL,
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extraction progress tracking (for batch extraction)
CREATE TABLE IF NOT EXISTS extraction_progress (
    id SERIAL PRIMARY KEY,
    asset_class TEXT NOT NULL,
    instrument TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'pending',
    rows_fetched INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_progress ON extraction_progress(asset_class, instrument, status);

-- =============================================================================
-- Bond Basis Tables
-- =============================================================================

-- Futures contract reference (for discrete contracts, not continuous)
CREATE TABLE IF NOT EXISTS futures_contracts (
    id SERIAL PRIMARY KEY,
    futures_root TEXT NOT NULL,           -- 'TY', 'FV', 'TU', 'US', 'TN', 'UB'
    contract_month TEXT NOT NULL,         -- 'H26', 'M26', 'U26', 'Z26'
    expiry_date DATE NOT NULL,
    first_notice_date DATE,
    first_delivery_date DATE,
    last_delivery_date DATE,
    lseg_ric TEXT NOT NULL UNIQUE,        -- 'TYH26', 'TYH5^2' (for expired)
    cme_symbol TEXT,                      -- 'ZNH26'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (futures_root, contract_month)
);
CREATE INDEX IF NOT EXISTS idx_futures_contracts_root ON futures_contracts(futures_root);
CREATE INDEX IF NOT EXISTS idx_futures_contracts_expiry ON futures_contracts(expiry_date);

-- Bonds deliverable into futures contracts
CREATE TABLE IF NOT EXISTS deliverable_bonds (
    id SERIAL PRIMARY KEY,
    bond_instrument_id INTEGER REFERENCES instruments(id),
    futures_contract_id INTEGER NOT NULL REFERENCES futures_contracts(id),
    cusip TEXT NOT NULL,
    isin TEXT,
    coupon_rate DOUBLE PRECISION NOT NULL,
    maturity_date DATE NOT NULL,
    issue_date DATE,
    lseg_ric TEXT,                        -- '91282CFV8='
    is_ctd BOOLEAN DEFAULT FALSE,         -- CTD at contract expiry
    ctd_rank INTEGER,                     -- 1=CTD, 2=2nd cheapest, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (futures_contract_id, cusip)
);
CREATE INDEX IF NOT EXISTS idx_deliverable_bonds_contract ON deliverable_bonds(futures_contract_id);
CREATE INDEX IF NOT EXISTS idx_deliverable_bonds_cusip ON deliverable_bonds(cusip);
CREATE INDEX IF NOT EXISTS idx_deliverable_bonds_ctd ON deliverable_bonds(is_ctd) WHERE is_ctd = TRUE;

-- CME conversion factors (one per bond per contract)
CREATE TABLE IF NOT EXISTS conversion_factors (
    id SERIAL PRIMARY KEY,
    futures_contract_id INTEGER NOT NULL REFERENCES futures_contracts(id),
    bond_cusip TEXT NOT NULL,
    conversion_factor DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,                 -- 'cme_lookup', 'cme_calculator', 'calculated'
    effective_date DATE,                  -- When CF was published
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (futures_contract_id, bond_cusip)
);
CREATE INDEX IF NOT EXISTS idx_conversion_factors_contract ON conversion_factors(futures_contract_id);

-- Historical bond basis timeseries
CREATE TABLE IF NOT EXISTS timeseries_basis (
    futures_contract_id INTEGER NOT NULL REFERENCES futures_contracts(id),
    bond_cusip TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    -- Prices
    bond_price DOUBLE PRECISION NOT NULL,         -- Clean price (ASK)
    bond_bid DOUBLE PRECISION,
    bond_yield DOUBLE PRECISION,
    futures_price DOUBLE PRECISION NOT NULL,      -- Settle or BID
    -- Basis components
    conversion_factor DOUBLE PRECISION NOT NULL,
    invoice_price DOUBLE PRECISION NOT NULL,      -- futures_price * CF
    gross_basis DOUBLE PRECISION NOT NULL,        -- bond_price - invoice_price
    carry DOUBLE PRECISION,                       -- Coupon income - financing cost
    net_basis DOUBLE PRECISION,                   -- gross_basis - carry (or + carry if LSEG sign convention)
    -- Rates
    repo_rate DOUBLE PRECISION,                   -- Actual repo used for carry calc
    implied_repo_rate DOUBLE PRECISION,           -- IRR derived from basis
    -- Context
    days_to_delivery INTEGER,
    accrued_interest DOUBLE PRECISION,
    source TEXT DEFAULT 'calculated',             -- 'lseg_ctd', 'calculated'
    PRIMARY KEY (futures_contract_id, bond_cusip, ts)
);
CREATE INDEX IF NOT EXISTS idx_basis_contract_ts ON timeseries_basis(futures_contract_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_basis_cusip ON timeseries_basis(bond_cusip);

-- =============================================================================
-- Scheduler Tables
-- =============================================================================

-- Job definitions (what to extract)
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    instrument_group TEXT NOT NULL,
    granularity TEXT NOT NULL,
    schedule_cron TEXT NOT NULL,
    priority INTEGER DEFAULT 50,
    enabled BOOLEAN DEFAULT TRUE,
    lookback_days INTEGER DEFAULT 5,
    max_chunk_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_group ON scheduler_jobs(instrument_group);
CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_enabled ON scheduler_jobs(enabled);

-- Per-instrument extraction state
CREATE TABLE IF NOT EXISTS scheduler_state (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES scheduler_jobs(id) ON DELETE CASCADE,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    last_success_date DATE,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    error_message TEXT,
    UNIQUE (job_id, instrument_id)
);
CREATE INDEX IF NOT EXISTS idx_scheduler_state_job ON scheduler_state(job_id);
CREATE INDEX IF NOT EXISTS idx_scheduler_state_failures ON scheduler_state(consecutive_failures) WHERE consecutive_failures > 0;
CREATE INDEX IF NOT EXISTS idx_scheduler_state_last_success ON scheduler_state(last_success_date) WHERE last_success_date IS NOT NULL;

-- Job run history (audit log)
CREATE TABLE IF NOT EXISTS scheduler_runs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES scheduler_jobs(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    instruments_total INTEGER DEFAULT 0,
    instruments_success INTEGER DEFAULT 0,
    instruments_failed INTEGER DEFAULT 0,
    rows_extracted INTEGER DEFAULT 0,
    error_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_job ON scheduler_runs(job_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_status ON scheduler_runs(status) WHERE status = 'running';
"""

# =============================================================================
# Hypertable Configuration
# =============================================================================

HYPERTABLE_SQL = """
-- =============================================================================
-- Convert timeseries tables to hypertables
-- =============================================================================

-- OHLCV: 1 month chunks with space partitioning by instrument_id
SELECT create_hypertable(
    'timeseries_ohlcv',
    'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);
SELECT add_dimension(
    'timeseries_ohlcv',
    by_hash('instrument_id', 4),
    if_not_exists => TRUE
);

-- Quote: 1 month chunks with space partitioning
SELECT create_hypertable(
    'timeseries_quote',
    'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);
SELECT add_dimension(
    'timeseries_quote',
    by_hash('instrument_id', 4),
    if_not_exists => TRUE
);

-- Rate: 1 month chunks with space partitioning
SELECT create_hypertable(
    'timeseries_rate',
    'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);
SELECT add_dimension(
    'timeseries_rate',
    by_hash('instrument_id', 4),
    if_not_exists => TRUE
);

-- Bond: 1 month chunks with space partitioning
SELECT create_hypertable(
    'timeseries_bond',
    'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);
SELECT add_dimension(
    'timeseries_bond',
    by_hash('instrument_id', 4),
    if_not_exists => TRUE
);

-- Fixing: 1 year chunks (daily data, lower volume)
SELECT create_hypertable(
    'timeseries_fixing',
    'date',
    chunk_time_interval => INTERVAL '1 year',
    if_not_exists => TRUE
);

-- Basis: 1 month chunks with space partitioning by futures contract
SELECT create_hypertable(
    'timeseries_basis',
    'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);
SELECT add_dimension(
    'timeseries_basis',
    by_hash('futures_contract_id', 4),
    if_not_exists => TRUE
);
"""

# =============================================================================
# Compression Policies
# =============================================================================

COMPRESSION_SQL = """
-- =============================================================================
-- Enable compression on hypertables
-- =============================================================================

-- OHLCV compression (segment by instrument for efficient single-instrument queries)
ALTER TABLE timeseries_ohlcv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument_id, granularity',
    timescaledb.compress_orderby = 'ts DESC'
);

-- Quote compression
ALTER TABLE timeseries_quote SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument_id, granularity',
    timescaledb.compress_orderby = 'ts DESC'
);

-- Rate compression
ALTER TABLE timeseries_rate SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument_id, granularity',
    timescaledb.compress_orderby = 'ts DESC'
);

-- Bond compression
ALTER TABLE timeseries_bond SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument_id, granularity',
    timescaledb.compress_orderby = 'ts DESC'
);

-- Fixing compression
ALTER TABLE timeseries_fixing SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'instrument_id',
    timescaledb.compress_orderby = 'date DESC'
);

-- Basis compression
ALTER TABLE timeseries_basis SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'futures_contract_id, bond_cusip',
    timescaledb.compress_orderby = 'ts DESC'
);

-- =============================================================================
-- Add compression policies (auto-compress chunks older than N days)
-- =============================================================================

SELECT add_compression_policy('timeseries_ohlcv', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('timeseries_quote', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('timeseries_rate', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('timeseries_bond', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('timeseries_fixing', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_compression_policy('timeseries_basis', INTERVAL '7 days', if_not_exists => TRUE);
"""

# =============================================================================
# Views
# =============================================================================

VIEWS_SQL = """
-- Data coverage view for gap analysis
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


def init_schema(conn: psycopg.Connection) -> None:
    """
    Initialize the TimescaleDB schema.

    Creates all tables, converts timeseries tables to hypertables,
    and sets up compression policies.

    Args:
        conn: PostgreSQL connection.

    Raises:
        StorageError: If schema initialization fails.
    """
    try:
        with conn.cursor() as cur:
            # Create base tables
            cur.execute(SCHEMA_SQL)

            # Convert to hypertables (idempotent with if_not_exists)
            cur.execute(HYPERTABLE_SQL)

            # Set up compression (idempotent)
            try:
                cur.execute(COMPRESSION_SQL)
            except psycopg.Error as e:
                # Compression may fail if already configured differently
                # This is non-fatal
                if "already set" not in str(e).lower():
                    raise

            # Create views
            cur.execute(VIEWS_SQL)

        conn.commit()
    except psycopg.Error as e:
        raise StorageError(f"Failed to initialize schema: {e}") from e


def check_timescaledb(conn: psycopg.Connection) -> bool:
    """
    Check if TimescaleDB extension is available.

    Args:
        conn: PostgreSQL connection.

    Returns:
        True if TimescaleDB is installed and available.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
            )
            result = cur.fetchone()
            return bool(result and result["exists"])
    except psycopg.Error:
        return False
