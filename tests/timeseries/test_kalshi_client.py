"""Tests for Kalshi HTTP client."""

from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.prediction_markets.kalshi.client import KalshiClient


class TestKalshiClientInit:
    """Tests for client initialization."""

    def test_default_base_url(self):
        client = KalshiClient()
        assert "kalshi" in client.base_url

    def test_custom_base_url(self):
        client = KalshiClient(base_url="https://custom.api.com")
        assert client.base_url == "https://custom.api.com"


class TestListMarkets:
    """Tests for list_markets method."""

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.httpx.get")
    def test_list_markets_by_series(self, mock_get):
        """Should fetch markets filtered by series_ticker."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "markets": [
                {
                    "ticker": "KXFED-26JAN-T4.50",
                    "title": "Fed rate above 4.50%",
                    "subtitle": "After Jan 2026 meeting",
                    "status": "settled",
                    "result": "yes",
                    "last_price": 0.97,
                    "volume": 1000,
                    "open_interest": 0,
                    "open_time": "2025-12-01T14:00:00Z",
                    "close_time": "2026-01-29T18:55:00Z",
                    "event_ticker": "KXFED-26JAN",
                    "series_ticker": "KXFED",
                }
            ],
            "cursor": "",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = KalshiClient()
        markets = client.list_markets(series_ticker="KXFED", status="settled")

        assert len(markets) == 1
        assert markets[0]["ticker"] == "KXFED-26JAN-T4.50"
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["series_ticker"] == "KXFED"

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.httpx.get")
    def test_list_markets_paginates(self, mock_get):
        """Should follow cursor for paginated results."""
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "markets": [{"ticker": "M1"}],
            "cursor": "next_page",
        }
        page1.raise_for_status = MagicMock()

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "markets": [{"ticker": "M2"}],
            "cursor": "",
        }
        page2.raise_for_status = MagicMock()

        mock_get.side_effect = [page1, page2]

        client = KalshiClient()
        markets = client.list_markets(series_ticker="KXFED")

        assert len(markets) == 2
        assert mock_get.call_count == 2

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.httpx.get")
    def test_list_markets_maps_active_to_open(self, mock_get):
        """Client should translate legacy active filter to current API open filter."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"markets": [], "cursor": ""}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = KalshiClient()
        client.list_markets(series_ticker="KXFED", status="active")

        assert mock_get.call_args[1]["params"]["status"] == "open"


class TestGetCandlesticks:
    """Tests for get_candlesticks method."""

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.httpx.get")
    def test_get_candlesticks(self, mock_get):
        """Should fetch candlesticks with start/end timestamps."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candlesticks": [
                {
                    "end_period_ts": 1706140800,
                    "price": {
                        "open": 0.95,
                        "high": 0.98,
                        "low": 0.94,
                        "close": 0.97,
                        "mean": 0.96,
                    },
                    "yes_bid": {"close": 0.96},
                    "yes_ask": {"close": 0.98},
                    "volume": 150,
                    "open_interest": 500,
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = KalshiClient()
        candles = client.get_candlesticks(
            series_ticker="KXFED",
            market_ticker="KXFED-26JAN-T4.50",
        )

        assert len(candles) == 1
        assert candles[0]["price"]["close"] == 0.97

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.httpx.get")
    def test_get_candlesticks_empty(self, mock_get):
        """Should return empty list for markets with no trades."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"candlesticks": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client = KalshiClient()
        candles = client.get_candlesticks(
            series_ticker="KXFED",
            market_ticker="KXFED-26JAN-T3.00",
        )

        assert candles == []


class TestRetryBehavior:
    """Tests for retry on 429/5xx."""

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.time.sleep")
    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.httpx.get")
    def test_retries_on_429(self, mock_get, mock_sleep):
        """Should retry on 429 with exponential backoff."""
        error_resp = MagicMock()
        error_resp.status_code = 429

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"candlesticks": []}
        ok_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [error_resp, ok_resp]

        client = KalshiClient()
        candles = client.get_candlesticks("KXFED", "M1")

        assert candles == []
        assert mock_get.call_count == 2
        # Verify exponential backoff was used (2**0 = 1 second for first retry)
        mock_sleep.assert_any_call(1)

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.time.sleep")
    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.client.httpx.get")
    def test_retries_on_500(self, mock_get, mock_sleep):
        """Should retry on 5xx server errors."""
        error_resp = MagicMock()
        error_resp.status_code = 502

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"markets": [], "cursor": ""}
        ok_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [error_resp, ok_resp]

        client = KalshiClient()
        markets = client.list_markets(series_ticker="KXFED")

        assert markets == []
        assert mock_get.call_count == 2
