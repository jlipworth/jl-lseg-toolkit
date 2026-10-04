"""Opt-in PostgreSQL regressions; only disposable test containers are used.

No LSEG sessions or ambient database credentials are used. These tests exercise
ordinary table semantics, not TimescaleDB extension/compression policies.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import MagicMock

import pandas as pd
import psycopg
import pyarrow.parquet as pq
import pytest
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.config import DatabaseConfig
from lseg_toolkit.timeseries.enums import AssetClass, DataShape, Granularity
from lseg_toolkit.timeseries.export import export_metadata, export_to_parquet
from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.jobs import ExtractionJob
from lseg_toolkit.timeseries.scheduler.models import InstrumentSpec
from lseg_toolkit.timeseries.scheduler.state import create_job, get_instrument_state
from lseg_toolkit.timeseries.storage import (
    load_timeseries,
    save_instrument,
    save_timeseries,
)
from lseg_toolkit.timeseries.storage.connection import close_pool
from lseg_toolkit.timeseries.storage.fetch_coverage import (
    load_fetch_coverage,
    save_fetch_coverage,
)
from lseg_toolkit.timeseries.storage.pg_schema import SCHEMA_SQL

pytestmark = pytest.mark.integration


@pytest.fixture
def postgres_dsn():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(
        "postgres:16-alpine",
        username="storage_test",
        password="storage_test",
        dbname="storage_test",
        driver=None,
    ) as postgres:
        dsn = postgres.get_connection_url()
        with psycopg.connect(dsn) as conn:
            conn.execute(
                SCHEMA_SQL.replace(
                    "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;", ""
                )
            )
        yield dsn
        close_pool()


@pytest.mark.parametrize(
    "shape,asset,column",
    [
        (DataShape.OHLCV, AssetClass.BOND_FUTURES, "close"),
        (DataShape.QUOTE, AssetClass.FX_SPOT, "bid"),
        (DataShape.RATE, AssetClass.OIS, "rate"),
        (DataShape.BOND, AssetClass.GOVT_YIELD, "yield"),
        (DataShape.FIXING, AssetClass.FIXING, "value"),
    ],
)
def test_all_shapes_copy_upsert_read_export(
    postgres_dsn, tmp_path, shape, asset, column
):
    # Explicit DSN-derived config; never fall back to the operator environment.
    kwargs = psycopg.conninfo.conninfo_to_dict(postgres_dsn)
    config = DatabaseConfig(
        host=kwargs["host"],
        port=int(kwargs.get("port", 5432)),
        database=kwargs["dbname"],
        user=kwargs["user"],
        password=kwargs.get("password", ""),
    )
    index = pd.to_datetime(["2026-01-05 00:00", "2026-01-06 23:00"], utc=True)
    frame = pd.DataFrame({column: [1.0, 2.0]}, index=index)
    with psycopg.connect(postgres_dsn, row_factory=dict_row) as conn:
        instrument = save_instrument(
            conn, "TEST", "Test", asset, "TEST", data_shape=shape
        )
        assert save_timeseries(conn, instrument, frame, Granularity.DAILY) == 2
        assert save_timeseries(conn, instrument, frame * 2, Granularity.DAILY) == 2
        loaded = load_timeseries(conn, "TEST", date(2026, 1, 5), date(2026, 1, 6))
        assert loaded[column].tolist() == [2.0, 4.0]
        save_fetch_coverage(
            conn, instrument, Granularity.DAILY, date(2026, 1, 5), date(2026, 1, 6)
        )
        assert load_fetch_coverage(
            conn, instrument, Granularity.DAILY, date(2026, 1, 5), date(2026, 1, 6)
        ) == [(date(2026, 1, 5), date(2026, 1, 6))]
    files = export_to_parquet(config=config, output_dir=str(tmp_path), symbol="TEST")
    assert len(files) == 1
    assert pq.read_table(files[0]).column(column).to_pylist() == [2.0, 4.0]
    metadata = export_metadata(config=config, output_dir=str(tmp_path))
    assert pq.read_table(metadata["instruments"]).num_rows == 1
    assert pq.read_table(metadata["roll_events"]).num_rows == 0


def test_simultaneous_staging_preserves_public_table(postgres_dsn):
    with psycopg.connect(postgres_dsn, row_factory=dict_row) as conn:
        ids = [
            save_instrument(
                conn,
                f"TEST{i}",
                "Test",
                AssetClass.OIS,
                f"TEST{i}",
                data_shape=DataShape.RATE,
            )
            for i in range(2)
        ]
        conn.execute("CREATE TABLE public._staging_timeseries_rate (sentinel integer)")
        conn.execute("INSERT INTO public._staging_timeseries_rate VALUES (42)")
    barrier = Barrier(2)

    def write(instrument):
        with psycopg.connect(postgres_dsn, row_factory=dict_row) as conn:
            barrier.wait(timeout=10)
            frame = pd.DataFrame(
                {"rate": [float(instrument)]}, index=pd.to_datetime(["2026-01-05"])
            )
            for _ in range(2):
                assert save_timeseries(conn, instrument, frame) == 1
        return instrument

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert set(executor.map(write, ids)) == set(ids)
    with psycopg.connect(postgres_dsn, row_factory=dict_row) as conn:
        assert (
            conn.execute(
                "SELECT sentinel FROM public._staging_timeseries_rate"
            ).fetchone()["sentinel"]
            == 42
        )
        assert (
            conn.execute("SELECT count(*) AS count FROM timeseries_rate").fetchone()[
                "count"
            ]
            == 2
        )
        assert (
            conn.execute(
                "SELECT to_regclass('pg_temp._staging_timeseries_rate') AS relation"
            ).fetchone()["relation"]
            is None
        )


def test_scheduler_partial_calendar_response_rolls_back(postgres_dsn, monkeypatch):
    with psycopg.connect(postgres_dsn, row_factory=dict_row) as conn:
        instrument = save_instrument(
            conn, "ZN", "Treasury", AssetClass.BOND_FUTURES, "TYc1"
        )
        job_id = create_job(
            conn, "test", "treasury_futures", "daily", "0 18 * * mon-fri"
        )
        conn.commit()
        job = ExtractionJob(job_id, MagicMock(), SchedulerConfig())
        spec = InstrumentSpec("ZN", "TYc1", AssetClass.BOND_FUTURES, DataShape.OHLCV)
        # Fixed historical gap, deliberately return only one of its sessions.
        from lseg_toolkit.timeseries.cache import DateGap, detect_gaps
        from lseg_toolkit.timeseries.scheduler import jobs

        def gaps(*args, **kwargs):
            if kwargs.get("refresh_mutable") is False:
                return detect_gaps(
                    conn,
                    "ZN",
                    date(2026, 1, 5),
                    date(2026, 1, 7),
                    Granularity.DAILY,
                    refresh_mutable=False,
                )
            return [DateGap(date(2026, 1, 5), date(2026, 1, 7))]

        monkeypatch.setattr(jobs, "detect_gaps", gaps)
        monkeypatch.setattr(
            job,
            "_fetch_timeseries",
            lambda *args: pd.DataFrame(
                {"close": [100.0]}, index=pd.to_datetime(["2026-01-05"])
            ),
        )
        result = job._extract_instrument(
            conn,
            spec,
            instrument,
            {"granularity": "daily", "lookback_days": 5, "max_chunk_days": 30},
        )
        assert not result.success
        state = get_instrument_state(conn, job_id, instrument)
        assert state["last_success_date"] is None
        assert state["consecutive_failures"] == 1
        assert load_timeseries(conn, "ZN").empty
        assert (
            load_fetch_coverage(
                conn, instrument, Granularity.DAILY, date(2026, 1, 5), date(2026, 1, 7)
            )
            == []
        )
        assert conn.execute("SELECT 1 AS usable").fetchone()["usable"] == 1


def test_scheduler_sql_error_records_failure_in_usable_transaction(
    postgres_dsn, monkeypatch
):
    with psycopg.connect(postgres_dsn, row_factory=dict_row) as conn:
        instrument = save_instrument(
            conn, "EURUSD", "FX", AssetClass.FX_SPOT, "EUR=", data_shape=DataShape.QUOTE
        )
        job_id = create_job(
            conn, "sql_failure", "fx_spot", "hourly", "0 18 * * mon-fri"
        )
        conn.commit()
        job = ExtractionJob(job_id, MagicMock(), SchedulerConfig())
        spec = InstrumentSpec("EURUSD", "EUR=", AssetClass.FX_SPOT, DataShape.QUOTE)

        def sql_error(*args):
            conn.execute("SELECT missing_column FROM instruments")

        monkeypatch.setattr(job, "_fetch_timeseries", sql_error)
        result = job._extract_instrument(
            conn,
            spec,
            instrument,
            {"granularity": "hourly", "lookback_days": 5, "max_chunk_days": 30},
        )
        assert not result.success
        state = get_instrument_state(conn, job_id, instrument)
        assert state["consecutive_failures"] == 1
        assert state["last_success_date"] is None
        assert conn.execute("SELECT 1 AS usable").fetchone()["usable"] == 1
