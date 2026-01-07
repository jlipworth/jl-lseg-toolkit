"""Tests for async cache layer."""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from lseg_toolkit.timeseries.cache import (
    CacheConfig,
    DataCache,
    DateGap,
    FetchResult,
    FetchStatus,
    InstrumentNotFoundError,
    InstrumentRegistry,
    detect_gaps,
    get_registry,
)
from lseg_toolkit.timeseries.duckdb_storage import (
    get_connection,
    save_instrument,
    save_timeseries,
)
from lseg_toolkit.timeseries.enums import AssetClass, Granularity


class TestInstrumentRegistry:
    """Tests for InstrumentRegistry."""

    def test_validates_known_futures(self):
        """Test that known futures symbols are valid."""
        registry = InstrumentRegistry()

        # CME symbols
        assert registry.is_valid("ZN")
        assert registry.is_valid("ZB")
        assert registry.is_valid("ES")

        # LSEG continuous contracts
        assert registry.is_valid("TYc1")
        assert registry.is_valid("USc1")
        assert registry.is_valid("ESc1")

    def test_validates_fx_spot(self):
        """Test that FX spot symbols are valid."""
        registry = InstrumentRegistry()

        assert registry.is_valid("EURUSD")
        assert registry.is_valid("EUR=")
        assert registry.is_valid("GBPUSD")
        assert registry.is_valid("GBP=")

    def test_validates_ois_rates(self):
        """Test that OIS rate RICs are valid."""
        registry = InstrumentRegistry()

        assert registry.is_valid("USD1MOIS=")
        assert registry.is_valid("USD10YOIS=")
        assert registry.is_valid("EUR3MOIS=")
        assert registry.is_valid("GBP1YOIS=")

    def test_validates_irs_rates(self):
        """Test that IRS rate RICs are valid."""
        registry = InstrumentRegistry()

        assert registry.is_valid("EURIRS5Y=")
        assert registry.is_valid("USDIRS10Y=")
        assert registry.is_valid("GBPSB6L5Y=")  # GBP IRS pattern

    def test_validates_govt_yields(self):
        """Test that government yield RICs are valid."""
        registry = InstrumentRegistry()

        assert registry.is_valid("US10YT=RR")
        assert registry.is_valid("US10YT=RRPS")
        assert registry.is_valid("DE10YT=RR")
        assert registry.is_valid("GB10YT=RR")

    def test_rejects_unknown_ric(self):
        """Test that unknown RICs are rejected."""
        registry = InstrumentRegistry()

        assert not registry.is_valid("INVALID_XYZ")
        assert not registry.is_valid("RANDOM123=")
        assert not registry.is_valid("NOTREAL")

    def test_validate_raises_for_unknown(self):
        """Test that validate() raises InstrumentNotFoundError."""
        registry = InstrumentRegistry()

        with pytest.raises(InstrumentNotFoundError):
            registry.validate("INVALID_XYZ")

    def test_get_asset_class_futures(self):
        """Test asset class inference for futures."""
        registry = InstrumentRegistry()

        assert registry.get_asset_class("ZN") == AssetClass.BOND_FUTURES
        assert registry.get_asset_class("TYc1") == AssetClass.BOND_FUTURES
        assert registry.get_asset_class("ES") == AssetClass.INDEX_FUTURES

    def test_get_asset_class_fx(self):
        """Test asset class inference for FX."""
        registry = InstrumentRegistry()

        assert registry.get_asset_class("EUR=") == AssetClass.FX_SPOT
        assert registry.get_asset_class("EURUSD") == AssetClass.FX_SPOT

    def test_get_asset_class_rates(self):
        """Test asset class inference for rates."""
        registry = InstrumentRegistry()

        assert registry.get_asset_class("USD1MOIS=") == AssetClass.OIS
        assert registry.get_asset_class("EURIRS5Y=") == AssetClass.IRS
        assert registry.get_asset_class("USD3X6F=") == AssetClass.FRA

    def test_singleton_registry(self):
        """Test that get_registry returns singleton."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2


class TestDateGap:
    """Tests for DateGap dataclass."""

    def test_days_property(self):
        """Test days calculation."""
        gap = DateGap(start=date(2024, 1, 1), end=date(2024, 1, 10))
        assert gap.days == 10

    def test_single_day_gap(self):
        """Test single day gap."""
        gap = DateGap(start=date(2024, 1, 1), end=date(2024, 1, 1))
        assert gap.days == 1


class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_success_properties(self):
        """Test success property."""
        result = FetchResult(ric="TYc1", status=FetchStatus.SUCCESS)
        assert result.success

        result = FetchResult(ric="TYc1", status=FetchStatus.FROM_CACHE)
        assert result.success

        result = FetchResult(ric="TYc1", status=FetchStatus.PARTIAL)
        assert result.success

    def test_failed_not_success(self):
        """Test failed status is not success."""
        result = FetchResult(ric="TYc1", status=FetchStatus.FAILED)
        assert not result.success

        result = FetchResult(ric="TYc1", status=FetchStatus.NOT_FOUND)
        assert not result.success

    def test_total_rows(self):
        """Test total_rows calculation."""
        result = FetchResult(
            ric="TYc1",
            status=FetchStatus.PARTIAL,
            rows_fetched=100,
            rows_from_cache=200,
        )
        assert result.total_rows == 300


class TestGapDetection:
    """Tests for gap detection logic."""

    def test_detects_full_gap_when_no_data(self):
        """Test full gap returned when no data exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with get_connection(str(db_path)) as conn:
                # Create instrument but no data
                save_instrument(
                    conn,
                    symbol="TYc1",
                    name="10Y Treasury Futures",
                    asset_class=AssetClass.BOND_FUTURES,
                    lseg_ric="TYc1",
                )

                gaps = detect_gaps(
                    conn,
                    symbol="TYc1",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    granularity=Granularity.DAILY,
                )

                assert len(gaps) == 1
                assert gaps[0].start == date(2024, 1, 1)
                assert gaps[0].end == date(2024, 12, 31)

    def test_granularity_isolation(self):
        """Test that daily data doesn't satisfy 5min request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with get_connection(str(db_path)) as conn:
                # Create instrument
                instr_id = save_instrument(
                    conn,
                    symbol="TYc1",
                    name="10Y Treasury Futures",
                    asset_class=AssetClass.BOND_FUTURES,
                    lseg_ric="TYc1",
                )

                # Save DAILY data
                df = pd.DataFrame(
                    {
                        "close": [110.0, 111.0, 112.0],
                    },
                    index=pd.date_range("2024-06-01", periods=3, freq="D"),
                )
                save_timeseries(conn, instr_id, df, Granularity.DAILY)

                # Request 5MIN data - should have full gap
                gaps = detect_gaps(
                    conn,
                    symbol="TYc1",
                    start_date=date(2024, 6, 1),
                    end_date=date(2024, 6, 3),
                    granularity=Granularity.MINUTE_5,
                )

                # Daily data doesn't satisfy 5min request
                assert len(gaps) == 1
                assert gaps[0].start == date(2024, 6, 1)
                assert gaps[0].end == date(2024, 6, 3)

    def test_no_gaps_when_fully_covered(self):
        """Test no gaps when data fully covers range."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with get_connection(str(db_path)) as conn:
                # Create instrument
                instr_id = save_instrument(
                    conn,
                    symbol="TYc1",
                    name="10Y Treasury Futures",
                    asset_class=AssetClass.BOND_FUTURES,
                    lseg_ric="TYc1",
                )

                # Save data covering full range (use float values)
                df = pd.DataFrame(
                    {
                        "close": [100.0 + i for i in range(100)],
                    },
                    index=pd.date_range("2024-01-01", periods=100, freq="D"),
                )
                save_timeseries(conn, instr_id, df, Granularity.DAILY)

                # Request within stored range
                gaps = detect_gaps(
                    conn,
                    symbol="TYc1",
                    start_date=date(2024, 2, 1),
                    end_date=date(2024, 3, 1),
                    granularity=Granularity.DAILY,
                )

                assert len(gaps) == 0

    def test_detects_gap_at_start(self):
        """Test gap detection when request starts before stored data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with get_connection(str(db_path)) as conn:
                # Create instrument
                instr_id = save_instrument(
                    conn,
                    symbol="TYc1",
                    name="10Y Treasury Futures",
                    asset_class=AssetClass.BOND_FUTURES,
                    lseg_ric="TYc1",
                )

                # Save data starting from Feb (use float values)
                df = pd.DataFrame(
                    {
                        "close": [100.0 + i for i in range(100)],
                    },
                    index=pd.date_range("2024-02-01", periods=100, freq="D"),
                )
                save_timeseries(conn, instr_id, df, Granularity.DAILY)

                # Request starting from Jan
                gaps = detect_gaps(
                    conn,
                    symbol="TYc1",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 3, 1),
                    granularity=Granularity.DAILY,
                )

                # Should have gap from Jan 1 to Jan 31 (one day before stored data)
                assert len(gaps) == 1
                assert gaps[0].start == date(2024, 1, 1)
                assert gaps[0].end == date(
                    2024, 1, 31
                )  # Fixed: no overlap with stored data


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CacheConfig()

        assert config.max_concurrent_fetches == 5
        assert config.executor_workers == 4
        assert config.validate_instruments is True
        assert config.auto_register_instruments is True

    def test_custom_values(self):
        """Test custom configuration."""
        config = CacheConfig(
            max_concurrent_fetches=10,
            executor_workers=8,
            validate_instruments=False,
        )

        assert config.max_concurrent_fetches == 10
        assert config.executor_workers == 8
        assert config.validate_instruments is False


class TestDataCache:
    """Tests for DataCache class."""

    def test_init_with_defaults(self):
        """Test cache initialization with defaults."""
        cache = DataCache()
        assert cache.config is not None
        assert cache.client is not None
        assert cache.registry is not None
        cache.close()

    def test_init_with_custom_config(self):
        """Test cache initialization with custom config."""
        config = CacheConfig(max_concurrent_fetches=10)
        cache = DataCache(config=config)
        assert cache.config.max_concurrent_fetches == 10
        cache.close()

    def test_context_manager(self):
        """Test cache as context manager."""
        with DataCache() as cache:
            assert cache is not None

    def test_rejects_unknown_instrument(self):
        """Test that unknown instruments are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            config = CacheConfig(db_path=str(db_path))

            with DataCache(config=config) as cache:
                with pytest.raises(InstrumentNotFoundError):
                    cache.get_or_fetch(
                        "INVALID_XYZ",
                        start="2024-01-01",
                        end="2024-12-31",
                    )

    def test_allows_known_instrument(self):
        """Test that known instruments pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            config = CacheConfig(db_path=str(db_path))

            # Mock the client to avoid actual LSEG calls
            mock_client = MagicMock()
            mock_client.get_history.return_value = pd.DataFrame(
                {"close": [110.0]},
                index=pd.date_range("2024-01-01", periods=1),
            )

            with DataCache(config=config, client=mock_client) as cache:
                # Should not raise
                df = cache.get_or_fetch(
                    "TYc1",
                    start="2024-01-01",
                    end="2024-01-02",
                )
                assert not df.empty

    def test_returns_cached_data(self):
        """Test that cached data is returned without fetching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            config = CacheConfig(db_path=str(db_path))

            # Pre-populate cache
            with get_connection(str(db_path)) as conn:
                instr_id = save_instrument(
                    conn,
                    symbol="TYc1",
                    name="10Y Treasury Futures",
                    asset_class=AssetClass.BOND_FUTURES,
                    lseg_ric="TYc1",
                )
                df = pd.DataFrame(
                    {"close": [110.0, 111.0, 112.0]},
                    index=pd.date_range("2024-01-01", periods=3, freq="D"),
                )
                save_timeseries(conn, instr_id, df, Granularity.DAILY)

            # Mock client should not be called
            mock_client = MagicMock()

            with DataCache(config=config, client=mock_client) as cache:
                result = cache.get_or_fetch(
                    "TYc1",
                    start="2024-01-01",
                    end="2024-01-03",
                )
                assert len(result) == 3
                # Client should not have been called
                mock_client.get_history.assert_not_called()

    def test_get_or_fetch_many(self):
        """Test batch fetching multiple RICs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            config = CacheConfig(db_path=str(db_path))

            mock_client = MagicMock()
            mock_client.get_history.return_value = pd.DataFrame(
                {"close": [110.0]},
                index=pd.date_range("2024-01-01", periods=1),
            )

            with DataCache(config=config, client=mock_client) as cache:
                results = cache.get_or_fetch_many(
                    ["TYc1", "USc1"],
                    start="2024-01-01",
                    end="2024-01-02",
                )
                assert "TYc1" in results
                assert "USc1" in results


class TestAsyncCache:
    """Tests for async cache methods."""

    def test_async_get_or_fetch(self):
        """Test async single RIC fetch."""
        import asyncio

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test.duckdb"
                config = CacheConfig(db_path=str(db_path))

                mock_client = MagicMock()
                mock_client.get_history.return_value = pd.DataFrame(
                    {"close": [110.0]},
                    index=pd.date_range("2024-01-01", periods=1),
                )

                cache = DataCache(config=config, client=mock_client)
                try:
                    df = await cache.async_get_or_fetch(
                        "TYc1",
                        start="2024-01-01",
                        end="2024-01-02",
                    )
                    assert not df.empty
                finally:
                    cache.close()

        asyncio.run(run_test())

    def test_async_get_or_fetch_many(self):
        """Test async batch fetch."""
        import asyncio

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test.duckdb"
                # Use max_concurrent_fetches=1 to avoid DuckDB write conflicts
                config = CacheConfig(db_path=str(db_path), max_concurrent_fetches=1)

                mock_client = MagicMock()
                mock_client.get_history.return_value = pd.DataFrame(
                    {"close": [110.0]},
                    index=pd.date_range("2024-01-01", periods=1),
                )

                cache = DataCache(config=config, client=mock_client)
                try:
                    results = await cache.async_get_or_fetch_many(
                        ["TYc1", "USc1", "FVc1"],
                        start="2024-01-01",
                        end="2024-01-02",
                    )
                    assert len(results) == 3
                    assert "TYc1" in results
                    assert "USc1" in results
                    assert "FVc1" in results
                finally:
                    cache.close()

        asyncio.run(run_test())

    def test_async_iter_fetch(self):
        """Test async iterator for fetch results."""
        import asyncio

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test.duckdb"
                # Use max_concurrent_fetches=1 to avoid DuckDB write conflicts
                config = CacheConfig(db_path=str(db_path), max_concurrent_fetches=1)

                mock_client = MagicMock()
                mock_client.get_history.return_value = pd.DataFrame(
                    {"close": [110.0]},
                    index=pd.date_range("2024-01-01", periods=1),
                )

                cache = DataCache(config=config, client=mock_client)
                try:
                    rics = ["TYc1", "USc1"]
                    results = []
                    async for result in cache.async_iter_fetch(
                        rics,
                        start="2024-01-01",
                        end="2024-01-02",
                    ):
                        results.append(result)

                    assert len(results) == 2
                    assert all(isinstance(r, FetchResult) for r in results)
                finally:
                    cache.close()

        asyncio.run(run_test())

    def test_async_progress_callback(self):
        """Test progress callback in async batch fetch."""
        import asyncio

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test.duckdb"
                # Use max_concurrent_fetches=1 to avoid DuckDB write conflicts
                config = CacheConfig(db_path=str(db_path), max_concurrent_fetches=1)

                mock_client = MagicMock()
                mock_client.get_history.return_value = pd.DataFrame(
                    {"close": [110.0]},
                    index=pd.date_range("2024-01-01", periods=1),
                )

                progress_calls = []

                def progress_callback(ric: str, completed: int, total: int):
                    progress_calls.append((ric, completed, total))

                cache = DataCache(config=config, client=mock_client)
                try:
                    await cache.async_get_or_fetch_many(
                        ["TYc1", "USc1"],
                        start="2024-01-01",
                        end="2024-01-02",
                        progress_callback=progress_callback,
                    )
                    assert len(progress_calls) == 2
                    # Check that all RICs were reported
                    reported_rics = {call[0] for call in progress_calls}
                    assert "TYc1" in reported_rics
                    assert "USc1" in reported_rics
                finally:
                    cache.close()

        asyncio.run(run_test())

    def test_concurrent_same_ric_no_duplicate_api_calls(self):
        """Test that concurrent fetches of same RIC don't make duplicate API calls.

        Uses async_iter_fetch to get individual results for each request,
        verifying that per-RIC locking prevents duplicate API calls.
        """
        import asyncio

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test.duckdb"
                # Use max_concurrent_fetches=5 to allow parallelism
                config = CacheConfig(db_path=str(db_path), max_concurrent_fetches=5)

                mock_client = MagicMock()
                mock_client.get_history.return_value = pd.DataFrame(
                    {"close": [110.0, 111.0, 112.0]},
                    index=pd.date_range("2024-01-01", periods=3),
                )

                cache = DataCache(config=config, client=mock_client)
                try:
                    # Launch 5 concurrent fetches for SAME RIC using iter_fetch
                    # to get individual FetchResult for each request
                    results = []
                    async for result in cache.async_iter_fetch(
                        ["TYc1", "TYc1", "TYc1", "TYc1", "TYc1"],
                        start="2024-01-01",
                        end="2024-01-03",
                    ):
                        results.append(result)

                    # All 5 requests should complete successfully
                    assert len(results) == 5
                    for result in results:
                        assert result.success
                        assert result.data is not None
                        assert len(result.data) == 3

                    # Should only call API ONCE due to per-RIC locking
                    # First fetch gets data from API, subsequent ones get cached data
                    assert mock_client.get_history.call_count == 1
                finally:
                    cache.close()

        asyncio.run(run_test())
