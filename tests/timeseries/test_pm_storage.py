"""Tests for prediction market storage operations."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from lseg_toolkit.timeseries.prediction_markets.models import (
    Candlestick,
    Market,
    Series,
)
from lseg_toolkit.timeseries.prediction_markets.storage import (
    get_markets_by_event,
    get_markets_by_series,
    get_platform_by_name,
    upsert_candlestick,
    upsert_candlesticks,
    upsert_market,
    upsert_series,
)


def _mock_conn():
    """Create a mock psycopg connection with cursor context manager."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


class TestUpsertSeries:
    """Tests for series upsert."""

    def test_upsert_returns_id(self):
        conn, cursor = _mock_conn()
        cursor.fetchone.return_value = {"id": 5}

        series = Series(
            platform_id=1,
            series_ticker="KXFED",
            title="Fed Funds Rate Target",
        )
        result = upsert_series(conn, series)

        assert result == 5
        sql = cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql

    def test_upsert_uses_platform_series_unique(self):
        """ON CONFLICT should target (platform_id, series_ticker)."""
        conn, cursor = _mock_conn()
        cursor.fetchone.return_value = {"id": 1}

        series = Series(platform_id=1, series_ticker="KXFED", title="Test")
        upsert_series(conn, series)

        sql = cursor.execute.call_args[0][0]
        assert "platform_id, series_ticker" in sql


class TestUpsertMarket:
    """Tests for market upsert."""

    def test_upsert_returns_id(self):
        conn, cursor = _mock_conn()
        cursor.fetchone.return_value = {"id": 42}

        market = Market(
            platform_id=1,
            market_ticker="KXFED-26JAN-T4.50",
            platform_market_id="abc-123",
            title="Fed rate above 4.50%",
            strike_value=4.50,
            status="settled",
        )
        result = upsert_market(conn, market)

        assert result == 42

    def test_upsert_includes_fomc_meeting_id(self):
        """Should include fomc_meeting_id in upsert."""
        conn, cursor = _mock_conn()
        cursor.fetchone.return_value = {"id": 1}

        market = Market(
            platform_id=1,
            market_ticker="TEST",
            platform_market_id="test",
            title="Test",
            fomc_meeting_id=10,
        )
        upsert_market(conn, market)

        params = cursor.execute.call_args[0][1]
        assert params["fomc_meeting_id"] == 10


class TestUpsertCandlestick:
    """Tests for candlestick upsert."""

    def test_upsert_single(self):
        conn, cursor = _mock_conn()
        ts = datetime(2025, 1, 28, 0, 0, 0, tzinfo=UTC)

        candle = Candlestick(
            market_id=1,
            ts=ts,
            price_open=0.95,
            price_close=0.97,
            volume=150,
        )
        upsert_candlestick(conn, candle)

        sql = cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql
        assert "market_id" in sql

    def test_upsert_batch(self):
        """upsert_candlesticks should handle multiple candles."""
        conn, cursor = _mock_conn()

        candles = [
            Candlestick(
                market_id=1,
                ts=datetime(2025, 1, d, tzinfo=UTC),
                price_close=0.95 + d * 0.01,
            )
            for d in range(1, 4)
        ]
        count = upsert_candlesticks(conn, candles)

        assert count == 3
        assert cursor.execute.call_count == 3


class TestQueryOperations:
    """Tests for query functions."""

    def test_get_platform_by_name(self):
        conn, cursor = _mock_conn()
        cursor.fetchone.return_value = {
            "id": 1,
            "name": "kalshi",
            "display_name": "Kalshi",
        }

        result = get_platform_by_name(conn, "kalshi")

        assert result["name"] == "kalshi"

    def test_get_markets_by_series(self):
        conn, cursor = _mock_conn()
        cursor.fetchall.return_value = [
            {"id": 1, "market_ticker": "KXFED-26JAN-T4.50"},
            {"id": 2, "market_ticker": "KXFED-26JAN-T4.25"},
        ]

        result = get_markets_by_series(conn, series_id=1)

        assert len(result) == 2

    def test_get_markets_by_series_with_status(self):
        conn, cursor = _mock_conn()
        cursor.fetchall.return_value = []

        get_markets_by_series(conn, series_id=1, status="settled")

        params = cursor.execute.call_args[0][1]
        assert params["status"] == "settled"

    def test_get_markets_by_event(self):
        conn, cursor = _mock_conn()
        cursor.fetchall.return_value = [
            {"id": 1, "market_ticker": "KXFED-26JAN-T4.50"},
        ]

        result = get_markets_by_event(conn, event_ticker="KXFED-26JAN")

        assert len(result) == 1
        params = cursor.execute.call_args[0][1]
        assert params["event_ticker"] == "KXFED-26JAN"
