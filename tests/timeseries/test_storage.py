"""Tests for timeseries storage layer."""

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lseg_toolkit.timeseries.enums import AssetClass, Granularity
from lseg_toolkit.timeseries.storage import (
    get_connection,
    get_data_range,
    get_instrument,
    get_instrument_id,
    get_instruments,
    get_roll_events,
    init_db,
    load_timeseries,
    save_instrument,
    save_roll_event,
    save_timeseries,
)


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_init_db_creates_file(self):
        """Test database file creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_db(str(db_path))
            assert db_path.exists()
            conn.close()

    def test_init_db_creates_nested_path(self):
        """Test database creation with nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "data" / "nested" / "test.db"
            conn = init_db(str(db_path))
            assert db_path.exists()
            conn.close()

    def test_init_db_creates_tables(self):
        """Test that all tables are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_db(str(db_path))

            # Check tables exist
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

            assert "instruments" in tables
            assert "ohlcv_daily" in tables
            assert "ohlcv_intraday" in tables
            assert "roll_events" in tables
            assert "extraction_log" in tables
            assert "futures_contracts" in tables
            assert "fx_spots" in tables
            assert "ois_rates" in tables

            conn.close()


class TestInstrumentCRUD:
    """Tests for instrument CRUD operations."""

    @pytest.fixture
    def db_conn(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_db(str(db_path))
            yield conn
            conn.close()

    def test_save_instrument_new(self, db_conn):
        """Test saving a new instrument."""
        inst_id = save_instrument(
            db_conn,
            symbol="ZN",
            name="10-Year T-Note",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYc1",
        )
        assert inst_id == 1

    def test_save_instrument_upsert(self, db_conn):
        """Test upserting an instrument."""
        # Save first time
        id1 = save_instrument(
            db_conn,
            symbol="ZN",
            name="10-Year T-Note",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYc1",
        )

        # Upsert with updated name
        id2 = save_instrument(
            db_conn,
            symbol="ZN",
            name="Updated Name",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYc1",
        )

        assert id1 == id2  # Same ID

        # Check name was updated
        inst = get_instrument(db_conn, "ZN")
        assert inst["name"] == "Updated Name"

    def test_save_futures_with_details(self, db_conn):
        """Test saving futures with contract details."""
        inst_id = save_instrument(
            db_conn,
            symbol="TYH25",
            name="10-Year T-Note Mar 2025",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYH5",
            underlying="TY",
            expiry_month="H",
            expiry_year=25,
            continuous_type="discrete",
        )
        assert inst_id > 0

    def test_save_fx_with_details(self, db_conn):
        """Test saving FX with currency details."""
        inst_id = save_instrument(
            db_conn,
            symbol="EURUSD",
            name="EUR/USD",
            asset_class=AssetClass.FX_SPOT,
            lseg_ric="EUR=",
            base_currency="EUR",
            quote_currency="USD",
            pip_size=0.0001,
        )
        assert inst_id > 0

    def test_save_ois_with_details(self, db_conn):
        """Test saving OIS with rate details."""
        inst_id = save_instrument(
            db_conn,
            symbol="USD1MOIS",
            name="USD 1M OIS",
            asset_class=AssetClass.OIS,
            lseg_ric="USD1MOIS=",
            currency="USD",
            tenor="1M",
            reference_rate="SOFR",
        )
        assert inst_id > 0

    def test_get_instrument(self, db_conn):
        """Test retrieving an instrument."""
        save_instrument(
            db_conn,
            symbol="ZN",
            name="10-Year T-Note",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYc1",
        )

        inst = get_instrument(db_conn, "ZN")
        assert inst is not None
        assert inst["symbol"] == "ZN"
        assert inst["name"] == "10-Year T-Note"
        assert inst["asset_class"] == "bond_futures"
        assert inst["lseg_ric"] == "TYc1"

    def test_get_instrument_not_found(self, db_conn):
        """Test retrieving non-existent instrument."""
        inst = get_instrument(db_conn, "NOTFOUND")
        assert inst is None

    def test_get_instrument_id(self, db_conn):
        """Test getting instrument ID."""
        save_instrument(
            db_conn,
            symbol="ZN",
            name="10-Year T-Note",
            asset_class=AssetClass.BOND_FUTURES,
            lseg_ric="TYc1",
        )

        inst_id = get_instrument_id(db_conn, "ZN")
        assert inst_id == 1

        inst_id = get_instrument_id(db_conn, "NOTFOUND")
        assert inst_id is None

    def test_get_instruments_all(self, db_conn):
        """Test retrieving all instruments."""
        save_instrument(db_conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1")
        save_instrument(db_conn, "EURUSD", "EUR/USD", AssetClass.FX_SPOT, "EUR=")

        instruments = get_instruments(db_conn)
        assert len(instruments) == 2
        assert instruments[0]["symbol"] == "EURUSD"  # Sorted alphabetically
        assert instruments[1]["symbol"] == "ZN"

    def test_get_instruments_by_asset_class(self, db_conn):
        """Test filtering instruments by asset class."""
        save_instrument(db_conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1")
        save_instrument(db_conn, "EURUSD", "EUR/USD", AssetClass.FX_SPOT, "EUR=")
        save_instrument(db_conn, "GBPUSD", "GBP/USD", AssetClass.FX_SPOT, "GBP=")

        fx_instruments = get_instruments(db_conn, AssetClass.FX_SPOT)
        assert len(fx_instruments) == 2
        assert all(i["asset_class"] == "fx_spot" for i in fx_instruments)


class TestTimeSeriesCRUD:
    """Tests for time series CRUD operations."""

    @pytest.fixture
    def db_with_instrument(self):
        """Create database with an instrument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_db(str(db_path))
            inst_id = save_instrument(
                conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1"
            )
            yield conn, inst_id
            conn.close()

    def test_save_timeseries_daily(self, db_with_instrument):
        """Test saving daily time series."""
        conn, inst_id = db_with_instrument

        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "open": [110.0, 110.5, 111.0, 110.5, 111.5],
                "high": [110.5, 111.0, 111.5, 111.0, 112.0],
                "low": [109.5, 110.0, 110.5, 110.0, 111.0],
                "close": [110.25, 110.75, 111.25, 110.75, 111.75],
                "volume": [100000, 120000, 110000, 90000, 130000],
            },
            index=dates,
        )

        rows = save_timeseries(conn, inst_id, df, Granularity.DAILY)
        assert rows == 5

    def test_save_timeseries_upsert(self, db_with_instrument):
        """Test upserting time series data."""
        conn, inst_id = db_with_instrument

        # Save initial data
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        df1 = pd.DataFrame({"close": [100, 101, 102]}, index=dates)
        save_timeseries(conn, inst_id, df1, Granularity.DAILY)

        # Upsert with updated values
        df2 = pd.DataFrame({"close": [100.5, 101.5, 102.5]}, index=dates)
        save_timeseries(conn, inst_id, df2, Granularity.DAILY)

        # Check values were updated
        loaded = load_timeseries(conn, "ZN")
        assert len(loaded) == 3
        assert loaded["close"].iloc[0] == 100.5

    def test_load_timeseries_all(self, db_with_instrument):
        """Test loading all time series data."""
        conn, inst_id = db_with_instrument

        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame({"close": range(10)}, index=dates)
        save_timeseries(conn, inst_id, df, Granularity.DAILY)

        loaded = load_timeseries(conn, "ZN")
        assert len(loaded) == 10
        assert "close" in loaded.columns

    def test_load_timeseries_date_filter(self, db_with_instrument):
        """Test loading time series with date filter."""
        conn, inst_id = db_with_instrument

        dates = pd.date_range("2024-01-01", periods=31, freq="D")
        df = pd.DataFrame({"close": range(31)}, index=dates)
        save_timeseries(conn, inst_id, df, Granularity.DAILY)

        # Load subset
        loaded = load_timeseries(
            conn,
            "ZN",
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 20),
        )
        assert len(loaded) == 11
        assert loaded.index.min().date() == date(2024, 1, 10)
        assert loaded.index.max().date() == date(2024, 1, 20)

    def test_load_timeseries_not_found(self, db_with_instrument):
        """Test loading non-existent instrument."""
        conn, _ = db_with_instrument
        loaded = load_timeseries(conn, "NOTFOUND")
        assert loaded.empty

    def test_get_data_range(self, db_with_instrument):
        """Test getting data date range."""
        conn, inst_id = db_with_instrument

        dates = pd.date_range("2024-01-15", periods=20, freq="D")
        df = pd.DataFrame({"close": range(20)}, index=dates)
        save_timeseries(conn, inst_id, df, Granularity.DAILY)

        min_date, max_date = get_data_range(conn, "ZN")
        assert min_date == date(2024, 1, 15)
        assert max_date == date(2024, 2, 3)

    def test_get_data_range_no_data(self, db_with_instrument):
        """Test getting range for empty instrument."""
        conn, _ = db_with_instrument
        min_date, max_date = get_data_range(conn, "ZN")
        assert min_date is None
        assert max_date is None


class TestRollEvents:
    """Tests for roll event operations."""

    @pytest.fixture
    def db_with_continuous(self):
        """Create database with continuous instrument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = init_db(str(db_path))
            save_instrument(
                conn, "ZN", "10-Year Continuous", AssetClass.BOND_FUTURES, "TYc1"
            )
            yield conn
            conn.close()

    def test_save_roll_event(self, db_with_continuous):
        """Test saving a roll event."""
        conn = db_with_continuous
        roll_id = save_roll_event(
            conn,
            continuous_symbol="ZN",
            roll_date=date(2024, 3, 15),
            from_contract="TYH24",
            to_contract="TYM24",
            from_price=110.0,
            to_price=110.5,
            roll_method="volume_switch",
        )
        assert roll_id == 1

    def test_get_roll_events(self, db_with_continuous):
        """Test retrieving roll events."""
        conn = db_with_continuous

        # Save multiple roll events
        save_roll_event(
            conn, "ZN", date(2024, 3, 15), "TYH24", "TYM24", 110.0, 110.5, "volume"
        )
        save_roll_event(
            conn, "ZN", date(2024, 6, 15), "TYM24", "TYU24", 111.0, 111.3, "volume"
        )

        events = get_roll_events(conn, "ZN")
        assert len(events) == 2
        assert events[0]["from_contract"] == "TYH24"
        assert events[1]["from_contract"] == "TYM24"

    def test_get_roll_events_empty(self, db_with_continuous):
        """Test getting roll events for instrument with none."""
        conn = db_with_continuous
        events = get_roll_events(conn, "ZN")
        assert events == []


class TestContextManager:
    """Tests for database context manager."""

    def test_get_connection_context(self):
        """Test context manager for connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with get_connection(str(db_path)) as conn:
                save_instrument(conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1")
                inst = get_instrument(conn, "ZN")
                assert inst is not None

            # Connection should be closed after context
            assert db_path.exists()
