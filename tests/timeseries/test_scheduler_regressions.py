"""Offline scheduler regressions for timezone and failed SQL transactions."""

from contextlib import contextmanager
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import psycopg
import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from lseg_toolkit.timeseries.enums import AssetClass, DataShape, Granularity
from lseg_toolkit.timeseries.scheduler import jobs
from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.daemon import ExtractionDaemon
from lseg_toolkit.timeseries.scheduler.jobs import ExtractionJob
from lseg_toolkit.timeseries.scheduler.models import InstrumentSpec


@pytest.mark.parametrize("month,expected_hour", [(1, 23), (7, 22)])
def test_cron_uses_scheduler_timezone_not_host_timezone(month, expected_hour):
    daemon = ExtractionDaemon()
    daemon.scheduler = BackgroundScheduler(timezone="America/New_York")
    daemon._schedule_job({"id": 1, "name": "daily", "schedule_cron": "30 18 * * *"})
    trigger = daemon.scheduler.get_job("job_1").trigger
    now = datetime(2026, month, 15, tzinfo=UTC)
    next_fire = trigger.get_next_fire_time(None, now)
    assert next_fire.astimezone(UTC).hour == expected_hour
    assert next_fire.minute == 30


def test_environment_default_retention_matches_dataclass(monkeypatch):
    monkeypatch.delenv("SCHEDULER_INTRADAY_RETENTION", raising=False)
    assert (
        SchedulerConfig.from_env().intraday_retention_days
        == SchedulerConfig().intraday_retention_days
    )


def test_database_error_rolls_back_before_recording_instrument_failure(monkeypatch):
    conn = MagicMock()
    events = []

    @contextmanager
    def transaction():
        events.append("begin")
        try:
            yield
        except Exception:
            events.append("rollback")
            raise

    conn.transaction = transaction
    monkeypatch.setattr(jobs, "get_instrument_state", lambda *a: None)

    def fail_sql(*args):
        raise psycopg.DatabaseError("synthetic database failure")

    monkeypatch.setattr(jobs, "detect_gaps", fail_sql)

    def record_state(*args, **kwargs):
        assert events[-1] == "rollback"
        assert not kwargs["success"]
        events.append("failure recorded")

    monkeypatch.setattr(jobs, "upsert_instrument_state", record_state)
    job = ExtractionJob(1, MagicMock(), SchedulerConfig())
    spec = InstrumentSpec("EURUSD", "EUR=", AssetClass.FX_SPOT, DataShape.QUOTE)
    result = job._extract_instrument(
        conn,
        spec,
        1,
        {"granularity": "daily", "lookback_days": 5, "max_chunk_days": 30},
    )
    assert not result.success
    assert events == ["begin", "rollback", "failure recorded"]


@pytest.mark.parametrize("chunk_days", [0, -1])
def test_nonpositive_chunk_size_fails_without_fetching(chunk_days):
    client = MagicMock()
    job = ExtractionJob(1, client, SchedulerConfig())
    spec = InstrumentSpec("EURUSD", "EUR=", AssetClass.FX_SPOT, DataShape.QUOTE)
    with pytest.raises(ValueError, match="max_chunk_days"):
        job._fetch_gap(
            MagicMock(),
            spec,
            1,
            date(2026, 1, 1),
            date(2026, 1, 2),
            Granularity.DAILY,
            chunk_days,
        )
    client.get_history.assert_not_called()


def test_default_daily_jobs_skip_weekends_and_include_monday():
    from apscheduler.triggers.cron import CronTrigger

    from lseg_toolkit.timeseries.scheduler.default_jobs import (
        FF_STRIP_JOB_SPECS,
        RATE_DECISION_JOB_SPECS,
    )

    for spec in [FF_STRIP_JOB_SPECS[0], *RATE_DECISION_JOB_SPECS]:
        trigger = CronTrigger.from_crontab(
            spec.schedule_cron, timezone="America/New_York"
        )
        # After every Friday firing (including 22:00 New York).
        after_friday = datetime(2026, 9, 12, 4, tzinfo=UTC)
        next_fire = trigger.get_next_fire_time(None, after_friday)
        assert next_fire.weekday() == 0


def test_default_ff_hourly_includes_sunday_not_saturday():
    from apscheduler.triggers.cron import CronTrigger

    from lseg_toolkit.timeseries.scheduler.default_jobs import FF_STRIP_JOB_SPECS

    trigger = CronTrigger.from_crontab(
        FF_STRIP_JOB_SPECS[1].schedule_cron, timezone="America/New_York"
    )
    saturday = datetime(2026, 9, 12, 4, tzinfo=UTC)
    assert trigger.get_next_fire_time(None, saturday).weekday() == 6


def test_successful_empty_scheduler_chunks_record_coverage(monkeypatch):
    import pandas as pd

    job = ExtractionJob(1, MagicMock(), SchedulerConfig())
    spec = InstrumentSpec("EURUSD", "EUR=", AssetClass.FX_SPOT, DataShape.QUOTE)
    monkeypatch.setattr(job, "_fetch_timeseries", lambda *args: pd.DataFrame())
    coverage = MagicMock()
    monkeypatch.setattr(jobs, "save_fetch_coverage", coverage)
    job._fetch_gap(
        MagicMock(), spec, 7, date(2026, 1, 1), date(2026, 1, 3), Granularity.HOURLY, 2
    )
    assert [call.args[-2:] for call in coverage.call_args_list] == [
        (date(2026, 1, 1), date(2026, 1, 2)),
        (date(2026, 1, 3), date(2026, 1, 3)),
    ]


def test_failed_scheduler_chunk_does_not_record_coverage(monkeypatch):
    job = ExtractionJob(1, MagicMock(), SchedulerConfig())
    spec = InstrumentSpec("EURUSD", "EUR=", AssetClass.FX_SPOT, DataShape.QUOTE)
    monkeypatch.setattr(
        job, "_fetch_timeseries", MagicMock(side_effect=RuntimeError("provider failed"))
    )
    coverage = MagicMock()
    monkeypatch.setattr(jobs, "save_fetch_coverage", coverage)
    with pytest.raises(RuntimeError, match="provider failed"):
        job._fetch_gap(
            MagicMock(),
            spec,
            7,
            date(2026, 1, 1),
            date(2026, 1, 3),
            Granularity.HOURLY,
            2,
        )
    coverage.assert_not_called()
