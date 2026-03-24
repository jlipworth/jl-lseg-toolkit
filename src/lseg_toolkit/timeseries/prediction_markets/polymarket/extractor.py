"""Polymarket extraction orchestrator.

Supports metadata ingest, active-market refresh, targeted Fed/macro discovery,
and explicit/manual trade-derived candlestick backfill.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.fomc.storage import get_fomc_meetings
from lseg_toolkit.timeseries.prediction_markets.models import Market, Series
from lseg_toolkit.timeseries.prediction_markets.polymarket.client import (
    PolymarketClient,
)
from lseg_toolkit.timeseries.prediction_markets.polymarket.resolution import (
    is_macro_resolution_candidate,
    resolve_market_family,
    suggest_fomc_meeting_id,
)
from lseg_toolkit.timeseries.prediction_markets.polymarket.trades import (
    aggregate_daily_candles,
    get_condition_trades,
    get_last_trade_times_by_token,
)
from lseg_toolkit.timeseries.prediction_markets.schema import (
    seed_polymarket_platform,
)
from lseg_toolkit.timeseries.prediction_markets.storage import (
    upsert_candlesticks,
    upsert_market,
    upsert_series,
)

logger = logging.getLogger(__name__)

FED_DISCOVERY_QUERIES = (
    "fed",
    "fomc",
    "federal reserve",
    "rate cut",
    "interest rate",
    "fed funds",
    "powell",
    "cpi",
    "inflation",
    "recession",
)
FED_DISCOVERY_TAG_SLUGS = {
    "fed",
    "fed-rates",
    "fomc",
    "powell",
    "jerome-powell",
    "macro",
    "macro-indicators",
    "macro-unemployment",
    "inflation",
    "jobs-report",
}
FED_DISCOVERY_POSITIVE_TERMS = (
    "federal reserve",
    "federal funds",
    "fed decision",
    "fed rate",
    "fed rates",
    "fomc",
    "rate cut",
    "rate hike",
    "interest rate",
    "powell",
    "inflation",
    "cpi",
    "jobs report",
    "unemployment",
)
FED_DISCOVERY_NEGATIVE_TERMS = (
    "federal charge",
    "federal charges",
    "federal criminal",
    "federal prison",
    "federal judge",
)


def _parse_json_list(value: str | list | None) -> list:
    """Parse a Polymarket field that may be a JSON string or already a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO8601 timestamps used by Polymarket."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _coerce_int(value: Any) -> int | None:
    """Coerce numeric-ish values to int, rounding when needed."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(round(float(value)))
    if isinstance(value, str):
        try:
            return int(round(float(value)))
        except ValueError:
            return None
    return None


def _market_text(raw: dict[str, Any]) -> str:
    """Build a normalized text blob for discovery heuristics."""
    parts: list[str] = []
    fields = (
        "title",
        "question",
        "slug",
        "description",
        "resolutionSource",
        "seriesSlug",
    )
    for field in fields:
        value = raw.get(field)
        if isinstance(value, str):
            parts.append(value)

    for tag in raw.get("tags") or []:
        if isinstance(tag, dict):
            for key in ("label", "slug"):
                value = tag.get(key)
                if isinstance(value, str):
                    parts.append(value)

    for market in raw.get("markets") or []:
        if isinstance(market, dict):
            for key in ("question", "slug", "description"):
                value = market.get(key)
                if isinstance(value, str):
                    parts.append(value)

    return " \n".join(parts).lower()


def is_fed_discovery_match(raw: dict[str, Any]) -> bool:
    """Return True when an event/market looks Fed or macro related."""
    return is_macro_resolution_candidate(raw)


def _event_stub(event: dict[str, Any]) -> dict[str, Any]:
    """Extract the event metadata we need to attach to nested markets."""
    return {
        "slug": event.get("slug"),
        "title": event.get("title"),
        "startDate": event.get("startDate"),
        "endDate": event.get("endDate"),
        "category": event.get("category"),
    }


def extract_event_markets(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten discovered event rows into market rows with attached event context."""
    flattened: list[dict[str, Any]] = []
    seen_condition_ids: set[str] = set()

    for event in events:
        if not isinstance(event, dict):
            continue
        event_stub = _event_stub(event)
        for market in event.get("markets") or []:
            if not isinstance(market, dict):
                continue
            condition_id = market.get("conditionId")
            if not isinstance(condition_id, str) or condition_id in seen_condition_ids:
                continue

            row = dict(market)
            row["events"] = [event_stub]
            flattened.append(row)
            seen_condition_ids.add(condition_id)

    return flattened


def discover_fed_events(
    client: PolymarketClient | None = None,
    *,
    queries: Iterable[str] = FED_DISCOVERY_QUERIES,
    limit_per_type: int = 10,
    max_event_pages: int = 1,
    active: bool | None = None,
    closed: bool | None = None,
) -> list[dict[str, Any]]:
    """Discover Fed/macro-relevant Polymarket events via search + tag expansion."""
    client = client or PolymarketClient()

    events_by_slug: dict[str, dict[str, Any]] = {}
    discovered_tag_ids: set[int] = set()

    def add_events(rows: Iterable[dict[str, Any]]) -> None:
        for row in rows:
            if not isinstance(row, dict) or not is_fed_discovery_match(row):
                continue
            slug = row.get("slug") or row.get("ticker") or row.get("id")
            if not slug:
                continue
            events_by_slug[str(slug)] = row

    for query in queries:
        payload = client.search_public(str(query), limit_per_type=limit_per_type)
        add_events(payload.get("events") or [])
        for tag in payload.get("tags") or []:
            if not isinstance(tag, dict):
                continue
            tag_slug = str(tag.get("slug") or "").lower()
            tag_label = str(tag.get("label") or "").lower()
            tag_id = tag.get("id")
            if not isinstance(tag_id, int):
                continue
            if tag_slug in FED_DISCOVERY_TAG_SLUGS or any(
                term in f"{tag_label} {tag_slug}"
                for term in FED_DISCOVERY_POSITIVE_TERMS
            ):
                discovered_tag_ids.add(tag_id)

    for tag in client.list_tags(limit=500, max_pages=1):
        if not isinstance(tag, dict):
            continue
        tag_id = tag.get("id")
        if not isinstance(tag_id, int):
            continue
        tag_slug = str(tag.get("slug") or "").lower()
        tag_label = str(tag.get("label") or "").lower()
        if tag_slug in FED_DISCOVERY_TAG_SLUGS or any(
            term in f"{tag_label} {tag_slug}" for term in FED_DISCOVERY_POSITIVE_TERMS
        ):
            discovered_tag_ids.add(tag_id)

    for tag_id in sorted(discovered_tag_ids):
        add_events(
            client.list_events(
                tag_id=tag_id,
                related_tags=True,
                active=active,
                closed=closed,
                order="volume",
                ascending=False,
                max_pages=max_event_pages,
            )
        )

    discovered = sorted(
        events_by_slug.values(),
        key=lambda row: (
            float(row.get("volume24hr") or 0),
            float(row.get("volume") or 0),
            str(row.get("slug") or ""),
        ),
        reverse=True,
    )
    logger.info("Discovered %d Fed/macro Polymarket events", len(discovered))
    return discovered


def discover_fed_markets(
    client: PolymarketClient | None = None,
    *,
    queries: Iterable[str] = FED_DISCOVERY_QUERIES,
    limit_per_type: int = 10,
    max_event_pages: int = 1,
    active: bool | None = None,
    closed: bool | None = None,
) -> list[dict[str, Any]]:
    """Discover Fed/macro-relevant market rows with event context attached."""
    events = discover_fed_events(
        client=client,
        queries=queries,
        limit_per_type=limit_per_type,
        max_event_pages=max_event_pages,
        active=active,
        closed=closed,
    )
    return extract_event_markets(events)


def _get_fomc_meeting_id_map(conn: psycopg.Connection | None) -> dict:
    """Build a date -> meeting id lookup for dry-run linkage suggestions."""
    if conn is None:
        return {}
    return {
        row["meeting_date"]: row["id"]
        for row in get_fomc_meetings(conn)
        if row.get("meeting_date") is not None and row.get("id") is not None
    }


def discover_fed_event_summaries(
    conn: psycopg.Connection | None = None,
    client: PolymarketClient | None = None,
    *,
    queries: Iterable[str] = FED_DISCOVERY_QUERIES,
    limit_per_type: int = 10,
    max_event_pages: int = 1,
    active: bool | None = None,
    closed: bool | None = None,
) -> list[dict[str, Any]]:
    """Return dry-run event summaries with conservative family resolution.

    This is intended for manual review and troubleshooting. It does not mutate
    the database or auto-write FOMC links.
    """
    events = discover_fed_events(
        client=client,
        queries=queries,
        limit_per_type=limit_per_type,
        max_event_pages=max_event_pages,
        active=active,
        closed=closed,
    )
    fomc_ids_by_date = _get_fomc_meeting_id_map(conn)

    summaries: list[dict[str, Any]] = []
    for event in events:
        resolution = resolve_market_family(event)
        close_time = _parse_datetime(event.get("endDate"))
        summaries.append(
            {
                "event_slug": event.get("slug"),
                "title": event.get("title"),
                "close_date": close_time.date() if close_time else None,
                "family": resolution.family,
                "is_macro_candidate": resolution.is_macro_candidate,
                "is_fomc_link_candidate": resolution.is_fomc_link_candidate,
                "suggested_fomc_meeting_id": suggest_fomc_meeting_id(
                    close_time,
                    resolution,
                    fomc_ids_by_date,
                ),
                "reason": resolution.reason,
            }
        )

    summaries.sort(
        key=lambda row: (
            row["close_date"] is None,
            row["close_date"] or datetime.max.date(),
            str(row["event_slug"] or ""),
        )
    )
    return summaries


def build_market_ticker(condition_id: str, token_id: str) -> str:
    """Build a stable synthetic market ticker for a Polymarket token."""
    return f"POLY:{condition_id}:{token_id}"


def normalize_status(raw: dict, simplified: dict | None = None) -> str:
    """Map Polymarket market booleans into our generic market statuses."""
    if simplified and simplified.get("closed") and not simplified.get("active", True):
        return "settled"
    if str(raw.get("umaResolutionStatus", "")).lower() == "resolved":
        return "settled"
    if raw.get("closed"):
        return "closed"
    if raw.get("archived"):
        return "closed"
    if raw.get("active"):
        return "active"
    return "active"


def parse_series(raw: dict, platform_id: int) -> Series:
    """Parse a Polymarket Gamma market row into a series bucket."""
    events = raw.get("events") or []
    event0 = events[0] if events else {}
    series_ticker = (
        event0.get("slug")
        or raw.get("eventSlug")
        or raw.get("slug")
        or raw["conditionId"]
    )
    title = (
        event0.get("title") or raw.get("question") or raw.get("title") or series_ticker
    )

    return Series(
        platform_id=platform_id,
        series_ticker=series_ticker,
        title=title,
        category="prediction_markets",
    )


def parse_market_tokens(
    raw: dict,
    platform_id: int,
    series_id: int | None = None,
    *,
    simplified: dict | None = None,
    last_trade_times: dict[str, datetime | None] | None = None,
) -> list[Market]:
    """Parse a Polymarket Gamma market row into token-level Market rows."""
    condition_id = raw["conditionId"]
    outcomes = _parse_json_list(raw.get("outcomes"))
    outcome_prices = _parse_json_list(raw.get("outcomePrices"))
    token_ids = _parse_json_list(raw.get("clobTokenIds"))
    events = raw.get("events") or []
    event0 = events[0] if events else {}

    event_slug = event0.get("slug") or raw.get("eventSlug")
    question_slug = raw.get("slug")
    title = raw.get("question") or raw.get("title") or question_slug or condition_id
    open_time = _parse_datetime(
        event0.get("startDate") or raw.get("startDate") or raw.get("startDateIso")
    )
    close_time = _parse_datetime(
        event0.get("endDate") or raw.get("endDate") or raw.get("endDateIso")
    )
    status = normalize_status(raw, simplified=simplified)
    volume = _coerce_int(raw.get("volumeNum"))
    if volume is None:
        volume = _coerce_int(raw.get("volume"))

    token_lookup: dict[str, dict] = {}
    if simplified:
        for token in simplified.get("tokens", []):
            token_id = token.get("token_id")
            if isinstance(token_id, str):
                token_lookup[token_id] = token

    markets: list[Market] = []
    for idx, outcome in enumerate(outcomes):
        token_id = (
            str(token_ids[idx])
            if idx < len(token_ids) and token_ids[idx] is not None
            else f"{condition_id}:{outcome}"
        )
        last_price: float | None = None
        if idx < len(outcome_prices) and outcome_prices[idx] is not None:
            last_price = float(outcome_prices[idx])
        else:
            token_state = token_lookup.get(token_id, {})
            if isinstance(token_state.get("price"), (int, float)):
                last_price = float(token_state["price"])

        result = None
        token_state = token_lookup.get(token_id, {})
        winner = token_state.get("winner")
        if winner is True:
            result = "yes"
        elif winner is False and status == "settled":
            result = "no"

        market = Market(
            platform_id=platform_id,
            series_id=series_id,
            market_ticker=build_market_ticker(condition_id, token_id),
            platform_market_id=token_id,
            event_ticker=condition_id,
            condition_id=condition_id,
            token_id=token_id,
            outcome_label=str(outcome),
            event_slug=event_slug,
            question_slug=question_slug,
            title=title,
            subtitle=str(outcome),
            open_time=open_time,
            close_time=close_time,
            status=status,
            result=result,
            last_price=last_price,
            last_trade_time=(last_trade_times or {}).get(token_id),
            volume=volume,
        )
        markets.append(market)

    return markets


def parse_markets(
    raw: dict,
    platform_id: int,
    series_id: int | None = None,
    simplified: dict | None = None,
    last_trade_times: dict[str, datetime | None] | None = None,
) -> list[Market]:
    """Compatibility wrapper naming the token-level output rows as markets."""
    return parse_market_tokens(
        raw,
        platform_id=platform_id,
        series_id=series_id,
        simplified=simplified,
        last_trade_times=last_trade_times,
    )


def backfill(
    conn: psycopg.Connection,
    *,
    max_pages: int | None = None,
) -> dict:
    """
    Backfill Polymarket metadata into platform/series/market tables.

    Trade-derived candlesticks remain a separate explicit/manual step via
    ``backfill_candlesticks()`` or ``backfill_with_candlesticks()``.
    """
    client = PolymarketClient()
    platform_id = seed_polymarket_platform(conn)
    raw_markets = client.list_markets(max_pages=max_pages)

    series_ids: dict[str, int] = {}
    market_count = 0

    for raw in raw_markets:
        series = parse_series(raw, platform_id=platform_id)
        series_id = series_ids.get(series.series_ticker)
        if series_id is None:
            series_id = upsert_series(conn, series)
            series_ids[series.series_ticker] = series_id

        for market in parse_market_tokens(
            raw, platform_id=platform_id, series_id=series_id
        ):
            upsert_market(conn, market)
            market_count += 1

    conn.commit()
    summary = {
        "platform_id": platform_id,
        "series": len(series_ids),
        "series_count": len(series_ids),
        "markets": market_count,
        "market_count": market_count,
    }
    logger.info("Polymarket backfill complete: %s", summary)
    return summary


def backfill_fed_discovery(
    conn: psycopg.Connection,
    *,
    queries: Iterable[str] = FED_DISCOVERY_QUERIES,
    limit_per_type: int = 10,
    max_event_pages: int = 1,
    active: bool | None = None,
    closed: bool | None = None,
) -> dict:
    """Backfill targeted Fed/macro markets discovered via search + tag expansion."""
    client = PolymarketClient()
    platform_id = seed_polymarket_platform(conn)
    raw_markets = discover_fed_markets(
        client=client,
        queries=queries,
        limit_per_type=limit_per_type,
        max_event_pages=max_event_pages,
        active=active,
        closed=closed,
    )

    series_ids: dict[str, int] = {}
    market_count = 0

    for raw in raw_markets:
        series = parse_series(raw, platform_id=platform_id)
        series_id = series_ids.get(series.series_ticker)
        if series_id is None:
            series_id = upsert_series(conn, series)
            series_ids[series.series_ticker] = series_id

        for market in parse_market_tokens(
            raw, platform_id=platform_id, series_id=series_id
        ):
            upsert_market(conn, market)
            market_count += 1

    conn.commit()
    summary = {
        "platform_id": platform_id,
        "series": len(series_ids),
        "series_count": len(series_ids),
        "markets": market_count,
        "market_count": market_count,
    }
    logger.info("Polymarket Fed discovery backfill complete: %s", summary)
    return summary


def daily_refresh(
    conn: psycopg.Connection,
    *,
    limit: int | None = None,
    max_pages: int | None = None,
    include_closed: bool = False,
) -> dict:
    """
    Refresh active Polymarket markets and populate latest trade times.
    """
    client = PolymarketClient()
    platform_id = seed_polymarket_platform(conn)
    list_kwargs: dict = {
        "closed": include_closed if include_closed else False,
        "active": None if include_closed else True,
        "max_pages": max_pages,
    }
    if limit is not None:
        list_kwargs["limit"] = limit
    raw_markets = client.list_markets(**list_kwargs)
    simplified_rows = client.list_simplified_markets(max_pages=1)
    simplified_by_condition = {
        row["condition_id"]: row
        for row in simplified_rows
        if isinstance(row.get("condition_id"), str)
    }

    series_ids: dict[str, int] = {}
    market_count = 0

    for raw in raw_markets:
        series = parse_series(raw, platform_id=platform_id)
        series_id = series_ids.get(series.series_ticker)
        if series_id is None:
            series_id = upsert_series(conn, series)
            series_ids[series.series_ticker] = series_id

        token_ids = _parse_json_list(raw.get("clobTokenIds"))
        token_ids = [str(token_id) for token_id in token_ids if token_id is not None]
        last_trade_times = get_last_trade_times_by_token(
            client,
            condition_id=str(raw["conditionId"]),
            token_ids=token_ids,
        )

        for market in parse_market_tokens(
            raw,
            platform_id=platform_id,
            series_id=series_id,
            simplified=simplified_by_condition.get(raw.get("conditionId")),
            last_trade_times=last_trade_times,
        ):
            upsert_market(conn, market)
            market_count += 1

    conn.commit()
    summary = {
        "platform_id": platform_id,
        "series": len(series_ids),
        "series_count": len(series_ids),
        "markets": market_count,
        "market_count": market_count,
    }
    logger.info("Polymarket daily refresh complete: %s", summary)
    return summary


def _get_polymarket_markets_for_candles(
    conn: psycopg.Connection,
    *,
    platform_id: int,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return stored Polymarket token rows that can be used for bar derivation."""
    params: dict[str, Any] = {"platform_id": platform_id}
    status_filter = ""
    if status is not None:
        params["status"] = status
        status_filter = "AND status = %(status)s"

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT id, market_ticker, condition_id, token_id, status, close_time, last_trade_time
            FROM pm_markets
            WHERE platform_id = %(platform_id)s
              AND condition_id IS NOT NULL
              AND token_id IS NOT NULL
              {status_filter}
            ORDER BY condition_id, token_id
            """,
            params,
        )
        return list(cur.fetchall())


def _filter_condition_groups_missing_candles(
    conn: psycopg.Connection,
    condition_groups: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Skip conditions where every stored token row already has at least one candle."""
    market_ids = [row["id"] for rows in condition_groups.values() for row in rows]
    if not market_ids:
        return {}

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

    filtered: dict[str, list[dict[str, Any]]] = {}
    for condition_id, rows in condition_groups.items():
        row_ids = {row["id"] for row in rows}
        if row_ids and row_ids.issubset(existing_ids):
            continue
        filtered[condition_id] = rows

    return filtered


def _group_markets_by_condition(
    market_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in market_rows:
        condition_id = row.get("condition_id")
        if not isinstance(condition_id, str) or not condition_id:
            continue
        grouped.setdefault(condition_id, []).append(row)
    return grouped


def backfill_candlesticks(
    conn: psycopg.Connection,
    *,
    status: str | None = None,
    missing_only: bool = True,
    trade_limit: int = 1000,
    max_pages_per_condition: int | None = None,
) -> dict[str, int]:
    """Fetch condition trades, derive token bars, and upsert `pm_candlesticks`.

    This is intentionally explicit/manual for now and does not run implicitly as
    part of metadata ingest.
    """
    client = PolymarketClient()
    platform_id = seed_polymarket_platform(conn)
    market_rows = _get_polymarket_markets_for_candles(
        conn,
        platform_id=platform_id,
        status=status,
    )
    condition_groups = _group_markets_by_condition(market_rows)
    if missing_only:
        condition_groups = _filter_condition_groups_missing_candles(
            conn, condition_groups
        )

    total_candles = 0
    total_markets = 0

    for condition_id, rows in condition_groups.items():
        trades = get_condition_trades(
            client,
            condition_id=condition_id,
            limit=trade_limit,
            max_pages=max_pages_per_condition,
        )
        if not trades:
            continue

        candles = []
        for row in rows:
            market_id = int(row["id"])
            token_id = str(row["token_id"])
            token_candles = aggregate_daily_candles(
                trades,
                market_id=market_id,
                token_id=token_id,
            )
            if token_candles:
                candles.extend(token_candles)
                total_markets += 1

        if not candles:
            continue

        total_candles += upsert_candlesticks(conn, candles)
        conn.commit()

    summary = {
        "platform_id": platform_id,
        "conditions": len(condition_groups),
        "markets": total_markets,
        "candlesticks": total_candles,
    }
    logger.info("Polymarket candlestick backfill complete: %s", summary)
    return summary


def backfill_with_candlesticks(
    conn: psycopg.Connection,
    *,
    metadata_max_pages: int | None = None,
    candle_status: str | None = None,
    missing_only: bool = True,
    trade_limit: int = 1000,
    max_pages_per_condition: int | None = None,
) -> dict[str, Any]:
    """Explicit higher-level Polymarket backfill workflow.

    This keeps metadata ingest and candle upserts separate by default, but
    provides a single manual entry point when you explicitly want both.
    """
    market_summary = backfill(conn, max_pages=metadata_max_pages)
    candle_summary = backfill_candlesticks(
        conn,
        status=candle_status,
        missing_only=missing_only,
        trade_limit=trade_limit,
        max_pages_per_condition=max_pages_per_condition,
    )
    summary = {
        "platform_id": market_summary.get("platform_id"),
        "markets": market_summary,
        "candlesticks": candle_summary,
    }
    logger.info("Polymarket combined backfill complete: %s", summary)
    return summary


def cleanup_stale_active_statuses(conn: psycopg.Connection) -> dict[str, int]:
    """Mark clearly stale Polymarket active rows as closed/settled.

    This targets rows already stored in TSDB where:
    - platform = polymarket
    - status = active
    - close_time is in the past

    If a result is already present, we mark the row as settled; otherwise
    it becomes closed.
    """
    platform_id = seed_polymarket_platform(conn)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM pm_markets
            WHERE platform_id = %(platform_id)s
              AND status = 'active'
              AND close_time IS NOT NULL
              AND close_time < NOW()
            """,
            {"platform_id": platform_id},
        )
        result = cur.fetchone() or {"count": 0}
        stale_count = int(result["count"])

        cur.execute(
            """
            UPDATE pm_markets
            SET status = CASE
                    WHEN result IS NOT NULL THEN 'settled'
                    ELSE 'closed'
                END,
                updated_at = NOW()
            WHERE platform_id = %(platform_id)s
              AND status = 'active'
              AND close_time IS NOT NULL
              AND close_time < NOW()
            """,
            {"platform_id": platform_id},
        )

    conn.commit()
    summary = {
        "platform_id": platform_id,
        "updated_markets": stale_count,
    }
    logger.info("Polymarket stale-status cleanup complete: %s", summary)
    return summary


parse_token_markets = parse_market_tokens
