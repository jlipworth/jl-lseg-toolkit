"""Database schema DDL for prediction market tables."""

import psycopg
from psycopg.rows import dict_row

PM_SCHEMA_SQL = """
-- Prediction market platforms
CREATE TABLE IF NOT EXISTS pm_platforms (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    api_base_url TEXT NOT NULL,
    is_regulated BOOLEAN DEFAULT FALSE,
    currency TEXT DEFAULT 'USD'
);

-- Series: groups of related markets
CREATE TABLE IF NOT EXISTS pm_series (
    id SERIAL PRIMARY KEY,
    platform_id INTEGER NOT NULL REFERENCES pm_platforms(id),
    series_ticker TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'economics',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (platform_id, series_ticker)
);
CREATE INDEX IF NOT EXISTS idx_pm_series_platform
    ON pm_series(platform_id);

-- Individual market contracts
CREATE TABLE IF NOT EXISTS pm_markets (
    id SERIAL PRIMARY KEY,
    platform_id INTEGER NOT NULL REFERENCES pm_platforms(id),
    series_id INTEGER REFERENCES pm_series(id),
    market_ticker TEXT NOT NULL,
    platform_market_id TEXT NOT NULL,
    event_ticker TEXT,
    condition_id TEXT,
    token_id TEXT,
    outcome_label TEXT,
    event_slug TEXT,
    question_slug TEXT,
    title TEXT NOT NULL,
    subtitle TEXT,
    strike_value DOUBLE PRECISION,
    open_time TIMESTAMPTZ,
    close_time TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    result TEXT,
    last_price DOUBLE PRECISION,
    last_trade_time TIMESTAMPTZ,
    volume INTEGER,
    open_interest INTEGER,
    fomc_meeting_id INTEGER REFERENCES fomc_meetings(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (platform_id, market_ticker)
);
CREATE INDEX IF NOT EXISTS idx_pm_markets_series ON pm_markets(series_id);
CREATE INDEX IF NOT EXISTS idx_pm_markets_fomc ON pm_markets(fomc_meeting_id);
CREATE INDEX IF NOT EXISTS idx_pm_markets_status ON pm_markets(status);
CREATE INDEX IF NOT EXISTS idx_pm_markets_event_ticker ON pm_markets(event_ticker);
ALTER TABLE pm_markets
    ADD COLUMN IF NOT EXISTS last_trade_time TIMESTAMPTZ;
ALTER TABLE pm_markets
    ADD COLUMN IF NOT EXISTS condition_id TEXT;
ALTER TABLE pm_markets
    ADD COLUMN IF NOT EXISTS token_id TEXT;
ALTER TABLE pm_markets
    ADD COLUMN IF NOT EXISTS outcome_label TEXT;
ALTER TABLE pm_markets
    ADD COLUMN IF NOT EXISTS event_slug TEXT;
ALTER TABLE pm_markets
    ADD COLUMN IF NOT EXISTS question_slug TEXT;
CREATE INDEX IF NOT EXISTS idx_pm_markets_last_trade_time
    ON pm_markets(last_trade_time);
CREATE INDEX IF NOT EXISTS idx_pm_markets_condition_id
    ON pm_markets(condition_id);
CREATE INDEX IF NOT EXISTS idx_pm_markets_token_id
    ON pm_markets(token_id);

-- Daily OHLC candlesticks
CREATE TABLE IF NOT EXISTS pm_candlesticks (
    market_id INTEGER NOT NULL REFERENCES pm_markets(id),
    ts TIMESTAMPTZ NOT NULL,
    price_open DOUBLE PRECISION,
    price_high DOUBLE PRECISION,
    price_low DOUBLE PRECISION,
    price_close DOUBLE PRECISION,
    price_mean DOUBLE PRECISION,
    yes_bid_close DOUBLE PRECISION,
    yes_ask_close DOUBLE PRECISION,
    volume INTEGER,
    open_interest INTEGER,
    PRIMARY KEY (market_id, ts)
);
"""

PM_HYPERTABLE_SQL = """
SELECT create_hypertable(
    'pm_candlesticks', 'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);
"""

PM_COMPRESSION_SQL = """
ALTER TABLE pm_candlesticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'market_id',
    timescaledb.compress_orderby = 'ts DESC'
);

SELECT add_compression_policy(
    'pm_candlesticks',
    compress_after => INTERVAL '3 months',
    if_not_exists => TRUE
);
"""


def init_pm_schema(conn: psycopg.Connection) -> None:
    """
    Create prediction market tables, hypertable, and compression policy.

    Safe to re-run (idempotent). Compression ALTER TABLE may fail if
    settings already exist; this is caught and logged.

    Args:
        conn: PostgreSQL connection. Must have TimescaleDB extension enabled.
    """
    with conn.cursor() as cur:
        cur.execute(PM_SCHEMA_SQL)
        cur.execute(PM_HYPERTABLE_SQL)
        try:
            cur.execute(PM_COMPRESSION_SQL)
        except psycopg.Error as e:
            if "already" not in str(e).lower():
                raise
            # Compression settings already configured — safe to ignore
    conn.commit()


def seed_kalshi_platform(conn: psycopg.Connection) -> int:
    """
    Insert or update the Kalshi platform row.

    Returns:
        The platform ID.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO pm_platforms (name, display_name, api_base_url, is_regulated, currency)
            VALUES ('kalshi', 'Kalshi', 'https://api.elections.kalshi.com/trade-api/v2', TRUE, 'USD')
            ON CONFLICT (name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                api_base_url = EXCLUDED.api_base_url,
                is_regulated = EXCLUDED.is_regulated
            RETURNING id
            """,
        )
        result = cur.fetchone()
        return result["id"] if result else 0


def seed_polymarket_platform(conn: psycopg.Connection) -> int:
    """
    Insert or update the Polymarket platform row.

    Returns:
        The platform ID.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO pm_platforms (name, display_name, api_base_url, is_regulated, currency)
            VALUES ('polymarket', 'Polymarket', 'https://gamma-api.polymarket.com', FALSE, 'USD')
            ON CONFLICT (name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                api_base_url = EXCLUDED.api_base_url,
                is_regulated = EXCLUDED.is_regulated
            RETURNING id
            """,
        )
        result = cur.fetchone()
        return result["id"] if result else 0
