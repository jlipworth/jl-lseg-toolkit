"""Tests for Kalshi data extractor/orchestrator."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.prediction_markets.kalshi.extractor import (
    SERIES_TICKERS,
    _fetch_candlesticks_for_markets,
    _filter_markets_missing_candlesticks,
    backfill,
    daily_refresh,
    link_fomc_meeting,
    parse_candlestick,
    parse_market,
)


class TestSeriesTickers:
    """Verify configured series."""

    def test_has_three_series(self):
        assert len(SERIES_TICKERS) == 3

    def test_includes_kxfed(self):
        assert "KXFED" in SERIES_TICKERS

    def test_includes_kxfeddecision(self):
        assert "KXFEDDECISION" in SERIES_TICKERS

    def test_includes_kxratecutcount(self):
        assert "KXRATECUTCOUNT" in SERIES_TICKERS


class TestParseMarket:
    """Tests for parsing Kalshi API market dicts to Market models."""

    def test_parse_kxfed_market(self):
        raw = {
            "ticker": "KXFED-26JAN-T4.50",
            "title": "Fed rate above 4.50%",
            "subtitle": "After Jan 2026 meeting",
            "status": "finalized",
            "result": "yes",
            "last_price_dollars": "0.9700",
            "volume_fp": "1000.00",
            "open_interest_fp": "0.00",
            "open_time": "2025-12-01T14:00:00Z",
            "close_time": "2026-01-29T18:55:00Z",
            "event_ticker": "KXFED-26JAN",
        }
        market = parse_market(raw, platform_id=1, series_id=5)

        assert market.market_ticker == "KXFED-26JAN-T4.50"
        assert market.platform_market_id == "KXFED-26JAN-T4.50"
        assert market.platform_id == 1
        assert market.series_id == 5
        assert market.strike_value == 4.50
        assert market.status == "settled"  # finalized → settled
        assert market.last_price == 0.97
        assert market.volume == 1000

    def test_parse_extracts_strike_from_ticker(self):
        """Should extract strike_value from ticker like T4.50."""
        raw = {
            "ticker": "KXFED-26JAN-T3.75",
            "title": "Test",
            "status": "open",
            "open_time": "2025-12-01T14:00:00Z",
            "close_time": "2026-01-29T18:55:00Z",
        }
        market = parse_market(raw, platform_id=1, series_id=1)
        assert market.strike_value == 3.75
        assert market.status == "active"

    def test_parse_no_strike_for_decision_market(self):
        """KXFEDDECISION markets don't have T-strike in ticker."""
        raw = {
            "ticker": "KXFEDDECISION-26JAN-H25",
            "title": "Hike 25bps",
            "status": "settled",
            "open_time": "2025-12-01T14:00:00Z",
            "close_time": "2026-01-29T18:55:00Z",
        }
        market = parse_market(raw, platform_id=1, series_id=2)
        assert market.strike_value is None


class TestParseCandlestick:
    """Tests for parsing Kalshi candlestick dicts."""

    def test_parse_candlestick(self):
        raw = {
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
        candle = parse_candlestick(raw, market_id=42)

        assert candle.market_id == 42
        assert candle.price_close == 0.97
        assert candle.price_mean == 0.96
        assert candle.yes_bid_close == 0.96
        assert candle.yes_ask_close == 0.98
        assert candle.volume == 150

    def test_parse_candlestick_timestamp(self):
        """end_period_ts should become a UTC datetime."""
        raw = {
            "end_period_ts": 1706140800,
            "price": {},
            "volume": 0,
            "open_interest": 0,
        }
        candle = parse_candlestick(raw, market_id=1)
        assert candle.ts.tzinfo == UTC


class TestLinkFOMCMeeting:
    """Tests for FOMC meeting linkage."""

    def test_links_by_close_time_date(self):
        """Should match close_time date to fomc_meetings.meeting_date."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 10}

        close_time = datetime(2026, 1, 29, 18, 55, 0, tzinfo=UTC)
        meeting_id = link_fomc_meeting(mock_conn, close_time)

        assert meeting_id == 10

    def test_returns_none_when_no_match(self):
        """Should return None for non-FOMC dates (e.g., Dec 31)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        close_time = datetime(2026, 12, 31, 23, 59, 0, tzinfo=UTC)
        meeting_id = link_fomc_meeting(mock_conn, close_time)

        assert meeting_id is None


class TestFetchCandlesticksForMarkets:
    """Tests for candlestick persistence orchestration."""

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.extractor.get_connection")
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.kalshi.extractor.upsert_candlesticks"
    )
    def test_uses_fresh_write_connection_per_market(
        self, mock_upsert_candlesticks, mock_get_connection
    ):
        mock_conn = MagicMock()
        mock_write_conn = MagicMock()
        mock_client = MagicMock()
        mock_client.get_candlesticks.return_value = [
            {
                "end_period_ts": 1706140800,
                "price": {"close": 0.97},
                "volume": 150,
                "open_interest": 500,
            }
        ]
        mock_upsert_candlesticks.return_value = 1
        mock_get_connection.return_value.__enter__ = MagicMock(return_value=mock_write_conn)
        mock_get_connection.return_value.__exit__ = MagicMock(return_value=False)

        count = _fetch_candlesticks_for_markets(
            mock_conn,
            mock_client,
            "KXFED",
            ["KXFED-26JAN-T4.50"],
            [42],
        )

        assert count == 1
        mock_upsert_candlesticks.assert_called_once()
        assert mock_upsert_candlesticks.call_args[0][0] is mock_write_conn


class TestFilterMarketsMissingCandlesticks:
    """Tests for resumable backfill filtering."""

    def test_filters_out_markets_with_existing_candles(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [{"market_id": 2}]

        tickers, ids = _filter_markets_missing_candlesticks(
            mock_conn,
            ["M1", "M2", "M3"],
            [1, 2, 3],
        )

        assert tickers == ["M1", "M3"]
        assert ids == [1, 3]


class TestBackfill:
    """Tests for the backfill orchestrator."""

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.extractor.sync_fomc_meetings")
    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.extractor.KalshiClient")
    def test_backfill_seeds_platform(self, mock_client_cls, mock_sync_fomc):
        """Backfill should seed the Kalshi platform first."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}

        mock_client = MagicMock()
        mock_client.list_markets.return_value = []
        mock_client_cls.return_value = mock_client

        backfill(mock_conn)

        mock_sync_fomc.assert_called_once_with(mock_conn)
        # Should have called seed_kalshi_platform (via SQL)
        calls = [str(c) for c in mock_cursor.execute.call_args_list]
        assert any("pm_platforms" in c for c in calls)


class TestDailyRefresh:
    """Tests for the daily refresh orchestrator."""

    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.extractor.sync_fomc_meetings")
    @patch("lseg_toolkit.timeseries.prediction_markets.kalshi.extractor.KalshiClient")
    def test_daily_refresh_fetches_active_markets(
        self, mock_client_cls, mock_sync_fomc
    ):
        """Daily refresh should fetch active (not settled) markets."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}

        mock_client = MagicMock()
        mock_client.list_markets.return_value = []
        mock_client_cls.return_value = mock_client

        daily_refresh(mock_conn)

        mock_sync_fomc.assert_called_once_with(mock_conn)
        # Every list_markets call should have status="active"
        for c in mock_client.list_markets.call_args_list:
            assert c.kwargs.get("status") == "active"
