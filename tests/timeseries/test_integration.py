"""
Integration tests for timeseries module.

These tests require LSEG Workspace to be running and connected.
They are skipped in CI using: pytest -m "not integration"

Run locally with: uv run pytest tests/timeseries/test_integration.py -v
"""

from datetime import date, timedelta

import pytest

from lseg_toolkit.timeseries.enums import AssetClass, Granularity
from lseg_toolkit.timeseries.fetch import (
    fetch_futures,
    fetch_fx,
    fetch_ois,
    fetch_treasury_yields,
    resolve_ric,
)


@pytest.fixture(scope="module")
def date_range():
    """Get a recent date range for testing."""
    end = date.today() - timedelta(days=1)  # Yesterday
    start = end - timedelta(days=30)  # 30 days of data
    return {"start": start, "end": end}


@pytest.fixture(scope="module")
def short_date_range():
    """Get a short date range for quick tests."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=5)  # 5 days of data
    return {"start": start, "end": end}


@pytest.mark.integration
class TestBondFuturesIntegration:
    """Integration tests for bond futures data."""

    def test_fetch_10y_treasury_futures(self, short_date_range):
        """Fetch 10-Year Treasury Note futures (ZN/TYc1)."""
        result = fetch_futures(
            ["ZN"],
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
        )

        assert "ZN" in result
        df = result["ZN"]
        assert not df.empty
        assert len(df) > 0

        # Check expected columns exist
        expected_cols = ["open", "high", "low", "close"]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_fetch_30y_treasury_futures(self, short_date_range):
        """Fetch 30-Year Treasury Bond futures (ZB/USc1)."""
        result = fetch_futures(
            ["ZB"],
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
        )

        assert "ZB" in result
        df = result["ZB"]
        assert not df.empty

    def test_fetch_multiple_futures(self, short_date_range):
        """Fetch multiple Treasury futures in single batch."""
        symbols = ["ZN", "ZB", "ZF"]

        result = fetch_futures(
            symbols,
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
        )

        # All symbols should be present
        for sym in symbols:
            assert sym in result, f"Missing symbol: {sym}"
            assert not result[sym].empty

    def test_fetch_euro_bund_futures(self, short_date_range):
        """Fetch Euro-Bund futures (FGBL)."""
        result = fetch_futures(
            ["FGBLc1"],  # Direct RIC
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
        )

        assert "FGBLc1" in result
        assert not result["FGBLc1"].empty


@pytest.mark.integration
class TestFXIntegration:
    """Integration tests for FX spot data."""

    def test_fetch_eurusd(self, short_date_range):
        """Fetch EUR/USD spot rate."""
        result = fetch_fx(
            ["EURUSD"],
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
        )

        assert "EURUSD" in result
        df = result["EURUSD"]
        assert not df.empty

        # FX should have bid/ask
        assert "bid" in df.columns or "close" in df.columns

    def test_fetch_multiple_fx_pairs(self, short_date_range):
        """Fetch multiple FX pairs."""
        pairs = ["EURUSD", "USDJPY", "GBPUSD"]

        result = fetch_fx(
            pairs,
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
        )

        for pair in pairs:
            assert pair in result, f"Missing pair: {pair}"


@pytest.mark.integration
class TestOISIntegration:
    """Integration tests for OIS curve data."""

    def test_fetch_usd_ois_1m(self, short_date_range):
        """Fetch USD 1-month OIS rate."""
        result = fetch_ois(
            "USD",
            ["1M"],
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
        )

        assert "1M" in result
        assert not result["1M"].empty

    def test_fetch_usd_ois_curve(self, short_date_range):
        """Fetch full USD OIS curve."""
        tenors = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"]

        result = fetch_ois(
            "USD",
            tenors,
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
        )

        # Not all tenors may have data, but at least some should
        assert len(result) > 0


@pytest.mark.integration
class TestTreasuryYieldsIntegration:
    """Integration tests for Treasury yield curve."""

    def test_fetch_10y_yield(self, short_date_range):
        """Fetch US 10-Year Treasury yield."""
        result = fetch_treasury_yields(
            ["10Y"],
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
        )

        assert "10Y" in result
        df = result["10Y"]
        assert not df.empty

    def test_fetch_yield_curve(self, short_date_range):
        """Fetch full yield curve."""
        tenors = ["2Y", "5Y", "10Y", "30Y"]

        result = fetch_treasury_yields(
            tenors,
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
        )

        assert len(result) > 0


@pytest.mark.integration
class TestIntradayIntegration:
    """Integration tests for intraday data."""

    def test_fetch_hourly_futures(self):
        """Fetch hourly Treasury futures data."""
        # Use very recent data for intraday (last 5 days)
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=5)

        result = fetch_futures(
            ["ZN"],
            start_date=start,
            end_date=end,
            granularity=Granularity.HOURLY,
        )

        assert "ZN" in result
        df = result["ZN"]
        # Hourly data should have more rows than daily
        # (assuming market is open)
        if not df.empty:
            assert len(df) > 5  # Should have multiple bars per day

    def test_fetch_5min_fx(self):
        """Fetch 5-minute FX data."""
        # Use very recent data for intraday
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=2)

        result = fetch_fx(
            ["EURUSD"],
            start_date=start,
            end_date=end,
            granularity=Granularity.MINUTE_5,
        )

        # May not have data if market was closed
        assert "EURUSD" in result


@pytest.mark.integration
class TestResolveRicIntegration:
    """Integration tests for RIC resolution."""

    def test_resolve_and_fetch(self, short_date_range):
        """Verify resolved RIC can be fetched."""
        # Resolve ZN to TYc1
        ric = resolve_ric("ZN")
        assert ric == "TYc1"

        # Now fetch using resolved RIC directly
        result = fetch_futures(
            [ric],
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
        )

        assert ric in result
        assert not result[ric].empty


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_full_extraction_pipeline(self, tmp_path, date_range):
        """Test full extraction pipeline with storage."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        db_path = str(tmp_path / "test.duckdb")

        config = TimeSeriesConfig(
            symbols=["ZN"],
            asset_class=AssetClass.BOND_FUTURES,
            start_date=date_range["start"],
            end_date=date_range["end"],
            granularity=Granularity.DAILY,
            db_path=db_path,
            export_parquet=False,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
