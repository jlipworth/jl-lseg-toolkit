"""Staging SQL must remain isolated to its own database session."""

import io
from unittest.mock import MagicMock

import pytest

from lseg_toolkit.timeseries.storage.writer import _copy_with_upsert


@pytest.mark.parametrize("columns", [["id", "value"], ["id"]])
def test_upsert_uses_transaction_scoped_temporary_staging(columns):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    assert (
        _copy_with_upsert(
            conn, "timeseries_rate", columns, io.StringIO("1\t2\n"), ["id"]
        )
        == 1
    )
    statements = [call.args[0].as_string() for call in cursor.execute.call_args_list]
    assert statements[0] == 'DROP TABLE IF EXISTS "pg_temp"."_staging_timeseries_rate"'
    assert 'CREATE TEMP TABLE "pg_temp"."_staging_timeseries_rate"' in statements[1]
    assert "ON COMMIT DROP" in statements[1]
    assert "UNLOGGED" not in statements[1]
    assert 'FROM "pg_temp"."_staging_timeseries_rate"' in statements[2]
    copy_sql = cursor.copy.call_args.args[0].as_string()
    assert 'COPY "pg_temp"."_staging_timeseries_rate"' in copy_sql
    conn.transaction.assert_called_once_with()


def test_repeated_batches_refresh_only_their_session_staging():
    conn = MagicMock()
    for _ in range(2):
        _copy_with_upsert(conn, "timeseries_rate", ["id"], io.StringIO("1\n"), ["id"])
    cursor = conn.cursor.return_value.__enter__.return_value
    statements = [call.args[0].as_string() for call in cursor.execute.call_args_list]
    assert statements[0] == statements[3]
    assert '"pg_temp"' in statements[3]


def test_empty_upsert_does_not_create_staging():
    conn = MagicMock()
    assert (
        _copy_with_upsert(conn, "timeseries_rate", ["id"], io.StringIO(), ["id"]) == 0
    )
    conn.cursor.assert_not_called()
    conn.transaction.assert_not_called()
