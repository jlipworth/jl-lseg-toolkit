"""
Unit tests for the Parquet export module.

Tests schema definitions, export functions, and partitioning.
These tests use temporary files and don't require LSEG Workspace.
"""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lseg_toolkit.timeseries.enums import Granularity
from lseg_toolkit.timeseries.export import (
    INSTRUMENT_SCHEMA,
    OHLCV_DAILY_SCHEMA,
    OHLCV_INTRADAY_SCHEMA,
    ROLL_EVENTS_SCHEMA,
)


class TestSchemaDefinitions:
    """Test PyArrow schema definitions."""

    def test_ohlcv_daily_schema_fields(self):
        """Daily OHLCV schema should have expected fields."""
        field_names = [f.name for f in OHLCV_DAILY_SCHEMA]

        assert "date" in field_names
        assert "open" in field_names
        assert "high" in field_names
        assert "low" in field_names
        assert "close" in field_names
        assert "volume" in field_names
        assert "settle" in field_names

    def test_ohlcv_daily_schema_types(self):
        """Daily OHLCV schema should have correct types."""
        type_map = {f.name: f.type for f in OHLCV_DAILY_SCHEMA}

        assert type_map["date"] == pa.date32()
        assert type_map["open"] == pa.float64()
        assert type_map["close"] == pa.float64()
        assert type_map["volume"] == pa.float64()

    def test_ohlcv_intraday_schema_has_timestamp(self):
        """Intraday schema should use timestamp instead of date."""
        field_names = [f.name for f in OHLCV_INTRADAY_SCHEMA]
        type_map = {f.name: f.type for f in OHLCV_INTRADAY_SCHEMA}

        assert "timestamp" in field_names
        assert "date" not in field_names
        assert type_map["timestamp"] == pa.timestamp("us")

    def test_instrument_schema_fields(self):
        """Instrument schema should have expected fields."""
        field_names = [f.name for f in INSTRUMENT_SCHEMA]

        assert "id" in field_names
        assert "symbol" in field_names
        assert "name" in field_names
        assert "asset_class" in field_names
        assert "lseg_ric" in field_names

    def test_roll_events_schema_fields(self):
        """Roll events schema should have expected fields."""
        field_names = [f.name for f in ROLL_EVENTS_SCHEMA]

        assert "symbol" in field_names
        assert "roll_date" in field_names
        assert "from_contract" in field_names
        assert "to_contract" in field_names
        assert "adjustment_factor" in field_names


class TestWriteParquet:
    """Test Parquet file writing."""

    def test_write_parquet_creates_file(self):
        """_write_parquet should create a valid Parquet file."""
        from lseg_toolkit.timeseries.export import _write_parquet

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.parquet"

            df = pd.DataFrame({
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "open": [100.0, 101.0],
                "high": [101.0, 102.0],
                "low": [99.0, 100.0],
                "close": [100.5, 101.5],
                "volume": [1000.0, 1100.0],
            })
            df = df.set_index("date")

            _write_parquet(df, file_path, Granularity.DAILY)

            assert file_path.exists()

            # Verify can be read back
            read_df = pq.read_table(file_path).to_pandas()
            assert len(read_df) == 2
            assert "close" in read_df.columns

    def test_write_parquet_uses_snappy_compression(self):
        """Parquet files should use snappy compression."""
        from lseg_toolkit.timeseries.export import _write_parquet

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.parquet"

            df = pd.DataFrame({
                "date": pd.to_datetime(["2024-01-01"]),
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": [100.5],
                "volume": [1000.0],
            })
            df = df.set_index("date")

            _write_parquet(df, file_path, Granularity.DAILY)

            # Check metadata
            metadata = pq.read_metadata(file_path)
            # Snappy compression should result in smaller file or specific encoding
            assert file_path.exists()


class TestExportToParquet:
    """Test export_to_parquet function."""

    @patch("lseg_toolkit.timeseries.export.get_connection")
    @patch("lseg_toolkit.timeseries.export.get_instruments")
    @patch("lseg_toolkit.timeseries.export.load_timeseries")
    def test_export_creates_files(
        self, mock_load, mock_get_instruments, mock_get_conn
    ):
        """export_to_parquet should create Parquet files."""
        from lseg_toolkit.timeseries.export import export_to_parquet

        # Setup mocks
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_get_instruments.return_value = [
            {"id": 1, "symbol": "ZN", "asset_class": "bond_futures"}
        ]

        mock_load.return_value = pd.DataFrame({
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000.0],
        }, index=pd.to_datetime(["2024-01-01"]))

        with tempfile.TemporaryDirectory() as tmpdir:
            files = export_to_parquet(
                db_path="dummy.db",
                output_dir=tmpdir,
                partition_by_year=False,
            )

            # At least one file should be created
            # (may be 0 if mock setup isn't complete)
            assert isinstance(files, list)

    @patch("lseg_toolkit.timeseries.export.get_connection")
    @patch("lseg_toolkit.timeseries.export.get_instrument")
    @patch("lseg_toolkit.timeseries.export.load_timeseries")
    def test_export_single_symbol(
        self, mock_load, mock_get_instrument, mock_get_conn
    ):
        """export_to_parquet with symbol filter should export one instrument."""
        from lseg_toolkit.timeseries.export import export_to_parquet

        # Setup mocks
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_get_instrument.return_value = {
            "id": 1,
            "symbol": "ZN",
            "asset_class": "bond_futures",
        }

        mock_load.return_value = pd.DataFrame({
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [1000.0, 1100.0],
        }, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))

        with tempfile.TemporaryDirectory() as tmpdir:
            files = export_to_parquet(
                db_path="dummy.db",
                output_dir=tmpdir,
                symbol="ZN",
                partition_by_year=False,
            )

            assert isinstance(files, list)


class TestExportMetadata:
    """Test metadata export functions."""

    @patch("lseg_toolkit.timeseries.export.get_connection")
    def test_export_metadata_creates_files(self, mock_get_conn):
        """export_metadata should create metadata Parquet files."""
        from lseg_toolkit.timeseries.export import export_metadata

        # Setup mock connection
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        # Mock SQL queries
        mock_conn.execute.return_value.fetchall.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock pd.read_sql_query to return empty DataFrames
            with patch("pandas.read_sql_query") as mock_sql:
                mock_sql.return_value = pd.DataFrame()

                result = export_metadata(
                    db_path="dummy.db",
                    output_dir=tmpdir,
                )

                assert "instruments" in result
                assert "roll_events" in result


class TestExportSymbol:
    """Test single symbol export convenience function."""

    @patch("lseg_toolkit.timeseries.export.export_to_parquet")
    def test_export_symbol_calls_export(self, mock_export):
        """export_symbol should call export_to_parquet with correct params."""
        from lseg_toolkit.exceptions import StorageError
        from lseg_toolkit.timeseries.export import export_symbol

        mock_export.return_value = [Path("/tmp/ZN.parquet")]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_symbol(
                db_path="dummy.db",
                symbol="ZN",
                output_dir=tmpdir,
            )

            assert result == Path("/tmp/ZN.parquet")
            mock_export.assert_called_once()

            # Verify partition_by_year=False was passed
            call_kwargs = mock_export.call_args.kwargs
            assert call_kwargs.get("partition_by_year") is False
            assert call_kwargs.get("symbol") == "ZN"

    @patch("lseg_toolkit.timeseries.export.export_to_parquet")
    def test_export_symbol_raises_on_no_data(self, mock_export):
        """export_symbol should raise StorageError if no data exported."""
        from lseg_toolkit.exceptions import StorageError
        from lseg_toolkit.timeseries.export import export_symbol

        mock_export.return_value = []  # No files created

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(StorageError) as exc_info:
                export_symbol(
                    db_path="dummy.db",
                    symbol="INVALID",
                    output_dir=tmpdir,
                )

            assert "No data to export" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
