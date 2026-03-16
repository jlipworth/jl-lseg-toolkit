"""Tests for prediction market Pydantic models."""

from datetime import UTC, datetime

from lseg_toolkit.timeseries.prediction_markets.models import (
    Candlestick,
    Market,
    Platform,
    Series,
)


class TestPlatformModel:
    """Tests for Platform model."""

    def test_create_kalshi_platform(self):
        """Should create a Kalshi platform with all fields."""
        p = Platform(
            name="kalshi",
            display_name="Kalshi",
            api_base_url="https://api.elections.kalshi.com/trade-api/v2",
            is_regulated=True,
            currency="USD",
        )
        assert p.name == "kalshi"
        assert p.is_regulated is True
        assert p.id is None

    def test_platform_defaults(self):
        """is_regulated and currency should have defaults."""
        p = Platform(
            name="test",
            display_name="Test",
            api_base_url="https://example.com",
        )
        assert p.is_regulated is False
        assert p.currency == "USD"


class TestSeriesModel:
    """Tests for Series model."""

    def test_create_kxfed_series(self):
        """Should create a KXFED series."""
        s = Series(
            platform_id=1,
            series_ticker="KXFED",
            title="Fed Funds Rate Target",
        )
        assert s.series_ticker == "KXFED"
        assert s.category == "economics"

    def test_series_default_category(self):
        """Default category should be 'economics'."""
        s = Series(platform_id=1, series_ticker="TEST", title="Test")
        assert s.category == "economics"


class TestMarketModel:
    """Tests for Market model."""

    def test_create_kxfed_market(self):
        """Should create a KXFED market with strike value."""
        m = Market(
            platform_id=1,
            market_ticker="KXFED-26JAN-T4.50",
            platform_market_id="abc-123",
            title="Fed rate above 4.50% after Jan 2026",
            strike_value=4.50,
            status="settled",
            result="yes",
        )
        assert m.market_ticker == "KXFED-26JAN-T4.50"
        assert m.strike_value == 4.50
        assert m.fomc_meeting_id is None

    def test_market_nullable_fields(self):
        """Optional fields should default to None."""
        m = Market(
            platform_id=1,
            market_ticker="TEST",
            platform_market_id="test-id",
            title="Test",
        )
        assert m.series_id is None
        assert m.event_ticker is None
        assert m.subtitle is None
        assert m.strike_value is None
        assert m.open_time is None
        assert m.close_time is None
        assert m.result is None
        assert m.last_price is None
        assert m.last_trade_time is None
        assert m.volume is None
        assert m.open_interest is None
        assert m.fomc_meeting_id is None

    def test_market_default_status(self):
        """Default status should be 'active'."""
        m = Market(
            platform_id=1,
            market_ticker="TEST",
            platform_market_id="test-id",
            title="Test",
        )
        assert m.status == "active"


class TestCandlestickModel:
    """Tests for Candlestick model."""

    def test_create_candlestick(self):
        """Should create a candlestick with all price fields."""
        ts = datetime(2025, 1, 28, 0, 0, 0, tzinfo=UTC)
        c = Candlestick(
            market_id=1,
            ts=ts,
            price_open=0.95,
            price_high=0.98,
            price_low=0.94,
            price_close=0.97,
            price_mean=0.96,
            yes_bid_close=0.96,
            yes_ask_close=0.98,
            volume=150,
            open_interest=500,
        )
        assert c.price_close == 0.97
        assert c.ts == ts

    def test_candlestick_minimal(self):
        """Should create with only required fields."""
        ts = datetime(2025, 1, 28, 0, 0, 0, tzinfo=UTC)
        c = Candlestick(market_id=1, ts=ts)
        assert c.price_open is None
        assert c.volume is None
