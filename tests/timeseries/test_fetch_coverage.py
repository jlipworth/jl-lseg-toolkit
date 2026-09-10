"""Fetch-coverage SQL tests: no database/server required."""

from datetime import date
from unittest.mock import MagicMock

from lseg_toolkit.timeseries.enums import Granularity
from lseg_toolkit.timeseries.storage.fetch_coverage import (
    load_fetch_coverage,
    save_fetch_coverage,
)


def test_read_coverage_parameterizes_identity_granularity_and_bounds():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [
        {"start_date": date(2026, 1, 1), "end_date": date(2026, 1, 3)},
        {"start_date": date(2026, 1, 8), "end_date": date(2026, 1, 10)},
    ]
    result = load_fetch_coverage(
        conn, 42, Granularity.HOURLY, date(2026, 1, 1), date(2026, 1, 10)
    )
    assert result == [
        (date(2026, 1, 1), date(2026, 1, 3)),
        (date(2026, 1, 8), date(2026, 1, 10)),
    ]
    assert conn.execute.call_args.args[1] == (
        42,
        "hourly",
        date(2026, 1, 10),
        date(2026, 1, 1),
    )


def test_record_coverage_does_not_commit_before_data():
    conn = MagicMock()
    save_fetch_coverage(conn, 42, Granularity.DAILY, date(2026, 1, 3), date(2026, 1, 4))
    assert conn.execute.call_args.args[1] == (
        42,
        "daily",
        date(2026, 1, 3),
        date(2026, 1, 4),
    )
    conn.commit.assert_not_called()


def test_current_and_future_dates_never_persist_as_complete():
    from datetime import UTC, datetime, timedelta

    today = datetime.now(UTC).date()
    conn = MagicMock()
    save_fetch_coverage(conn, 42, Granularity.HOURLY, today, today + timedelta(days=5))
    conn.execute.assert_not_called()
    save_fetch_coverage(conn, 42, Granularity.HOURLY, today - timedelta(days=1), today)
    assert conn.execute.call_args.args[1][-1] == today - timedelta(days=1)
