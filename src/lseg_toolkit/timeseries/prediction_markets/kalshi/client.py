"""HTTP client for Kalshi public API (v2)."""

import logging
import time
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3  # Number of retries after initial attempt (4 total attempts max)
THROTTLE_INTERVAL = 0.06  # ~16 req/sec, under the 20/sec limit

_STATUS_ALIASES = {
    "active": "open",
    "open": "open",
    "closed": "closed",
    "settled": "settled",
}


class KalshiClient:
    """Client for Kalshi public market data API.

    No authentication required for read endpoints.
    Rate limited to 20 reads/sec (basic tier).
    """

    def __init__(self, base_url: str = KALSHI_BASE_URL) -> None:
        self.base_url = base_url
        self._last_request_time: float = 0.0

    def _throttle(self) -> None:
        """Enforce minimum interval between requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < THROTTLE_INTERVAL:
            time.sleep(THROTTLE_INTERVAL - elapsed)

    def _request(self, path: str, params: dict | None = None) -> dict:
        """Make a throttled GET request with retry on 429/5xx."""
        url = f"{self.base_url}{path}"

        for attempt in range(MAX_RETRIES):
            self._throttle()
            self._last_request_time = time.monotonic()

            resp = httpx.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 2**attempt
                logger.warning(
                    "Kalshi %s %s (attempt %d/%d), retrying in %ds",
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

        # Final attempt — let it raise
        self._throttle()
        self._last_request_time = time.monotonic()
        resp = httpx.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def list_markets(
        self,
        series_ticker: str,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """
        Fetch all markets for a series, handling pagination.

        Args:
            series_ticker: e.g. 'KXFED', 'KXFEDDECISION', 'KXRATECUTCOUNT'
            status: Optional filter: 'active', 'closed', 'settled'
            limit: Page size (max 200).

        Returns:
            List of market dicts from Kalshi API.
        """
        all_markets: list[dict] = []
        cursor: str | None = None

        while True:
            params: dict = {
                "series_ticker": series_ticker,
                "limit": limit,
            }
            if status:
                params["status"] = _STATUS_ALIASES.get(status, status)
            if cursor:
                params["cursor"] = cursor

            data = self._request("/markets", params=params)
            markets = data.get("markets", [])
            all_markets.extend(markets)

            cursor = data.get("cursor", "")
            if not cursor or not markets:
                break

        logger.info(
            "Fetched %d markets for %s (status=%s)",
            len(all_markets),
            series_ticker,
            status,
        )
        return all_markets

    def get_candlesticks(
        self,
        series_ticker: str,
        market_ticker: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        period_interval: int = 1440,
    ) -> list[dict]:
        """
        Fetch daily candlesticks for a market.

        Args:
            series_ticker: Parent series ticker.
            market_ticker: Market ticker.
            start_ts: Start unix timestamp. Defaults to 2021-07-01 (first KXFED market).
            end_ts: End unix timestamp. Defaults to now.
            period_interval: Candle interval in minutes. 1440 = daily.

        Returns:
            List of candlestick dicts from Kalshi API.
        """
        if start_ts is None:
            # 2021-07-01 00:00:00 UTC — before the first Kalshi Fed market
            start_ts = 1625097600
        if end_ts is None:
            end_ts = int(time.time())

        params = {
            "start_ts": start_ts,
            "end_ts": end_ts,
            "period_interval": period_interval,
        }

        data = self._request(
            f"/series/{series_ticker}/markets/{market_ticker}/candlesticks",
            params=params,
        )
        candles = data.get("candlesticks", [])

        if candles:
            logger.debug("Fetched %d candlesticks for %s", len(candles), market_ticker)
        return candles

    def get_trades(self, market_ticker: str, limit: int = 1) -> list[dict]:
        """Fetch recent trades for a market, newest first."""
        data = self._request(
            "/markets/trades",
            params={"ticker": market_ticker, "limit": limit},
        )
        trades = data.get("trades", [])
        if trades:
            logger.debug("Fetched %d trades for %s", len(trades), market_ticker)
        return trades

    def get_last_trade_time(self, market_ticker: str) -> datetime | None:
        """Fetch the most recent trade timestamp for a market, if any."""
        trades = self.get_trades(market_ticker=market_ticker, limit=1)
        if not trades:
            return None
        created_time = trades[0].get("created_time")
        if not created_time:
            return None
        return datetime.fromisoformat(created_time.replace("Z", "+00:00"))
