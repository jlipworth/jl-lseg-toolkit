"""Storage operations for prediction market data."""

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.prediction_markets.models import (
    Candlestick,
    Market,
    Series,
)


def upsert_series(conn: psycopg.Connection, series: Series) -> int:
    """
    Insert or update a prediction market series.

    Returns:
        The series ID.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO pm_series (platform_id, series_ticker, title, category)
            VALUES (%(platform_id)s, %(series_ticker)s, %(title)s, %(category)s)
            ON CONFLICT (platform_id, series_ticker) DO UPDATE SET
                title = EXCLUDED.title,
                category = EXCLUDED.category
            RETURNING id
            """,
            {
                "platform_id": series.platform_id,
                "series_ticker": series.series_ticker,
                "title": series.title,
                "category": series.category,
            },
        )
        result = cur.fetchone()
        return result["id"] if result else 0


def upsert_market(conn: psycopg.Connection, market: Market) -> int:
    """
    Insert or update a prediction market contract.

    Returns:
        The market ID.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO pm_markets (
                platform_id, series_id, market_ticker, platform_market_id,
                event_ticker, title, subtitle, strike_value,
                open_time, close_time, status, result,
                last_price, last_trade_time, volume, open_interest, fomc_meeting_id,
                updated_at
            ) VALUES (
                %(platform_id)s, %(series_id)s, %(market_ticker)s, %(platform_market_id)s,
                %(event_ticker)s, %(title)s, %(subtitle)s, %(strike_value)s,
                %(open_time)s, %(close_time)s, %(status)s, %(result)s,
                %(last_price)s, %(last_trade_time)s, %(volume)s, %(open_interest)s, %(fomc_meeting_id)s,
                NOW()
            )
            ON CONFLICT (platform_id, market_ticker) DO UPDATE SET
                series_id = EXCLUDED.series_id,
                event_ticker = EXCLUDED.event_ticker,
                title = EXCLUDED.title,
                subtitle = EXCLUDED.subtitle,
                strike_value = EXCLUDED.strike_value,
                open_time = EXCLUDED.open_time,
                close_time = EXCLUDED.close_time,
                status = EXCLUDED.status,
                result = EXCLUDED.result,
                last_price = EXCLUDED.last_price,
                last_trade_time = EXCLUDED.last_trade_time,
                volume = EXCLUDED.volume,
                open_interest = EXCLUDED.open_interest,
                fomc_meeting_id = EXCLUDED.fomc_meeting_id,
                updated_at = NOW()
            RETURNING id
            """,
            {
                "platform_id": market.platform_id,
                "series_id": market.series_id,
                "market_ticker": market.market_ticker,
                "platform_market_id": market.platform_market_id,
                "event_ticker": market.event_ticker,
                "title": market.title,
                "subtitle": market.subtitle,
                "strike_value": market.strike_value,
                "open_time": market.open_time,
                "close_time": market.close_time,
                "status": market.status,
                "result": market.result,
                "last_price": market.last_price,
                "last_trade_time": market.last_trade_time,
                "volume": market.volume,
                "open_interest": market.open_interest,
                "fomc_meeting_id": market.fomc_meeting_id,
            },
        )
        result = cur.fetchone()
        return result["id"] if result else 0


def upsert_candlestick(conn: psycopg.Connection, candle: Candlestick) -> None:
    """Insert or update a single candlestick record."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pm_candlesticks (
                market_id, ts, price_open, price_high, price_low,
                price_close, price_mean, yes_bid_close, yes_ask_close,
                volume, open_interest
            ) VALUES (
                %(market_id)s, %(ts)s, %(price_open)s, %(price_high)s, %(price_low)s,
                %(price_close)s, %(price_mean)s, %(yes_bid_close)s, %(yes_ask_close)s,
                %(volume)s, %(open_interest)s
            )
            ON CONFLICT (market_id, ts) DO UPDATE SET
                price_open = EXCLUDED.price_open,
                price_high = EXCLUDED.price_high,
                price_low = EXCLUDED.price_low,
                price_close = EXCLUDED.price_close,
                price_mean = EXCLUDED.price_mean,
                yes_bid_close = EXCLUDED.yes_bid_close,
                yes_ask_close = EXCLUDED.yes_ask_close,
                volume = EXCLUDED.volume,
                open_interest = EXCLUDED.open_interest
            """,
            {
                "market_id": candle.market_id,
                "ts": candle.ts,
                "price_open": candle.price_open,
                "price_high": candle.price_high,
                "price_low": candle.price_low,
                "price_close": candle.price_close,
                "price_mean": candle.price_mean,
                "yes_bid_close": candle.yes_bid_close,
                "yes_ask_close": candle.yes_ask_close,
                "volume": candle.volume,
                "open_interest": candle.open_interest,
            },
        )


def upsert_candlesticks(
    conn: psycopg.Connection,
    candles: list[Candlestick],
) -> int:
    """
    Insert or update multiple candlestick records.

    Returns:
        Number of records upserted.
    """
    for candle in candles:
        upsert_candlestick(conn, candle)
    return len(candles)


def get_platform_by_name(
    conn: psycopg.Connection,
    name: str,
) -> dict | None:
    """Get a platform by name."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM pm_platforms WHERE name = %s",
            (name,),
        )
        return cur.fetchone()


def get_markets_by_series(
    conn: psycopg.Connection,
    series_id: int,
    status: str | None = None,
) -> list[dict]:
    """
    Get markets for a series, optionally filtered by status.

    Args:
        conn: PostgreSQL connection.
        series_id: The series ID.
        status: Optional filter ('active', 'closed', 'settled').

    Returns:
        List of market records as dicts.
    """
    params: dict = {"series_id": series_id}
    status_filter = ""
    if status:
        status_filter = "AND status = %(status)s"
        params["status"] = status

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT * FROM pm_markets
            WHERE series_id = %(series_id)s {status_filter}
            ORDER BY market_ticker
            """,
            params,
        )
        return list(cur.fetchall())


def get_markets_by_event(
    conn: psycopg.Connection,
    event_ticker: str,
) -> list[dict]:
    """
    Get all markets for a Kalshi event (e.g., KXFED-26JAN).

    Args:
        conn: PostgreSQL connection.
        event_ticker: The event ticker.

    Returns:
        List of market records ordered by strike_value.
        Convert to Market models via Market(**row) for use with
        analysis functions (rate_distribution, implied_rate).
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT * FROM pm_markets
            WHERE event_ticker = %(event_ticker)s
            ORDER BY strike_value
            """,
            {"event_ticker": event_ticker},
        )
        return list(cur.fetchall())


def get_candlesticks(
    conn: psycopg.Connection,
    market_id: int,
) -> list[dict]:
    """
    Get all candlesticks for a market, ordered by timestamp.

    Args:
        conn: PostgreSQL connection.
        market_id: The market ID.

    Returns:
        List of candlestick records as dicts.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT * FROM pm_candlesticks
            WHERE market_id = %s
            ORDER BY ts
            """,
            (market_id,),
        )
        return list(cur.fetchall())
