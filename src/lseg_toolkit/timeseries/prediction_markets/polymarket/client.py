"""HTTP client for Polymarket public market-data endpoints."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

POLYMARKET_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
POLYMARKET_DATA_BASE_URL = "https://data-api.polymarket.com"
POLYMARKET_CLOB_BASE_URL = "https://clob.polymarket.com"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
THROTTLE_INTERVAL = 0.06
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jl-lseg-toolkit/0.1.0; +https://github.com/jlipworth/jl-lseg-toolkit)",
    "Accept": "application/json",
}


class PolymarketClient:
    """Client for Polymarket public read-only APIs."""

    def __init__(
        self,
        gamma_base_url: str = POLYMARKET_GAMMA_BASE_URL,
        data_base_url: str = POLYMARKET_DATA_BASE_URL,
        clob_base_url: str = POLYMARKET_CLOB_BASE_URL,
    ) -> None:
        self.gamma_base_url = gamma_base_url.rstrip("/")
        self.data_base_url = data_base_url.rstrip("/")
        self.clob_base_url = clob_base_url.rstrip("/")
        self._last_request_time: float = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < THROTTLE_INTERVAL:
            time.sleep(THROTTLE_INTERVAL - elapsed)

    def _request(
        self,
        *,
        base_url: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a throttled GET request with retry on 429/5xx."""
        url = f"{base_url}{path}"

        for attempt in range(MAX_RETRIES):
            self._throttle()
            self._last_request_time = time.monotonic()
            resp = httpx.get(
                url,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 2**attempt
                logger.warning(
                    "Polymarket %s %s (attempt %d/%d), retrying in %ds",
                    resp.status_code,
                    path,
                    attempt + 1,
                    MAX_RETRIES,
                    wait,
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.json()

        self._throttle()
        self._last_request_time = time.monotonic()
        resp = httpx.get(
            url,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def list_markets(
        self,
        *,
        limit: int = 100,
        closed: bool | None = None,
        active: bool | None = None,
        archived: bool | None = None,
        slug: str | None = None,
        tag_id: int | None = None,
        related_tags: bool | None = None,
        exclude_tag_id: int | None = None,
        order: str | None = None,
        ascending: bool | None = None,
        max_pages: int | None = None,
    ) -> list[dict]:
        """
        Fetch Polymarket Gamma markets, handling offset pagination.
        """
        all_markets: list[dict] = []
        offset = 0
        pages = 0

        while True:
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if closed is not None:
                params["closed"] = str(closed).lower()
            if active is not None:
                params["active"] = str(active).lower()
            if archived is not None:
                params["archived"] = str(archived).lower()
            if slug:
                params["slug"] = slug
            if tag_id is not None:
                params["tag_id"] = tag_id
            if related_tags is not None:
                params["related_tags"] = str(related_tags).lower()
            if exclude_tag_id is not None:
                params["exclude_tag_id"] = exclude_tag_id
            if order:
                params["order"] = order
            if ascending is not None:
                params["ascending"] = str(ascending).lower()

            data = self._request(
                base_url=self.gamma_base_url,
                path="/markets",
                params=params,
            )
            markets = data if isinstance(data, list) else data.get("data", [])
            if not markets:
                break

            all_markets.extend(markets)
            pages += 1
            if len(markets) < limit or (max_pages is not None and pages >= max_pages):
                break
            offset += limit

        logger.info("Fetched %d Polymarket markets", len(all_markets))
        return all_markets

    def list_events(
        self,
        *,
        limit: int = 100,
        closed: bool | None = None,
        active: bool | None = None,
        archived: bool | None = None,
        slug: str | None = None,
        tag_id: int | None = None,
        related_tags: bool | None = None,
        exclude_tag_id: int | None = None,
        order: str | None = None,
        ascending: bool | None = None,
        max_pages: int | None = None,
    ) -> list[dict]:
        """Fetch Polymarket Gamma events, handling offset pagination."""
        all_events: list[dict] = []
        offset = 0
        pages = 0

        while True:
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if closed is not None:
                params["closed"] = str(closed).lower()
            if active is not None:
                params["active"] = str(active).lower()
            if archived is not None:
                params["archived"] = str(archived).lower()
            if slug:
                params["slug"] = slug
            if tag_id is not None:
                params["tag_id"] = tag_id
            if related_tags is not None:
                params["related_tags"] = str(related_tags).lower()
            if exclude_tag_id is not None:
                params["exclude_tag_id"] = exclude_tag_id
            if order:
                params["order"] = order
            if ascending is not None:
                params["ascending"] = str(ascending).lower()

            data = self._request(
                base_url=self.gamma_base_url,
                path="/events",
                params=params,
            )
            events = data if isinstance(data, list) else data.get("data", [])
            if not events:
                break

            all_events.extend(events)
            pages += 1
            if len(events) < limit or (max_pages is not None and pages >= max_pages):
                break
            offset += limit

        logger.info("Fetched %d Polymarket events", len(all_events))
        return all_events

    def list_tags(
        self,
        *,
        limit: int = 100,
        max_pages: int | None = None,
    ) -> list[dict]:
        """Fetch Polymarket Gamma tags, handling offset pagination."""
        all_tags: list[dict] = []
        offset = 0
        pages = 0

        while True:
            data = self._request(
                base_url=self.gamma_base_url,
                path="/tags",
                params={"limit": limit, "offset": offset},
            )
            tags = data if isinstance(data, list) else data.get("data", [])
            if not tags:
                break

            all_tags.extend(tags)
            pages += 1
            if len(tags) < limit or (max_pages is not None and pages >= max_pages):
                break
            offset += limit

        logger.info("Fetched %d Polymarket tags", len(all_tags))
        return all_tags

    def search_public(
        self,
        query: str,
        *,
        limit_per_type: int = 10,
        search_tags: bool = True,
        search_profiles: bool = False,
    ) -> dict:
        """Search public Polymarket entities such as events and tags."""
        data = self._request(
            base_url=self.gamma_base_url,
            path="/public-search",
            params={
                "q": query,
                "limit_per_type": limit_per_type,
                "search_tags": str(search_tags).lower(),
                "search_profiles": str(search_profiles).lower(),
            },
        )
        return data if isinstance(data, dict) else {}

    def list_simplified_markets(
        self,
        *,
        next_cursor: str = "MA==",
        max_pages: int | None = None,
    ) -> list[dict]:
        """Fetch public CLOB simplified markets, handling cursor pagination."""
        all_markets: list[dict] = []
        cursor = next_cursor
        pages = 0

        while True:
            data = self._request(
                base_url=self.clob_base_url,
                path="/simplified-markets",
                params={"next_cursor": cursor},
            )
            markets = data.get("data", [])
            if not markets:
                break

            all_markets.extend(markets)
            pages += 1
            next_value = data.get("next_cursor")
            if (
                not next_value
                or next_value == cursor
                or (max_pages is not None and pages >= max_pages)
            ):
                break
            cursor = next_value

        logger.info("Fetched %d Polymarket simplified markets", len(all_markets))
        return all_markets

    def get_trades(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        market: str | list[str] | None = None,
        condition_id: str | None = None,
        event_slug: str | None = None,
        outcome: str | None = None,
        side: str | None = None,
        taker_only: bool = True,
    ) -> list[dict]:
        """Fetch recent public trades.

        Notes:
        - The publicly documented market filter is `market=<condition_id>` with
          optional offset pagination.
        - `condition_id` is kept as a compatibility alias for callers in this
          repo and is translated into the documented `market` parameter.
        - `event_slug` and `outcome` are accepted for backward compatibility
          with earlier code but are not sent because they are not part of the
          documented public query contract.
        """
        del event_slug, outcome

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        market_param = market or condition_id
        if isinstance(market_param, list):
            params["market"] = ",".join(str(value) for value in market_param)
        elif market_param:
            params["market"] = market_param
        if side:
            params["side"] = side
        params["takerOnly"] = str(taker_only).lower()

        data = self._request(
            base_url=self.data_base_url,
            path="/trades",
            params=params,
        )
        trades = data if isinstance(data, list) else data.get("data", [])
        logger.debug("Fetched %d Polymarket trades", len(trades))
        return trades

    def get_last_trade_time(
        self,
        *,
        condition_id: str | None = None,
        event_slug: str | None = None,
        outcome: str | None = None,
    ) -> datetime | None:
        """Fetch the timestamp of the most recent public trade, if any."""
        trades = self.get_trades(
            limit=1,
            offset=0,
            condition_id=condition_id,
            event_slug=event_slug,
            outcome=outcome,
        )
        if not trades:
            return None

        raw_ts = trades[0].get("timestamp")
        if raw_ts is None:
            return None

        if isinstance(raw_ts, str) and raw_ts.isdigit():
            raw_ts = int(raw_ts)

        if isinstance(raw_ts, (int, float)):
            return datetime.fromtimestamp(raw_ts, tz=UTC)

        if isinstance(raw_ts, str):
            return datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))

        return None
