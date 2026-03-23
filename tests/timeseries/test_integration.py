"""
Integration tests for timeseries module.

These tests require LSEG Workspace to be running and connected.
They are skipped in CI using: pytest -m "not integration"

Run locally with: uv run pytest tests/timeseries/test_integration.py -v
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from lseg_toolkit.timeseries import get_client
from lseg_toolkit.timeseries.enums import AssetClass, Granularity
from lseg_toolkit.timeseries.fetch import (
    fetch_fras,
    fetch_futures,
    fetch_fx,
    fetch_ois,
    fetch_treasury_yields,
    resolve_ric,
)
from lseg_toolkit.timeseries.fed_funds import fetch_fed_funds_hourly


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


@pytest.fixture(scope="module")
def intraday_date_range():
    """Get a recent date range for intraday tests."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=7)
    return {"start": start, "end": end}


def assert_intraday_frame(df, required_columns: list[str]) -> None:
    """Assert basic intraday fetch invariants when data is available."""
    assert df.index.is_monotonic_increasing
    assert df.index.is_unique
    for col in required_columns:
        assert col in df.columns, f"Missing column: {col}"


def require_storage() -> None:
    """Skip storage-backed integration tests when TimescaleDB is unavailable."""
    from lseg_toolkit.timeseries.storage import get_connection

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as exc:  # pragma: no cover - live integration only
        pytest.skip(f"Storage not available for integration test: {exc}")


def load_stored_frame(
    symbol: str,
    start_date: date,
    end_date: date,
    granularity: Granularity,
):
    """Load stored data and instrument metadata for round-trip assertions."""
    from lseg_toolkit.timeseries.storage import (
        get_connection,
        get_instrument,
        load_timeseries,
    )

    with get_connection() as conn:
        instrument = get_instrument(conn, symbol)
        df = load_timeseries(
            conn,
            symbol,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )

    return instrument, df


def clear_stored_range(
    symbol: str,
    start_date: date,
    end_date: date,
    granularity: Granularity,
) -> None:
    """Delete existing rows for a symbol/date window to keep live tests repeatable."""
    from lseg_toolkit.timeseries.storage import get_connection

    table_by_shape = {
        "ohlcv": "timeseries_ohlcv",
        "quote": "timeseries_quote",
        "rate": "timeseries_rate",
        "bond": "timeseries_bond",
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, data_shape FROM instruments WHERE symbol = %s", [symbol]
            )
            instrument = cur.fetchone()
            if instrument is None:
                return

            table = table_by_shape.get(instrument["data_shape"])
            if table is None:
                return

            cur.execute(
                f"""
                DELETE FROM {table}
                WHERE instrument_id = %s
                  AND granularity = %s
                  AND ts >= %s
                  AND ts <= %s
                """,
                [
                    instrument["id"],
                    granularity.value,
                    datetime.combine(start_date, datetime.min.time(), tzinfo=UTC),
                    datetime.combine(end_date, datetime.max.time(), tzinfo=UTC),
                ],
            )
        conn.commit()


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
        assert "yield" in df.columns
        assert df["yield"].notna().all()

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
class TestFRAIntegration:
    """Integration tests for FRA data."""

    def test_fetch_usd_fra_1x4(self, short_date_range):
        """Fetch USD 1x4 FRA."""
        result = fetch_fras(
            "USD",
            ["1X4"],
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
        )

        assert "1X4" in result
        df = result["1X4"]
        assert not df.empty
        assert "bid" in df.columns
        assert "ask" in df.columns


@pytest.mark.integration
class TestIntradayIntegration:
    """Integration tests for intraday data."""

    def test_fetch_hourly_futures(self, intraday_date_range):
        """Fetch hourly Treasury futures data."""
        result = fetch_futures(
            ["ZN"],
            start_date=intraday_date_range["start"],
            end_date=intraday_date_range["end"],
            granularity=Granularity.HOURLY,
        )

        assert "ZN" in result
        df = result["ZN"]
        # Hourly data should have more rows than daily
        # (assuming market is open)
        if not df.empty:
            assert_intraday_frame(df, ["open", "high", "low", "close"])
            assert df["close"].notna().all()
            assert len(df) > 5  # Should have multiple bars per day

    def test_fetch_5min_fx(self, intraday_date_range):
        """Fetch 5-minute FX data."""
        result = fetch_fx(
            ["EURUSD"],
            start_date=intraday_date_range["start"],
            end_date=intraday_date_range["end"],
            granularity=Granularity.MINUTE_5,
        )

        # May not have data if market was closed
        assert "EURUSD" in result
        df = result["EURUSD"]
        if not df.empty:
            assert_intraday_frame(df, ["bid", "ask"])
            assert len(df) > 10

    def test_fetch_hourly_fed_funds_continuous(self, intraday_date_range):
        """Fetch hourly FFc1 data with session-date-aware labeling."""
        client = get_client()
        df = fetch_fed_funds_hourly(
            client,
            intraday_date_range["start"],
            intraday_date_range["end"],
            rank=1,
        )

        if not df.empty:
            assert_intraday_frame(
                df,
                ["bid", "ask", "mid", "close", "implied_rate", "session_date", "source_contract"],
            )
            assert df["source_contract"].str.startswith("FF").all()
            assert (df["implied_rate"] - (100.0 - df["mid"])).abs().max() < 1e-9


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
        """Test full extraction pipeline with storage.

        Note: This test requires a running TimescaleDB instance.
        Configure via TSDB_* environment variables.
        """
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        require_storage()

        config = TimeSeriesConfig(
            symbols=["ZN"],
            asset_class=AssetClass.BOND_FUTURES,
            start_date=date_range["start"],
            end_date=date_range["end"],
            granularity=Granularity.DAILY,
            parquet_dir=str(tmp_path / "parquet"),
            export_parquet=False,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0

    def test_full_intraday_futures_pipeline_round_trip(
        self, tmp_path, intraday_date_range
    ):
        """Hourly futures pipeline should persist and reload intraday OHLCV bars."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        require_storage()

        config = TimeSeriesConfig(
            symbols=["ZN"],
            asset_class=AssetClass.BOND_FUTURES,
            start_date=intraday_date_range["start"],
            end_date=intraday_date_range["end"],
            granularity=Granularity.HOURLY,
            parquet_dir=str(tmp_path / "parquet"),
            export_parquet=False,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0

        instrument, stored = load_stored_frame(
            "ZN",
            intraday_date_range["start"],
            intraday_date_range["end"],
            Granularity.HOURLY,
        )

        assert instrument is not None
        assert instrument["data_shape"] == "ohlcv"
        assert not stored.empty
        assert len(stored) == result.total_rows
        assert_intraday_frame(stored, ["open", "high", "low", "close"])

    def test_full_intraday_fx_pipeline_round_trip(
        self, tmp_path, intraday_date_range
    ):
        """5-minute FX pipeline should persist and reload quote-shaped intraday data."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        require_storage()

        config = TimeSeriesConfig(
            symbols=["EURUSD"],
            asset_class=AssetClass.FX_SPOT,
            start_date=intraday_date_range["start"],
            end_date=intraday_date_range["end"],
            granularity=Granularity.MINUTE_5,
            parquet_dir=str(tmp_path / "parquet"),
            export_parquet=False,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0

        instrument, stored = load_stored_frame(
            "EURUSD",
            intraday_date_range["start"],
            intraday_date_range["end"],
            Granularity.MINUTE_5,
        )

        assert instrument is not None
        assert instrument["data_shape"] == "quote"
        assert not stored.empty
        assert len(stored) == result.total_rows
        assert_intraday_frame(stored, ["bid", "ask", "mid"])

    def test_full_ois_pipeline_round_trip(self, tmp_path, short_date_range):
        """Daily USD OIS pipeline should persist and reload rate-shaped data."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        require_storage()

        config = TimeSeriesConfig(
            symbols=["1M"],
            asset_class=AssetClass.OIS,
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
            parquet_dir=str(tmp_path / "parquet"),
            export_parquet=False,
        )

        clear_stored_range(
            "USD1MOIS",
            short_date_range["start"],
            short_date_range["end"],
            Granularity.DAILY,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0

        instrument, stored = load_stored_frame(
            "USD1MOIS",
            short_date_range["start"],
            short_date_range["end"],
            Granularity.DAILY,
        )

        assert instrument is not None
        assert instrument["data_shape"] == "rate"
        assert not stored.empty
        assert len(stored) == result.total_rows
        assert "rate" in stored.columns
        assert stored["rate"].notna().all()

    def test_full_treasury_yield_pipeline_round_trip(
        self, tmp_path, short_date_range
    ):
        """Daily US Treasury yield pipeline should persist and reload bond-shaped data."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        require_storage()

        config = TimeSeriesConfig(
            symbols=["10Y"],
            asset_class=AssetClass.GOVT_YIELD,
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
            parquet_dir=str(tmp_path / "parquet"),
            export_parquet=False,
        )

        clear_stored_range(
            "US10YT",
            short_date_range["start"],
            short_date_range["end"],
            Granularity.DAILY,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0

        instrument, stored = load_stored_frame(
            "US10YT",
            short_date_range["start"],
            short_date_range["end"],
            Granularity.DAILY,
        )

        assert instrument is not None
        assert instrument["data_shape"] == "bond"
        assert not stored.empty
        assert len(stored) == result.total_rows
        assert "yield" in stored.columns
        assert stored["yield"].notna().all()

    def test_full_fra_pipeline_round_trip(self, tmp_path, short_date_range):
        """Daily FRA pipeline should persist and reload rate-shaped data."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        require_storage()

        config = TimeSeriesConfig(
            symbols=["1X4"],
            asset_class=AssetClass.FRA,
            start_date=short_date_range["start"],
            end_date=short_date_range["end"],
            granularity=Granularity.DAILY,
            parquet_dir=str(tmp_path / "parquet"),
            export_parquet=False,
        )

        clear_stored_range(
            "USD1X4F",
            short_date_range["start"],
            short_date_range["end"],
            Granularity.DAILY,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0

        instrument, stored = load_stored_frame(
            "USD1X4F",
            short_date_range["start"],
            short_date_range["end"],
            Granularity.DAILY,
        )

        assert instrument is not None
        assert instrument["data_shape"] == "rate"
        assert not stored.empty
        assert len(stored) == result.total_rows
        assert "bid" in stored.columns
        assert "ask" in stored.columns
        assert stored["bid"].notna().any()
        assert stored["ask"].notna().any()

    def test_full_intraday_fed_funds_pipeline_round_trip(
        self, tmp_path, intraday_date_range
    ):
        """Hourly FF continuous pipeline should round-trip storage metadata."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig
        from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

        require_storage()

        config = TimeSeriesConfig(
            symbols=["FF_CONTINUOUS"],
            asset_class=AssetClass.STIR_FUTURES,
            start_date=intraday_date_range["start"],
            end_date=intraday_date_range["end"],
            granularity=Granularity.HOURLY,
            parquet_dir=str(tmp_path / "parquet"),
            export_parquet=False,
        )

        pipeline = TimeSeriesExtractionPipeline(config, verbose=False)
        result = pipeline.run()

        assert result.success_count == 1
        assert result.total_rows > 0

        instrument, stored = load_stored_frame(
            "FF_CONTINUOUS",
            intraday_date_range["start"],
            intraday_date_range["end"],
            Granularity.HOURLY,
        )

        assert instrument is not None
        assert instrument["data_shape"] == "ohlcv"
        assert not stored.empty
        assert len(stored) == result.total_rows
        assert_intraday_frame(
            stored,
            [
                "bid",
                "ask",
                "mid",
                "close",
                "implied_rate",
                "session_date",
                "source_contract",
            ],
        )
        assert stored["session_date"].notna().all()
        assert stored["source_contract"].str.startswith("FF").all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
