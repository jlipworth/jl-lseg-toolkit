"""Tests for timeseries PostgreSQL/TimescaleDB storage layer.

Uses mocked psycopg connections to test storage operations without
requiring a live database.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lseg_toolkit.timeseries.enums import AssetClass, DataShape, Granularity


class TestGetConnection:
    """Tests for database connection management."""

    @patch("lseg_toolkit.timeseries.storage.connection.get_pool")
    def test_get_connection_uses_pool(self, mock_get_pool):
        """Connection should use pool by default."""
        from lseg_toolkit.timeseries.storage import get_connection

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_pool.return_value = mock_pool

        with get_connection() as conn:
            assert conn == mock_conn

    @patch("lseg_toolkit.timeseries.storage.connection.psycopg")
    def test_get_connection_direct_dsn(self, mock_psycopg):
        """Direct DSN should bypass pool."""
        from lseg_toolkit.timeseries.storage import get_connection

        mock_conn = MagicMock()
        mock_psycopg.connect.return_value = mock_conn

        with get_connection(dsn="postgresql://test", use_pool=False) as conn:
            mock_psycopg.connect.assert_called_once()
            assert conn == mock_conn

    @patch("lseg_toolkit.timeseries.storage.connection.get_pool")
    def test_get_connection_db_path_deprecated(self, mock_get_pool):
        """db_path parameter should emit deprecation warning."""
        from lseg_toolkit.timeseries.storage import get_connection

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_pool.return_value = mock_pool

        with pytest.warns(DeprecationWarning, match="db_path.*deprecated"):
            with get_connection(db_path="/path/to/db"):
                pass


class TestInitDb:
    """Tests for database initialization."""

    @patch("lseg_toolkit.timeseries.storage.connection.get_connection")
    @patch("lseg_toolkit.timeseries.storage.pg_schema.init_schema")
    def test_init_db_calls_init_schema(self, mock_init_schema, mock_get_conn):
        """init_db should call init_schema with connection."""
        from lseg_toolkit.timeseries.storage import init_db

        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        init_db()

        mock_init_schema.assert_called_once_with(mock_conn)


class TestSchemaSQL:
    """Tests for schema SQL content (table presence, indexes)."""

    def test_cb_meeting_tables_in_schema(self):
        from lseg_toolkit.timeseries.storage import pg_schema

        sql = pg_schema.SCHEMA_SQL
        for table in ("ecb_meetings", "boe_meetings", "boc_meetings"):
            assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
            assert f"idx_{table}_date" in sql
            assert f"idx_{table}_decision" in sql


class TestMaintenance:
    """Tests for storage maintenance helpers."""

    def test_backfill_ff_continuous_session_dates(self):
        """FF historical backfill should update NULL session_date rows."""
        from lseg_toolkit.timeseries.storage import backfill_ff_continuous_session_dates

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 123
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        updated = backfill_ff_continuous_session_dates(mock_conn)

        assert updated == 123
        sql = mock_cursor.execute.call_args[0][0]
        assert "FF_CONTINUOUS" in sql
        assert "INTERVAL '2 hours'" in sql
        assert "session_date IS NULL" in sql


class TestSaveInstrument:
    """Tests for instrument save operations."""

    def test_save_instrument_basic(self):
        """Test saving a new instrument."""
        from lseg_toolkit.timeseries.storage import save_instrument

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}

        inst_id = save_instrument(
            mock_conn,
            symbol="ZN",
            name="10-Year T-Note",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYc1",
        )

        assert inst_id == 1
        mock_cursor.execute.assert_called()

    def test_save_instrument_with_details(self):
        """Test saving instrument with futures details."""
        from lseg_toolkit.timeseries.storage import save_instrument

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}

        inst_id = save_instrument(
            mock_conn,
            symbol="TYH25",
            name="10-Year T-Note Mar 2025",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYH5",
            underlying="TY",
            continuous_type="discrete",
        )

        assert inst_id == 1


class TestGetInstrument:
    """Tests for instrument retrieval."""

    def test_get_instrument_found(self):
        """Test retrieving an existing instrument."""
        from lseg_toolkit.timeseries.storage import get_instrument

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "symbol": "ZN",
            "name": "10-Year T-Note",
            "asset_class": "bond_futures",
            "lseg_ric": "TYc1",
        }

        inst = get_instrument(mock_conn, "ZN")

        assert inst is not None
        assert inst["symbol"] == "ZN"
        assert inst["asset_class"] == "bond_futures"

    def test_get_instrument_not_found(self):
        """Test retrieving non-existent instrument."""
        from lseg_toolkit.timeseries.storage import get_instrument

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        inst = get_instrument(mock_conn, "NOTFOUND")

        assert inst is None


class TestGetInstrumentId:
    """Tests for instrument ID lookup."""

    def test_get_instrument_id_found(self):
        """Test getting ID for existing instrument."""
        from lseg_toolkit.timeseries.storage import get_instrument_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 42}

        inst_id = get_instrument_id(mock_conn, "ZN")

        assert inst_id == 42

    def test_get_instrument_id_not_found(self):
        """Test getting ID for non-existent instrument."""
        from lseg_toolkit.timeseries.storage import get_instrument_id

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        inst_id = get_instrument_id(mock_conn, "NOTFOUND")

        assert inst_id is None


class TestGetInstruments:
    """Tests for instrument listing."""

    def test_get_instruments_all(self):
        """Test retrieving all instruments."""
        from lseg_toolkit.timeseries.storage import get_instruments

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": 1, "symbol": "EURUSD", "asset_class": "fx_spot"},
            {"id": 2, "symbol": "ZN", "asset_class": "bond_futures"},
        ]

        instruments = get_instruments(mock_conn)

        assert len(instruments) == 2
        assert instruments[0]["symbol"] == "EURUSD"

    def test_get_instruments_by_asset_class(self):
        """Test filtering instruments by asset class."""
        from lseg_toolkit.timeseries.storage import get_instruments

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": 1, "symbol": "EURUSD", "asset_class": "fx_spot"},
            {"id": 2, "symbol": "GBPUSD", "asset_class": "fx_spot"},
        ]

        instruments = get_instruments(mock_conn, AssetClass.FX_SPOT)

        assert len(instruments) == 2
        mock_cursor.execute.assert_called()


class TestSaveTimeseries:
    """Tests for timeseries save operations."""

    def test_save_timeseries_daily(self):
        """Test saving daily time series."""
        from lseg_toolkit.timeseries.storage import save_timeseries

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "open": [110.0, 110.5, 111.0, 110.5, 111.5],
                "high": [110.5, 111.0, 111.5, 111.0, 112.0],
                "low": [109.5, 110.0, 110.5, 110.0, 111.0],
                "close": [110.25, 110.75, 111.25, 110.75, 111.75],
            },
            index=dates,
        )

        rows = save_timeseries(
            mock_conn, 1, df, Granularity.DAILY, data_shape=DataShape.OHLCV
        )

        assert rows == 5

    def test_save_timeseries_with_volume(self):
        """Test saving time series with volume."""
        from lseg_toolkit.timeseries.storage import save_timeseries

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame(
            {
                "close": [100, 101, 102],
                "volume": [1000, 1100, 1200],
            },
            index=dates,
        )

        rows = save_timeseries(
            mock_conn, 1, df, Granularity.DAILY, data_shape=DataShape.OHLCV
        )

        assert rows == 3

    def test_save_timeseries_skips_rows_without_usable_close(self, monkeypatch):
        """OHLCV writer should skip volume-only rows with no price fields."""
        from lseg_toolkit.timeseries import storage

        captured: dict[str, object] = {}

        def fake_copy_with_upsert(conn, table, columns, buffer, conflict_columns):
            captured["table"] = table
            captured["columns"] = columns
            captured["payload"] = buffer.getvalue()
            return buffer.getvalue().count("\n")

        monkeypatch.setattr(storage.writer, "_copy_with_upsert", fake_copy_with_upsert)

        mock_conn = MagicMock()
        dates = pd.date_range("2024-01-01", periods=2, freq="h")
        df = pd.DataFrame(
            {
                "close": [100.0, pd.NA],
                "volume": [10, 20],
            },
            index=dates,
        )

        rows = storage.save_timeseries(
            mock_conn,
            1,
            df,
            Granularity.HOURLY,
            data_shape=DataShape.OHLCV,
        )

        assert rows == 1
        assert captured["table"] == "timeseries_ohlcv"
        assert captured["payload"].count("\n") == 1


class TestLoadTimeseries:
    """Tests for timeseries retrieval."""

    def test_load_timeseries_basic(self):
        """Test loading time series data."""
        from lseg_toolkit.timeseries.storage import load_timeseries

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Mock instrument lookup
        mock_cursor.fetchone.side_effect = [
            {"id": 1, "data_shape": "ohlcv"},  # get_instrument_by_ric result
        ]

        # Mock timeseries data - returns list of dicts
        mock_cursor.fetchall.return_value = [
            {"ts": pd.Timestamp("2024-01-01"), "close": 100.0},
            {"ts": pd.Timestamp("2024-01-02"), "close": 101.0},
        ]

        load_timeseries(mock_conn, "ZN")

        # Check cursor was called
        mock_cursor.execute.assert_called()

    def test_load_timeseries_not_found(self):
        """Test loading non-existent instrument."""
        from lseg_toolkit.timeseries.storage import load_timeseries

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None  # Instrument not found

        df = load_timeseries(mock_conn, "NOTFOUND")

        assert df.empty


class TestGetDataRange:
    """Tests for data range queries."""

    def test_get_data_range_with_data(self):
        """Test getting date range for instrument with data."""
        from lseg_toolkit.timeseries.storage import get_data_range

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchone.side_effect = [
            {"id": 1, "data_shape": "ohlcv"},  # get_instrument_by_ric
            {"min": date(2024, 1, 1), "max": date(2024, 1, 31)},
        ]

        min_date, max_date = get_data_range(mock_conn, "ZN")

        assert min_date == date(2024, 1, 1)
        assert max_date == date(2024, 1, 31)

    def test_get_data_range_no_data(self):
        """Test getting range for instrument with no data."""
        from lseg_toolkit.timeseries.storage import get_data_range

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchone.side_effect = [
            {"id": 1, "data_shape": "ohlcv"},  # get_instrument_by_ric
            {"min": None, "max": None},  # No data
        ]

        min_date, max_date = get_data_range(mock_conn, "ZN")

        assert min_date is None
        assert max_date is None


class TestRollEvents:
    """Tests for roll event operations."""

    def test_save_roll_event(self):
        """Test saving a roll event."""
        from lseg_toolkit.timeseries.storage import save_roll_event

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.side_effect = [
            {"id": 1},  # get_instrument_id
            {"id": 1},  # insert result
        ]

        roll_id = save_roll_event(
            mock_conn,
            continuous_symbol="ZN",
            roll_date=date(2024, 3, 15),
            from_contract="TYH24",
            to_contract="TYM24",
            from_price=110.0,
            to_price=110.5,
            roll_method="volume",
        )

        assert roll_id == 1

    def test_get_roll_events(self):
        """Test retrieving roll events."""
        from lseg_toolkit.timeseries.storage import get_roll_events

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchone.return_value = {"id": 1}  # get_instrument_id
        mock_cursor.fetchall.return_value = [
            {
                "roll_date": date(2024, 3, 15),
                "from_contract": "TYH24",
                "to_contract": "TYM24",
            },
            {
                "roll_date": date(2024, 6, 15),
                "from_contract": "TYM24",
                "to_contract": "TYU24",
            },
        ]

        events = get_roll_events(mock_conn, "ZN")

        assert len(events) == 2
        assert events[0]["from_contract"] == "TYH24"

    def test_get_roll_events_empty(self):
        """Test getting roll events when none exist."""
        from lseg_toolkit.timeseries.storage import get_roll_events

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchone.return_value = {"id": 1}  # get_instrument_id
        mock_cursor.fetchall.return_value = []

        events = get_roll_events(mock_conn, "ZN")

        assert events == []


class TestDataShape:
    """Tests for data shape utilities."""

    def test_get_data_shape_futures(self):
        """Test data shape for futures."""
        from lseg_toolkit.timeseries.storage import get_data_shape

        shape = get_data_shape(AssetClass.BOND_FUTURES)
        assert shape == DataShape.OHLCV

    def test_get_data_shape_fx(self):
        """Test data shape for FX spot."""
        from lseg_toolkit.timeseries.storage import get_data_shape

        shape = get_data_shape(AssetClass.FX_SPOT)
        assert shape == DataShape.QUOTE

    def test_get_data_shape_ois(self):
        """Test data shape for OIS."""
        from lseg_toolkit.timeseries.storage import get_data_shape

        shape = get_data_shape(AssetClass.OIS)
        assert shape == DataShape.RATE

    def test_get_data_shape_govt_yield(self):
        """Test data shape for government yields."""
        from lseg_toolkit.timeseries.storage import get_data_shape

        shape = get_data_shape(AssetClass.GOVT_YIELD)
        assert shape == DataShape.BOND

    def test_get_data_shape_fixing(self):
        """Test data shape for fixings."""
        from lseg_toolkit.timeseries.storage import get_data_shape

        shape = get_data_shape(AssetClass.FIXING)
        assert shape == DataShape.FIXING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
