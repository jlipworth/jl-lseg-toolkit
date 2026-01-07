"""Tests for DuckDB timeseries storage layer."""

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lseg_toolkit.timeseries.duckdb_storage import (
    create_extraction_progress,
    export_symbol_to_parquet,
    export_to_parquet,
    get_connection,
    get_data_coverage,
    get_data_range,
    get_extraction_progress,
    get_instrument,
    get_instrument_id,
    get_instruments,
    get_roll_events,
    init_db,
    load_timeseries,
    log_extraction,
    save_instrument,
    save_roll_event,
    save_timeseries,
    update_extraction_progress,
)
from lseg_toolkit.timeseries.enums import AssetClass, Granularity


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_init_db_creates_file(self):
        """Test database file creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = init_db(str(db_path))
            assert db_path.exists()
            conn.close()

    def test_init_db_creates_nested_path(self):
        """Test database creation with nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "data" / "nested" / "test.duckdb"
            conn = init_db(str(db_path))
            assert db_path.exists()
            conn.close()

    def test_init_db_creates_tables(self):
        """Test that all tables are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = init_db(str(db_path))

            # Check tables exist
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
            ).fetchall()
            table_names = [t[0] for t in tables]

            assert "instruments" in table_names
            assert "ohlcv_daily" in table_names
            assert "ohlcv_intraday" in table_names
            assert "roll_events" in table_names
            assert "extraction_log" in table_names
            assert "extraction_progress" in table_names
            assert "futures_contracts" in table_names
            assert "fx_spots" in table_names
            assert "ois_rates" in table_names

            conn.close()

    def test_init_db_creates_view(self):
        """Test that data_coverage view is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = init_db(str(db_path))

            # Check view exists by querying it
            result = conn.execute("SELECT * FROM data_coverage").fetchdf()
            assert result is not None

            conn.close()


class TestInstrumentCRUD:
    """Tests for instrument CRUD operations."""

    @pytest.fixture
    def db_conn(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
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
            db_path = Path(tmpdir) / "test.duckdb"
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
            db_path = Path(tmpdir) / "test.duckdb"
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


class TestExtractionProgress:
    """Tests for extraction progress tracking."""

    @pytest.fixture
    def db_conn(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = init_db(str(db_path))
            yield conn
            conn.close()

    def test_create_extraction_progress(self, db_conn):
        """Test creating extraction progress record."""
        progress_id = create_extraction_progress(
            db_conn,
            asset_class="bond_futures",
            instrument="ZN",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert progress_id == 1

    def test_update_extraction_progress_running(self, db_conn):
        """Test updating progress to running."""
        progress_id = create_extraction_progress(
            db_conn,
            asset_class="bond_futures",
            instrument="ZN",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        update_extraction_progress(db_conn, progress_id, "running")

        records = get_extraction_progress(db_conn, status="running")
        assert len(records) == 1
        assert records[0]["started_at"] is not None

    def test_update_extraction_progress_complete(self, db_conn):
        """Test updating progress to complete."""
        progress_id = create_extraction_progress(
            db_conn,
            asset_class="bond_futures",
            instrument="ZN",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        update_extraction_progress(db_conn, progress_id, "complete", rows_fetched=250)

        records = get_extraction_progress(db_conn, status="complete")
        assert len(records) == 1
        assert records[0]["rows_fetched"] == 250
        assert records[0]["completed_at"] is not None

    def test_update_extraction_progress_failed(self, db_conn):
        """Test updating progress to failed."""
        progress_id = create_extraction_progress(
            db_conn,
            asset_class="bond_futures",
            instrument="ZN",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        update_extraction_progress(
            db_conn, progress_id, "failed", error_message="API timeout"
        )

        records = get_extraction_progress(db_conn, status="failed")
        assert len(records) == 1
        assert records[0]["error_message"] == "API timeout"

    def test_get_extraction_progress_filters(self, db_conn):
        """Test filtering extraction progress."""
        create_extraction_progress(
            db_conn, "bond_futures", "ZN", date(2024, 1, 1), date(2024, 6, 30)
        )
        create_extraction_progress(
            db_conn, "bond_futures", "ZB", date(2024, 1, 1), date(2024, 6, 30)
        )
        create_extraction_progress(
            db_conn, "fx_spot", "EURUSD", date(2024, 1, 1), date(2024, 6, 30)
        )

        # Filter by asset class
        futures = get_extraction_progress(db_conn, asset_class="bond_futures")
        assert len(futures) == 2

        # Filter by instrument
        zn = get_extraction_progress(db_conn, instrument="ZN")
        assert len(zn) == 1
        assert zn[0]["instrument"] == "ZN"


class TestDataCoverage:
    """Tests for data coverage view."""

    @pytest.fixture
    def db_with_data(self):
        """Create database with data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = init_db(str(db_path))

            # Create instruments
            zn_id = save_instrument(
                conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1"
            )
            eur_id = save_instrument(
                conn, "EURUSD", "EUR/USD", AssetClass.FX_SPOT, "EUR="
            )

            # Add data
            dates_zn = pd.date_range("2024-01-01", periods=100, freq="D")
            df_zn = pd.DataFrame({"close": range(100)}, index=dates_zn)
            save_timeseries(conn, zn_id, df_zn, Granularity.DAILY)

            dates_eur = pd.date_range("2024-03-01", periods=50, freq="D")
            df_eur = pd.DataFrame({"close": range(50)}, index=dates_eur)
            save_timeseries(conn, eur_id, df_eur, Granularity.DAILY)

            yield conn
            conn.close()

    def test_get_data_coverage(self, db_with_data):
        """Test getting data coverage summary."""
        coverage = get_data_coverage(db_with_data)
        assert len(coverage) == 2

        zn_row = coverage[coverage["symbol"] == "ZN"].iloc[0]
        assert zn_row["days"] == 100

        eur_row = coverage[coverage["symbol"] == "EURUSD"].iloc[0]
        assert eur_row["days"] == 50


class TestExtractionLogging:
    """Tests for extraction logging."""

    @pytest.fixture
    def db_with_instrument(self):
        """Create database with instrument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = init_db(str(db_path))
            save_instrument(conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1")
            yield conn
            conn.close()

    def test_log_extraction(self, db_with_instrument):
        """Test logging an extraction."""
        conn = db_with_instrument
        log_extraction(
            conn,
            symbol="ZN",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            granularity=Granularity.DAILY,
            rows_fetched=250,
        )

        result = conn.execute(
            "SELECT rows_fetched FROM extraction_log WHERE instrument_id = 1"
        ).fetchone()
        assert result is not None
        assert result[0] == 250  # rows_fetched


class TestParquetExport:
    """Tests for Parquet export functionality."""

    @pytest.fixture
    def db_with_data(self):
        """Create database with data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = init_db(str(db_path))

            zn_id = save_instrument(
                conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1"
            )

            dates = pd.date_range("2024-01-01", periods=100, freq="D")
            df = pd.DataFrame(
                {
                    "open": range(100, 200),
                    "high": range(101, 201),
                    "low": range(99, 199),
                    "close": range(100, 200),
                    "volume": range(1000, 1100),
                },
                index=dates,
            )
            save_timeseries(conn, zn_id, df, Granularity.DAILY)

            yield conn, tmpdir
            conn.close()

    def test_export_to_parquet(self, db_with_data):
        """Test exporting data to Parquet."""
        conn, tmpdir = db_with_data
        output_path = Path(tmpdir) / "export" / "test.parquet"

        result_path = export_to_parquet(conn, str(output_path), symbol="ZN")
        assert Path(result_path).exists()

        # Verify content
        df = pd.read_parquet(result_path)
        assert len(df) == 100
        assert "symbol" in df.columns
        assert "close" in df.columns

    def test_export_symbol_to_parquet(self, db_with_data):
        """Test exporting symbol to Parquet with partitioning."""
        conn, tmpdir = db_with_data
        output_dir = Path(tmpdir) / "export"

        files = export_symbol_to_parquet(conn, "ZN", str(output_dir))
        assert len(files) == 1  # Single year of data
        assert Path(files[0]).exists()
        assert "2024" in files[0]

        # Verify content
        df = pd.read_parquet(files[0])
        assert len(df) == 100

    def test_export_symbol_no_partition(self, db_with_data):
        """Test exporting symbol without partitioning."""
        conn, tmpdir = db_with_data
        output_dir = Path(tmpdir) / "export"

        files = export_symbol_to_parquet(
            conn, "ZN", str(output_dir), partition_by_year=False
        )
        assert len(files) == 1
        assert "ZN.parquet" in files[0]


class TestContextManager:
    """Tests for database context manager."""

    def test_get_connection_context(self):
        """Test context manager for connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with get_connection(str(db_path)) as conn:
                save_instrument(conn, "ZN", "10-Year", AssetClass.BOND_FUTURES, "TYc1")
                inst = get_instrument(conn, "ZN")
                assert inst is not None

            # Connection should be closed after context
            assert db_path.exists()
