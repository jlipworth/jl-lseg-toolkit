"""Tests for Polymarket public HTTP client."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.prediction_markets.polymarket.client import (
    PolymarketClient,
)


class TestPolymarketClientInit:
    def test_defaults(self):
        client = PolymarketClient()
        assert "gamma-api.polymarket.com" in client.gamma_base_url
        assert "data-api.polymarket.com" in client.data_base_url
        assert "clob.polymarket.com" in client.clob_base_url


class TestListMarkets:
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_list_markets(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [
            {
                "id": "1",
                "question": "Will X happen?",
                "conditionId": "cond-1",
                "slug": "will-x-happen",
                "active": True,
                "closed": False,
            }
        ]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        client = PolymarketClient()
        markets = client.list_markets(limit=10, closed=False, max_pages=1)

        assert len(markets) == 1
        assert markets[0]["conditionId"] == "cond-1"
        assert mock_get.call_args[1]["params"]["closed"] == "false"

    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_list_markets_paginates_by_offset(self, mock_get):
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = [{"id": "1"}, {"id": "2"}]
        page1.raise_for_status = MagicMock()

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = [{"id": "3"}]
        page2.raise_for_status = MagicMock()

        mock_get.side_effect = [page1, page2]

        client = PolymarketClient()
        markets = client.list_markets(limit=2)

        assert [m["id"] for m in markets] == ["1", "2", "3"]
        assert mock_get.call_args_list[1][1]["params"]["offset"] == 2


class TestListEvents:
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_list_events(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"id": "event-1", "slug": "fed-event"}]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        client = PolymarketClient()
        events = client.list_events(limit=10, max_pages=1)

        assert len(events) == 1
        assert events[0]["slug"] == "fed-event"

    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_list_events_passes_tag_filters(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"id": "event-1", "slug": "fed-event"}]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        client = PolymarketClient()
        client.list_events(
            limit=10,
            tag_id=159,
            related_tags=True,
            active=True,
            closed=False,
            order="volume",
            ascending=False,
            max_pages=1,
        )

        params = mock_get.call_args[1]["params"]
        assert params["tag_id"] == 159
        assert params["related_tags"] == "true"
        assert params["active"] == "true"
        assert params["closed"] == "false"
        assert params["order"] == "volume"
        assert params["ascending"] == "false"


class TestTagsAndSearch:
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_list_tags_paginates(self, mock_get):
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = [{"id": 1, "slug": "fed"}, {"id": 2, "slug": "fomc"}]
        page1.raise_for_status = MagicMock()

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = [{"id": 3, "slug": "macro"}]
        page2.raise_for_status = MagicMock()

        mock_get.side_effect = [page1, page2]

        client = PolymarketClient()
        tags = client.list_tags(limit=2)

        assert [tag["slug"] for tag in tags] == ["fed", "fomc", "macro"]
        assert mock_get.call_args_list[1][1]["params"]["offset"] == 2

    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_search_public(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "events": [{"slug": "fed-decision-in-april"}],
            "tags": [{"id": 159, "slug": "fed"}],
            "pagination": {"totalResults": 1},
        }
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        client = PolymarketClient()
        data = client.search_public("fed decision", limit_per_type=5)

        assert data["events"][0]["slug"] == "fed-decision-in-april"
        params = mock_get.call_args[1]["params"]
        assert params["q"] == "fed decision"
        assert params["limit_per_type"] == 5
        assert params["search_tags"] == "true"
        assert params["search_profiles"] == "false"


class TestListSimplifiedMarkets:
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_list_simplified_markets(self, mock_get):
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "data": [{"condition_id": "cond-1"}],
            "next_cursor": "NEXT",
        }
        page1.raise_for_status = MagicMock()

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "data": [{"condition_id": "cond-2"}],
            "next_cursor": "NEXT",
        }
        page2.raise_for_status = MagicMock()

        mock_get.side_effect = [page1, page2]

        client = PolymarketClient()
        markets = client.list_simplified_markets(max_pages=2)

        assert [m["condition_id"] for m in markets] == ["cond-1", "cond-2"]


class TestTrades:
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_get_trades(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [
            {
                "conditionId": "cond-1",
                "eventSlug": "fed-event",
                "outcome": "Yes",
                "timestamp": 1774133887,
            }
        ]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        client = PolymarketClient()
        trades = client.get_trades(condition_id="cond-1", outcome="Yes")

        assert len(trades) == 1
        params = mock_get.call_args[1]["params"]
        assert params["conditionId"] == "cond-1"
        assert params["outcome"] == "Yes"

    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_get_last_trade_time_from_unix_timestamp(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"timestamp": 1774133887}]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        client = PolymarketClient()
        ts = client.get_last_trade_time(condition_id="cond-1")

        assert ts == datetime.fromtimestamp(1774133887, tz=UTC)

    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_get_last_trade_time_none_when_no_trades(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        client = PolymarketClient()
        assert client.get_last_trade_time(condition_id="cond-1") is None


class TestRetryBehavior:
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.time.sleep")
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.client.httpx.get")
    def test_retries_on_429(self, mock_get, mock_sleep):
        error_resp = MagicMock()
        error_resp.status_code = 429

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = []
        ok_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [error_resp, ok_resp]

        client = PolymarketClient()
        markets = client.list_markets(max_pages=1)

        assert markets == []
        mock_sleep.assert_any_call(1)
