"""Trade normalization and derived-bar helpers for Polymarket.

These helpers intentionally operate on the documented public Data API trades
endpoint (`market=<condition_id>` + `offset` pagination). Token-level bars are
derived client-side by filtering condition trades by `asset`/token id.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx

from lseg_toolkit.timeseries.prediction_markets.models import Candlestick
from lseg_toolkit.timeseries.prediction_markets.polymarket.client import (
    PolymarketClient,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolymarketTrade:
    """Normalized Polymarket trade row."""

    condition_id: str
    token_id: str
    price: float
    size: float
    timestamp: datetime
    side: str | None = None
    outcome_label: str | None = None
    transaction_hash: str | None = None


def parse_trade(raw: dict) -> PolymarketTrade:
    """Parse a public Polymarket trade payload into a normalized trade."""
    raw_ts = raw.get("timestamp")
    if isinstance(raw_ts, str) and raw_ts.isdigit():
        raw_ts = int(raw_ts)
    if isinstance(raw_ts, (int, float)):
        ts = datetime.fromtimestamp(raw_ts, tz=UTC)
    elif isinstance(raw_ts, str):
        ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
    else:
        raise ValueError(f"Unsupported trade timestamp: {raw_ts!r}")

    return PolymarketTrade(
        condition_id=str(raw["conditionId"]),
        token_id=str(raw["asset"]),
        price=float(raw["price"]),
        size=float(raw["size"]),
        timestamp=ts,
        side=str(raw["side"]) if raw.get("side") is not None else None,
        outcome_label=(
            str(raw["outcome"]) if raw.get("outcome") is not None else None
        ),
        transaction_hash=(
            str(raw["transactionHash"])
            if raw.get("transactionHash") is not None
            else None
        ),
    )


def get_condition_trades(
    client: PolymarketClient,
    *,
    condition_id: str,
    limit: int = 1000,
    max_pages: int | None = None,
    stop_before: datetime | None = None,
) -> list[PolymarketTrade]:
    """Fetch paginated condition trades using the documented `market` filter.

    Trades are returned newest-first by the API. This helper paginates using
    `offset` until exhaustion or until all remaining trades would be older than
    `stop_before`.
    """
    all_trades: list[PolymarketTrade] = []
    offset = 0
    pages = 0

    while True:
        try:
            raw_rows = client.get_trades(
                limit=limit,
                offset=offset,
                market=condition_id,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400 and offset > 0:
                logger.warning(
                    "Stopping Polymarket trade pagination for %s at offset=%d "
                    "after HTTP 400; treating as end-of-history",
                    condition_id,
                    offset,
                )
                break
            raise
        if not raw_rows:
            break

        parsed_rows = [parse_trade(row) for row in raw_rows]
        if stop_before is not None:
            parsed_rows = [row for row in parsed_rows if row.timestamp >= stop_before]

        all_trades.extend(parsed_rows)
        pages += 1

        if len(raw_rows) < limit or (max_pages is not None and pages >= max_pages):
            break

        if stop_before is not None and parsed_rows:
            oldest_in_page = min(row.timestamp for row in parsed_rows)
            if oldest_in_page < stop_before:
                break
        elif stop_before is not None and not parsed_rows:
            break

        offset += limit

    return all_trades


def get_last_trade_times_by_token(
    client: PolymarketClient,
    *,
    condition_id: str,
    token_ids: list[str],
    limit: int = 100,
    max_pages: int = 10,
) -> dict[str, datetime | None]:
    """Find the latest observed trade timestamp for each token under a condition.

    The public endpoint filters by condition, not by token/outcome, so we page
    through recent condition trades until we have seen each token or we hit the
    page limit.
    """
    remaining = set(token_ids)
    latest: dict[str, datetime | None] = dict.fromkeys(token_ids)

    offset = 0
    pages = 0
    while remaining and pages < max_pages:
        try:
            raw_rows = client.get_trades(
                limit=limit,
                offset=offset,
                market=condition_id,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400 and offset > 0:
                logger.warning(
                    "Stopping Polymarket latest-trade scan for %s at offset=%d "
                    "after HTTP 400; using partial token coverage",
                    condition_id,
                    offset,
                )
                break
            raise
        if not raw_rows:
            break

        for row in raw_rows:
            trade = parse_trade(row)
            if trade.token_id in remaining:
                latest[trade.token_id] = trade.timestamp
                remaining.remove(trade.token_id)

        pages += 1
        if len(raw_rows) < limit:
            break
        offset += limit

    return latest


def aggregate_daily_candles(
    trades: list[PolymarketTrade],
    *,
    market_id: int,
    token_id: str,
) -> list[Candlestick]:
    """Aggregate token-level trades into daily derived candlesticks.

    - Groups by UTC trade date.
    - Uses first/last trade for open/close.
    - Uses max/min trade price for high/low.
    - Uses size-weighted average price for `price_mean`.
    - Stores rounded total trade size in `volume` because the current shared
      `pm_candlesticks.volume` schema is integer-valued.
    """
    token_trades = [trade for trade in trades if trade.token_id == token_id]
    if not token_trades:
        return []

    token_trades.sort(
        key=lambda trade: (
            trade.timestamp,
            trade.transaction_hash or "",
        )
    )

    by_day: dict[date, list[PolymarketTrade]] = defaultdict(list)
    for trade in token_trades:
        by_day[trade.timestamp.date()].append(trade)

    candles: list[Candlestick] = []
    for day in sorted(by_day):
        day_trades = by_day[day]
        prices = [trade.price for trade in day_trades]
        sizes = [trade.size for trade in day_trades]
        total_size = sum(sizes)
        weighted_mean = (
            sum(price * size for price, size in zip(prices, sizes, strict=True))
            / total_size
            if total_size
            else None
        )

        candles.append(
            Candlestick(
                market_id=market_id,
                ts=datetime(day.year, day.month, day.day, tzinfo=UTC),
                price_open=day_trades[0].price,
                price_high=max(prices),
                price_low=min(prices),
                price_close=day_trades[-1].price,
                price_mean=weighted_mean,
                volume=int(round(total_size)),
            )
        )

    return candles
