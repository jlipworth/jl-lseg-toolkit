"""Tests for timeseries scheduler.

Tests cover:
- Universe building from constants
- Job CRUD operations
- Extraction with mocked LSEG client
- State management
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lseg_toolkit.timeseries.config import DatabaseConfig
from lseg_toolkit.timeseries.enums import AssetClass, DataShape, Granularity
from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.default_jobs import ensure_ff_strip_jobs
from lseg_toolkit.timeseries.scheduler.jobs import ExtractionJob
from lseg_toolkit.timeseries.scheduler.models import InstrumentSpec, JobRunResult
from lseg_toolkit.timeseries.scheduler.universes import (
    build_universe,
    get_available_groups,
)


class TestUniverseBuilding:
    """Tests for instrument universe building."""

    def test_get_available_groups_not_empty(self):
        """Available groups list should not be empty."""
        groups = get_available_groups()
        assert len(groups) > 0
        assert "benchmark_fixings" in groups
        assert "fx_spot" in groups
        assert "treasury_futures" in groups
        assert "stir_ff" in groups

    def test_build_universe_benchmark_fixings(self):
        """Build benchmark fixings universe."""
        instruments = build_universe("benchmark_fixings")

        assert len(instruments) == 4
        assert all(isinstance(i, InstrumentSpec) for i in instruments)

        # Check SOFR is included
        sofr = next((i for i in instruments if i.symbol == "SOFR"), None)
        assert sofr is not None
        assert sofr.ric == "USDSOFR="
        assert sofr.asset_class == AssetClass.FIXING
        assert sofr.data_shape == DataShape.FIXING

    def test_build_universe_fx_spot(self):
        """Build FX spot universe."""
        instruments = build_universe("fx_spot")

        assert len(instruments) == 11
        assert all(i.data_shape == DataShape.QUOTE for i in instruments)

        # Check EURUSD
        eurusd = next((i for i in instruments if i.symbol == "EURUSD"), None)
        assert eurusd is not None
        assert eurusd.ric == "EUR="
        assert eurusd.asset_class == AssetClass.FX_SPOT

    def test_build_universe_treasury_futures(self):
        """Build treasury futures universe."""
        instruments = build_universe("treasury_futures")

        assert len(instruments) == 8
        assert all(i.data_shape == DataShape.OHLCV for i in instruments)
        assert all(i.asset_class == AssetClass.BOND_FUTURES for i in instruments)

        # Check ZN (10-year)
        zn = next((i for i in instruments if i.symbol == "ZN"), None)
        assert zn is not None
        assert zn.ric == "TYc1"

    def test_build_universe_unknown_group_raises(self):
        """Unknown group should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown instrument group"):
            build_universe("nonexistent_group")

    def test_all_groups_build_successfully(self):
        """All registered groups should build without error."""
        for group in get_available_groups():
            instruments = build_universe(group)
            assert len(instruments) > 0, f"Group {group} returned empty universe"
            assert all(isinstance(i, InstrumentSpec) for i in instruments), (
                f"Group {group} returned non-InstrumentSpec"
            )


class TestSchedulerConfig:
    """Tests for scheduler configuration."""

    def test_default_config(self):
        """Default config should have sensible values."""
        config = SchedulerConfig()

        assert config.max_workers >= 1
        assert config.rate_limit_delay >= 0
        assert config.max_rics_per_batch > 0
        assert config.intraday_retention_days > 0
        assert config.max_retries >= 0

    def test_config_from_env(self):
        """Config should load from environment."""
        with patch.dict(
            "os.environ",
            {
                "SCHEDULER_MAX_WORKERS": "8",
                "SCHEDULER_RATE_LIMIT": "0.1",
            },
        ):
            config = SchedulerConfig.from_env()
            assert config.max_workers == 8
            assert config.rate_limit_delay == 0.1


class TestInstrumentSpec:
    """Tests for InstrumentSpec dataclass."""

    def test_instrument_spec_creation(self):
        """InstrumentSpec should be creatable with required fields."""
        spec = InstrumentSpec(
            symbol="SOFR",
            ric="USDSOFR=",
            asset_class=AssetClass.FIXING,
            data_shape=DataShape.FIXING,
        )

        assert spec.symbol == "SOFR"
        assert spec.ric == "USDSOFR="
        assert spec.asset_class == AssetClass.FIXING
        assert spec.data_shape == DataShape.FIXING
        assert spec.name is None

    def test_instrument_spec_with_name(self):
        """InstrumentSpec should accept optional name."""
        spec = InstrumentSpec(
            symbol="ZN",
            ric="TYc1",
            asset_class=AssetClass.BOND_FUTURES,
            data_shape=DataShape.OHLCV,
            name="10-Year T-Note Future",
        )

        assert spec.name == "10-Year T-Note Future"


class TestDefaultJobs:
    """Tests for default scheduler job helpers."""

    @patch("lseg_toolkit.timeseries.scheduler.default_jobs.create_job")
    @patch("lseg_toolkit.timeseries.scheduler.default_jobs.get_job_by_name")
    def test_ensure_ff_strip_jobs_creates_missing_jobs(
        self, mock_get_job_by_name, mock_create_job
    ):
        """Missing FF strip jobs should be created."""
        mock_get_job_by_name.return_value = None

        result = ensure_ff_strip_jobs(MagicMock())

        assert result["STIR_FF_STRIP_DAILY"] == "created"
        assert result["STIR_FF_STRIP_HOURLY"] == "created"
        assert mock_create_job.call_count == 2

    @patch("lseg_toolkit.timeseries.scheduler.default_jobs.create_job")
    @patch("lseg_toolkit.timeseries.scheduler.default_jobs.get_job_by_name")
    def test_ensure_ff_strip_jobs_skips_existing_jobs(
        self, mock_get_job_by_name, mock_create_job
    ):
        """Existing FF strip jobs should not be recreated."""
        mock_get_job_by_name.return_value = {"id": 1}

        result = ensure_ff_strip_jobs(MagicMock())

        assert result["STIR_FF_STRIP_DAILY"] == "exists"
        assert result["STIR_FF_STRIP_HOURLY"] == "exists"
        mock_create_job.assert_not_called()


@pytest.mark.skipif(
    not pytest.importorskip("psycopg", reason="psycopg not installed"),
    reason="PostgreSQL tests require psycopg",
)
class TestJobCRUD:
    """Tests for job CRUD operations.

    These tests require a PostgreSQL database. Set POSTGRES_* env vars or skip.
    """

    @pytest.fixture
    def db_config(self):
        """Get database config from environment."""
        config = DatabaseConfig.from_env()
        # Skip if using default localhost (no real DB configured)
        if config.host == "localhost" and config.password == "":
            pytest.skip("No database configured - set POSTGRES_* env vars")
        return config

    @pytest.fixture
    def db_conn(self, db_config):
        """Get database connection."""
        from lseg_toolkit.timeseries.storage import get_connection, init_db

        init_db(db_config)
        with get_connection(config=db_config) as conn:
            yield conn

    def test_create_job(self, db_conn):
        """Test creating a new job."""
        from lseg_toolkit.timeseries.scheduler.state import create_job, get_job_by_name

        job_id = create_job(
            db_conn,
            name="test_job",
            instrument_group="benchmark_fixings",
            granularity="daily",
            schedule_cron="0 18 * * 1-5",
        )
        db_conn.commit()

        assert job_id > 0

        # Verify job exists
        job = get_job_by_name(db_conn, "test_job")
        assert job is not None
        assert job["instrument_group"] == "benchmark_fixings"
        assert job["granularity"] == "daily"

    def test_list_jobs(self, db_conn):
        """Test listing jobs."""
        from lseg_toolkit.timeseries.scheduler.state import (
            create_job,
            get_all_jobs,
            get_enabled_jobs,
        )

        # Create test jobs
        create_job(
            db_conn,
            name="job1",
            instrument_group="fx_spot",
            granularity="daily",
            schedule_cron="0 18 * * *",
            enabled=True,
        )
        create_job(
            db_conn,
            name="job2",
            instrument_group="benchmark_fixings",
            granularity="daily",
            schedule_cron="0 17 * * *",
            enabled=False,
        )
        db_conn.commit()

        all_jobs = get_all_jobs(db_conn)
        enabled_jobs = get_enabled_jobs(db_conn)

        assert len(all_jobs) >= 2
        assert len(enabled_jobs) >= 1
        assert any(j["name"] == "job1" for j in enabled_jobs)


class TestExtractionMocked:
    """Tests for extraction with mocked LSEG client."""

    @pytest.fixture
    def mock_client(self):
        """Create mock LSEG client."""
        client = MagicMock()

        # Mock get_history to return sample data
        def mock_get_history(rics, start, end, interval):
            # Return sample fixing data
            dates = pd.date_range(start=start, end=end, freq="B")
            data = {
                "Date": dates,
                "FIXING": [4.5 + i * 0.01 for i in range(len(dates))],
            }
            df = pd.DataFrame(data)
            df.set_index("Date", inplace=True)
            return df

        client.get_history.side_effect = mock_get_history
        return client

    def test_mock_client_returns_data(self, mock_client):
        """Mock client should return DataFrame."""
        df = mock_client.get_history(
            rics="USDSOFR=",
            start="2024-01-01",
            end="2024-01-31",
            interval="daily",
        )

        assert df is not None
        assert not df.empty
        assert "FIXING" in df.columns

    @patch("lseg_toolkit.timeseries.scheduler.jobs.save_timeseries")
    @patch("lseg_toolkit.timeseries.scheduler.jobs.fetch_fed_funds_hourly")
    def test_ff_continuous_hourly_uses_special_fetcher(
        self, mock_fetch_hourly, mock_save_timeseries
    ):
        """FF_CONTINUOUS hourly scheduler path should use Fed Funds fetcher."""
        dates = pd.date_range("2026-03-01 22:00", periods=2, freq="h")
        mock_fetch_hourly.return_value = pd.DataFrame(
            {
                "mid": [96.37, 96.36],
                "close": [96.37, 96.36],
                "session_date": [pd.Timestamp("2026-03-02").date()] * 2,
                "source_contract": ["FFJ26", "FFJ26"],
            },
            index=dates,
        )
        mock_save_timeseries.return_value = 2

        job = ExtractionJob(job_id=1, client=MagicMock(), config=SchedulerConfig())
        spec = InstrumentSpec(
            symbol="FF_CONTINUOUS",
            ric="FFc1",
            asset_class=AssetClass.STIR_FUTURES,
            data_shape=DataShape.OHLCV,
            name="30-Day Fed Funds Continuous",
        )

        rows = job._fetch_gap(
            conn=MagicMock(),
            spec=spec,
            instrument_id=123,
            start_date=pd.Timestamp("2026-03-01").date(),
            end_date=pd.Timestamp("2026-03-03").date(),
            granularity=Granularity.HOURLY,
            max_chunk_days=30,
        )

        assert rows == 2
        mock_fetch_hourly.assert_called_once()
        assert mock_fetch_hourly.call_args.kwargs["rank"] == 1
        mock_save_timeseries.assert_called_once()

    @patch("lseg_toolkit.timeseries.scheduler.jobs.save_timeseries")
    @patch("lseg_toolkit.timeseries.scheduler.jobs.fetch_fed_funds_hourly")
    def test_ff_continuous_rank_two_hourly_uses_special_fetcher(
        self, mock_fetch_hourly, mock_save_timeseries
    ):
        """FF_CONTINUOUS_2 should route to the FF rank-2 fetcher."""
        dates = pd.date_range("2026-03-01 22:00", periods=2, freq="h")
        mock_fetch_hourly.return_value = pd.DataFrame(
            {
                "mid": [96.37, 96.36],
                "close": [96.37, 96.36],
                "session_date": [pd.Timestamp("2026-03-02").date()] * 2,
                "source_contract": ["FFK26", "FFK26"],
            },
            index=dates,
        )
        mock_save_timeseries.return_value = 2

        job = ExtractionJob(job_id=1, client=MagicMock(), config=SchedulerConfig())
        spec = InstrumentSpec(
            symbol="FF_CONTINUOUS_2",
            ric="FFc2",
            asset_class=AssetClass.STIR_FUTURES,
            data_shape=DataShape.OHLCV,
            name="30-Day Fed Funds Continuous Rank 2",
        )

        rows = job._fetch_gap(
            conn=MagicMock(),
            spec=spec,
            instrument_id=123,
            start_date=pd.Timestamp("2026-03-01").date(),
            end_date=pd.Timestamp("2026-03-03").date(),
            granularity=Granularity.HOURLY,
            max_chunk_days=30,
        )

        assert rows == 2
        mock_fetch_hourly.assert_called_once()
        assert mock_fetch_hourly.call_args.kwargs["rank"] == 2
        mock_save_timeseries.assert_called_once()

    def test_stir_universe_includes_ff_continuous(self):
        """STIR universe should include the canonical FF continuous symbol."""
        instruments = build_universe("stir_futures")
        ff = next((i for i in instruments if i.symbol == "FF_CONTINUOUS"), None)
        assert ff is not None
        assert ff.ric == "FFc1"
        assert ff.asset_class == AssetClass.STIR_FUTURES

    def test_stir_ff_universe_only_contains_ff_continuous(self):
        """FF-only universe should contain the full 12-rank FF strip."""
        instruments = build_universe("stir_ff")
        assert len(instruments) == 12
        assert instruments[0].symbol == "FF_CONTINUOUS"
        assert instruments[0].ric == "FFc1"
        assert instruments[-1].symbol == "FF_CONTINUOUS_12"
        assert instruments[-1].ric == "FFc12"


class TestJobRunResult:
    """Tests for JobRunResult dataclass."""

    def test_job_run_result_creation(self):
        """JobRunResult should be creatable."""
        result = JobRunResult(
            job_id=1,
            run_id=100,
            status="completed",
            instruments_total=4,
            instruments_success=4,
            instruments_failed=0,
            rows_extracted=120,
            errors=[],
        )

        assert result.job_id == 1
        assert result.status == "completed"
        assert result.instruments_success == 4
        assert result.rows_extracted == 120
        assert len(result.errors) == 0

    def test_job_run_result_with_errors(self):
        """JobRunResult should handle errors."""
        result = JobRunResult(
            job_id=1,
            run_id=101,
            status="partial",
            instruments_total=4,
            instruments_success=3,
            instruments_failed=1,
            rows_extracted=90,
            errors=["CORRA: Connection timeout"],
        )

        assert result.status == "partial"
        assert result.instruments_failed == 1
        assert len(result.errors) == 1
        assert "CORRA" in result.errors[0]
