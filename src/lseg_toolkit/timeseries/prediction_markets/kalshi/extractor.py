"""Kalshi data extraction orchestrator.

Handles historical backfill and daily refresh of prediction market data.
Follows FK dependency order: platform → series → markets → candlesticks.
"""

import logging
import re
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.fomc import sync_fomc_meetings
from lseg_toolkit.timeseries.prediction_markets.kalshi.client import KalshiClient
from lseg_toolkit.timeseries.prediction_markets.models import (
    Candlestick,
    Market,
    Series,
)
from lseg_toolkit.timeseries.prediction_markets.schema import seed_kalshi_platform
from lseg_toolkit.timeseries.prediction_markets.storage import (
    upsert_candlesticks,
    upsert_market,
    upsert_series,
)
from lseg_toolkit.timeseries.storage import get_connection

logger = logging.getLogger(__name__)

SERIES_TICKERS = ["KXFED", "KXFEDDECISION", "KXRATECUTCOUNT"]

# Regex to extract strike value from tickers like KXFED-26JAN-T4.50
_STRIKE_RE = re.compile(r"-T(\d+\.?\d*)$")


def parse_market(
    raw: dict,
    platform_id: int,
    series_id: int | None = None,
) -> Market:
    """Parse a Kalshi API market dict into a Market model."""
    ticker = raw.get("ticker", "")

    # Extract strike value from ticker (e.g., T4.50)
    strike_match = _STRIKE_RE.search(ticker)
    strike_value = float(strike_match.group(1)) if strike_match else None

    # Parse timestamps
    open_time = None
    if raw.get("open_time"):
        open_time = datetime.fromisoformat(raw["open_time"].replace("Z", "+00:00"))

    close_time = None
    if raw.get("close_time"):
        close_time = datetime.fromisoformat(raw["close_time"].replace("Z", "+00:00"))

    last_trade_time = None
    last_trade_time_raw = raw.get("last_trade_time")
    if isinstance(last_trade_time_raw, datetime):
        last_trade_time = last_trade_time_raw
    elif isinstance(last_trade_time_raw, str):
        last_trade_time = datetime.fromisoformat(
            last_trade_time_raw.replace("Z", "+00:00")
        )

    # Kalshi API v2 uses _dollars/_fp suffixes; fall back to legacy names
    last_price = raw.get("last_price_dollars") or raw.get("last_price")
    volume = raw.get("volume_fp") or raw.get("volume")
    open_interest = raw.get("open_interest_fp") or raw.get("open_interest")

    # Normalize status: API currently uses "open" / "settled".
    # Older docs/examples referenced "active" / "finalized".
    status = raw.get("status", "active")
    if status == "open":
        status = "active"
    elif status == "finalized":
        status = "settled"

    return Market(
        platform_id=platform_id,
        series_id=series_id,
        market_ticker=ticker,
        platform_market_id=ticker,
        event_ticker=raw.get("event_ticker"),
        title=raw.get("title", ""),
        subtitle=raw.get("subtitle"),
        strike_value=strike_value,
        open_time=open_time,
        close_time=close_time,
        status=status,
        result=raw.get("result"),
        last_price=float(last_price) if last_price is not None else None,
        last_trade_time=last_trade_time,
        volume=int(float(volume)) if volume is not None else None,
        open_interest=int(float(open_interest)) if open_interest is not None else None,
    )


def _get_price(d: dict, key: str) -> float | None:
    """Extract a price value, handling both v1 and v2 API field names."""
    # v2 uses _dollars suffix, v1 uses plain names
    val = d.get(f"{key}_dollars") or d.get(key)
    return float(val) if val is not None else None


def parse_candlestick(raw: dict, market_id: int) -> Candlestick:
    """Parse a Kalshi API candlestick dict into a Candlestick model."""
    ts = datetime.fromtimestamp(raw["end_period_ts"], tz=UTC)
    price = raw.get("price", {})
    yes_bid = raw.get("yes_bid", {})
    yes_ask = raw.get("yes_ask", {})

    # v2 uses volume_fp/open_interest_fp (string), v1 uses volume/open_interest (int)
    volume_raw = raw.get("volume_fp") or raw.get("volume")
    oi_raw = raw.get("open_interest_fp") or raw.get("open_interest")

    return Candlestick(
        market_id=market_id,
        ts=ts,
        price_open=_get_price(price, "open"),
        price_high=_get_price(price, "high"),
        price_low=_get_price(price, "low"),
        price_close=_get_price(price, "close"),
        price_mean=_get_price(price, "mean"),
        yes_bid_close=_get_price(yes_bid, "close"),
        yes_ask_close=_get_price(yes_ask, "close"),
        volume=int(float(volume_raw)) if volume_raw is not None else None,
        open_interest=int(float(oi_raw)) if oi_raw is not None else None,
    )


def link_fomc_meeting(
    conn: psycopg.Connection,
    close_time: datetime,
) -> int | None:
    """
    Find the FOMC meeting ID matching a market's close_time date.

    Returns:
        Meeting ID if found, None otherwise.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id FROM fomc_meetings WHERE meeting_date = %s",
            (close_time.date(),),
        )
        result = cur.fetchone()
        return result["id"] if result else None


def _process_markets(
    conn: psycopg.Connection,
    client: KalshiClient,
    platform_id: int,
    series_ticker: str,
    series_id: int,
    status: str | None = None,
) -> list[int]:
    """Fetch, parse, link, and store markets. Returns list of market IDs."""
    raw_markets = client.list_markets(
        series_ticker=series_ticker,
        status=status,
    )

    market_ids: list[int] = []
    for raw in raw_markets:
        market = parse_market(raw, platform_id=platform_id, series_id=series_id)

        # Link to FOMC meeting
        if market.close_time:
            market.fomc_meeting_id = link_fomc_meeting(conn, market.close_time)

        market_id = upsert_market(conn, market)
        market_ids.append(market_id)

    conn.commit()
    logger.info(
        "Upserted %d markets for %s (status=%s)",
        len(market_ids),
        series_ticker,
        status,
    )
    return market_ids


def _fetch_candlesticks_for_markets(
    conn: psycopg.Connection,
    client: KalshiClient,
    series_ticker: str,
    market_tickers: list[str],
    market_ids: list[int],
) -> int:
    """Fetch and store candlesticks for a list of markets. Returns total count.

    Partial failures are logged and skipped — the market can be re-fetched
    on next run due to idempotent upserts (per design spec).

    A fresh pooled DB connection is used per market write batch so a dropped
    long-lived transaction doesn't poison the remainder of the series backfill.
    """
    total = 0
    for ticker, market_id in zip(market_tickers, market_ids, strict=True):
        try:
            raw_candles = client.get_candlesticks(
                series_ticker=series_ticker,
                market_ticker=ticker,
            )
            if not raw_candles:
                continue

            candles = [parse_candlestick(c, market_id=market_id) for c in raw_candles]
            with get_connection() as write_conn:
                count = upsert_candlesticks(write_conn, candles)
            total += count
        except Exception:
            logger.warning(
                "Failed to fetch candlesticks for %s, skipping",
                ticker,
                exc_info=True,
            )
            continue

    logger.info(
        "Upserted %d candlesticks for %s (%d markets)",
        total,
        series_ticker,
        len(market_tickers),
    )
    return total


def _filter_markets_missing_candlesticks(
    conn: psycopg.Connection,
    market_tickers: list[str],
    market_ids: list[int],
) -> tuple[list[str], list[int]]:
    """
    Return only markets that do not yet have stored candlesticks.

    This makes historical backfill resumable/idempotent after interruptions:
    once a market has at least one candlestick row, we assume that market's
    historical batch completed successfully and skip re-fetching it.
    """
    if not market_ids:
        return ([], [])

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT DISTINCT market_id
            FROM pm_candlesticks
            WHERE market_id = ANY(%(market_ids)s)
            """,
            {"market_ids": market_ids},
        )
        existing_ids = {row["market_id"] for row in cur.fetchall()}

    missing_tickers: list[str] = []
    missing_ids: list[int] = []
    for ticker, market_id in zip(market_tickers, market_ids, strict=True):
        if market_id in existing_ids:
            continue
        missing_tickers.append(ticker)
        missing_ids.append(market_id)

    return (missing_tickers, missing_ids)


def backfill(conn: psycopg.Connection) -> dict:
    """
    Historical backfill: fetch all settled markets and their candlesticks.

    Order follows FK dependencies:
    1. Seed platform
    2. Upsert series
    3. Fetch settled markets → upsert with FOMC linkage
    4. Fetch candlesticks for each market

    Returns:
        Summary dict with counts.
    """
    sync_fomc_meetings(conn)
    client = KalshiClient()
    platform_id = seed_kalshi_platform(conn)

    summary: dict = {"platform_id": platform_id, "series": {}}

    for series_ticker in SERIES_TICKERS:
        series = Series(
            platform_id=platform_id,
            series_ticker=series_ticker,
            title=series_ticker,
        )
        series_id = upsert_series(conn, series)

        # Fetch all markets (settled + active) for complete picture
        raw_markets = client.list_markets(series_ticker=series_ticker)

        market_ids: list[int] = []
        market_tickers: list[str] = []
        for raw in raw_markets:
            market = parse_market(raw, platform_id=platform_id, series_id=series_id)
            if market.close_time:
                market.fomc_meeting_id = link_fomc_meeting(conn, market.close_time)

            market_id = upsert_market(conn, market)
            market_ids.append(market_id)
            market_tickers.append(market.market_ticker)

        conn.commit()

        # Fetch candlesticks for finalized/settled markets only (complete data)
        # Kalshi API v2 uses "finalized" status for completed markets
        done_statuses = {"settled", "finalized"}
        settled_raw = [m for m in raw_markets if m.get("status") in done_statuses]
        settled_tickers = [m["ticker"] for m in settled_raw]
        settled_ids = [
            mid
            for mid, raw in zip(market_ids, raw_markets, strict=True)
            if raw.get("status") in done_statuses
        ]
        settled_tickers, settled_ids = _filter_markets_missing_candlesticks(
            conn,
            settled_tickers,
            settled_ids,
        )

        candle_count = _fetch_candlesticks_for_markets(
            conn, client, series_ticker, settled_tickers, settled_ids
        )

        summary["series"][series_ticker] = {
            "series_id": series_id,
            "markets": len(market_ids),
            "candlesticks": candle_count,
        }

    logger.info("Backfill complete: %s", summary)
    return summary


def daily_refresh(conn: psycopg.Connection) -> dict:
    """
    Daily refresh: update active markets and fetch today's candlesticks.

    Returns:
        Summary dict with counts.
    """
    sync_fomc_meetings(conn)
    client = KalshiClient()
    platform_id = seed_kalshi_platform(conn)

    summary: dict = {"series": {}}

    for series_ticker in SERIES_TICKERS:
        series = Series(
            platform_id=platform_id,
            series_ticker=series_ticker,
            title=series_ticker,
        )
        series_id = upsert_series(conn, series)

        raw_markets = client.list_markets(
            series_ticker=series_ticker,
            status="active",
        )

        market_ids: list[int] = []
        market_tickers: list[str] = []
        for raw in raw_markets:
            raw["last_trade_time"] = client.get_last_trade_time(raw["ticker"])
            market = parse_market(raw, platform_id=platform_id, series_id=series_id)
            if market.close_time:
                market.fomc_meeting_id = link_fomc_meeting(conn, market.close_time)

            market_id = upsert_market(conn, market)
            market_ids.append(market_id)
            market_tickers.append(market.market_ticker)

        conn.commit()

        candle_count = _fetch_candlesticks_for_markets(
            conn, client, series_ticker, market_tickers, market_ids
        )

        summary["series"][series_ticker] = {
            "markets": len(market_ids),
            "candlesticks": candle_count,
        }

    logger.info("Daily refresh complete: %s", summary)
    return summary
