"""Deterministic query-count regressions, not wall-clock performance assertions."""

from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.enums import AssetClass, DataShape
from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.jobs import ExtractionJob
from lseg_toolkit.timeseries.scheduler.models import InstrumentSpec


def spec(symbol):
    return InstrumentSpec(
        symbol=symbol,
        ric=symbol,
        asset_class=AssetClass.BOND_FUTURES,
        data_shape=DataShape.OHLCV,
    )


def test_existing_universe_uses_one_select_and_keeps_order():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchall.return_value = [
        {"symbol": f"S{i}", "id": i} for i in reversed(range(200))
    ]
    job = ExtractionJob(1, MagicMock(), SchedulerConfig())
    with patch("lseg_toolkit.timeseries.scheduler.jobs.save_instrument") as save:
        assert job._ensure_instruments(
            conn, [spec(f"S{i}") for i in range(200)]
        ) == list(range(200))
    cur.execute.assert_called_once()
    assert "symbol = ANY(%s)" in cur.execute.call_args.args[0]
    assert len(cur.execute.call_args.args[1][0]) == 200
    save.assert_not_called()


def test_missing_duplicate_symbol_registered_only_once():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchall.return_value = [{"symbol": "OLD", "id": 1}]
    job = ExtractionJob(1, MagicMock(), SchedulerConfig())
    with patch(
        "lseg_toolkit.timeseries.scheduler.jobs.save_instrument", return_value=2
    ) as save:
        assert job._ensure_instruments(
            conn, [spec("NEW"), spec("OLD"), spec("NEW")]
        ) == [2, 1, 2]
    save.assert_called_once()
    assert cur.execute.call_args.args[1] == [["NEW", "OLD"]]


def test_empty_universe_issues_no_queries():
    conn = MagicMock()
    job = ExtractionJob(1, MagicMock(), SchedulerConfig())
    assert job._ensure_instruments(conn, []) == []
    conn.cursor.assert_not_called()
