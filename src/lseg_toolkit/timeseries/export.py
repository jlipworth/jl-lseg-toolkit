"""
Parquet export layer for time series data.

Provides functions to export time series data and metadata to Parquet
format for C++/Rust interoperability.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.constants import DEFAULT_PARQUET_DIR
from lseg_toolkit.timeseries.enums import AssetClass, Granularity
from lseg_toolkit.timeseries.storage import (
    get_connection,
    get_instrument,
    get_instruments,
    load_timeseries,
)

# =============================================================================
# PyArrow Schemas
# =============================================================================

# OHLCV daily schema - optimized for C++/Rust consumption
OHLCV_DAILY_SCHEMA = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.float64()),
        pa.field("open_interest", pa.float64()),
        pa.field("settle", pa.float64()),
        pa.field("adjustment_factor", pa.float64()),
        pa.field("source_contract", pa.string()),
    ]
)

# OHLCV intraday schema
OHLCV_INTRADAY_SCHEMA = pa.schema(
    [
        pa.field("timestamp", pa.timestamp("us")),  # Microsecond precision
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.float64()),
    ]
)

# Instrument metadata schema
INSTRUMENT_SCHEMA = pa.schema(
    [
        pa.field("id", pa.int32()),
        pa.field("symbol", pa.string()),
        pa.field("name", pa.string()),
        pa.field("asset_class", pa.string()),
        pa.field("lseg_ric", pa.string()),
    ]
)

# Roll events schema
ROLL_EVENTS_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("roll_date", pa.date32()),
        pa.field("from_contract", pa.string()),
        pa.field("to_contract", pa.string()),
        pa.field("from_price", pa.float64()),
        pa.field("to_price", pa.float64()),
        pa.field("price_gap", pa.float64()),
        pa.field("adjustment_factor", pa.float64()),
        pa.field("roll_method", pa.string()),
    ]
)


# =============================================================================
# Export Functions
# =============================================================================


def export_to_parquet(
    db_path: str,
    output_dir: str = DEFAULT_PARQUET_DIR,
    symbol: str | None = None,
    asset_class: AssetClass | None = None,
    granularity: Granularity = Granularity.DAILY,
    start_date: date | None = None,
    end_date: date | None = None,
    partition_by_year: bool = True,
) -> list[Path]:
    """
    Export time series data to Parquet files.

    Args:
        db_path: Path to SQLite database.
        output_dir: Directory for Parquet output.
        symbol: Optional symbol to export (exports all if None).
        asset_class: Optional asset class filter.
        granularity: Data granularity.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        partition_by_year: Whether to partition by year.

    Returns:
        List of created Parquet file paths.

    Raises:
        StorageError: If export fails.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exported_files: list[Path] = []

    with get_connection(db_path) as conn:
        # Get instruments to export
        instruments: list[dict] = []
        if symbol:
            inst = get_instrument(conn, symbol)
            if inst is None:
                raise StorageError(f"Instrument not found: {symbol}")
            instruments = [inst]
        else:
            instruments = get_instruments(conn, asset_class)

        for inst in instruments:
            try:
                files = _export_instrument(
                    conn,
                    inst,
                    output_path,
                    granularity,
                    start_date,
                    end_date,
                    partition_by_year,
                )
                exported_files.extend(files)
            except Exception as e:
                raise StorageError(f"Failed to export {inst['symbol']}: {e}") from e

    return exported_files


def _export_instrument(
    conn: sqlite3.Connection,
    instrument: dict,
    output_path: Path,
    granularity: Granularity,
    start_date: date | None,
    end_date: date | None,
    partition_by_year: bool,
) -> list[Path]:
    """Export a single instrument to Parquet."""
    symbol = instrument["symbol"]
    asset_class = instrument["asset_class"]

    # Load data
    df = load_timeseries(conn, symbol, start_date, end_date, granularity)
    if df.empty:
        return []

    # Build output path
    granularity_dir = "daily" if granularity == Granularity.DAILY else "intraday"
    base_path = output_path / granularity_dir / asset_class

    exported: list[Path] = []

    if partition_by_year and granularity == Granularity.DAILY:
        # Partition by year
        df["year"] = pd.to_datetime(df.index).year
        for year, year_df in df.groupby("year"):
            year_path = base_path / f"year={year}"
            year_path.mkdir(parents=True, exist_ok=True)
            file_path = year_path / f"{symbol}.parquet"
            _write_parquet(year_df.drop(columns=["year"]), file_path, granularity)
            exported.append(file_path)
    else:
        # Single file
        base_path.mkdir(parents=True, exist_ok=True)
        file_path = base_path / f"{symbol}.parquet"
        _write_parquet(df, file_path, granularity)
        exported.append(file_path)

    return exported


def _write_parquet(df: pd.DataFrame, file_path: Path, granularity: Granularity) -> None:
    """Write DataFrame to Parquet with proper schema."""
    # Reset index to make date/timestamp a column
    df = df.reset_index()

    # Rename index column
    if "date" not in df.columns and "timestamp" not in df.columns:
        df.rename(columns={df.columns[0]: "date"}, inplace=True)

    # Convert date column to proper type
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    # Select schema
    schema = (
        OHLCV_DAILY_SCHEMA
        if granularity == Granularity.DAILY
        else OHLCV_INTRADAY_SCHEMA
    )

    # Filter to schema columns that exist
    schema_cols = [f.name for f in schema]
    df = df[[c for c in df.columns if c in schema_cols]]

    # Write with compression
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table,
        file_path,
        compression="snappy",
        use_dictionary=True,
        write_statistics=True,
    )


def export_metadata(
    db_path: str, output_dir: str = DEFAULT_PARQUET_DIR
) -> dict[str, Path]:
    """
    Export metadata tables to Parquet.

    Args:
        db_path: Path to SQLite database.
        output_dir: Directory for Parquet output.

    Returns:
        Dict mapping table name to file path.

    Raises:
        StorageError: If export fails.
    """
    output_path = Path(output_dir) / "metadata"
    output_path.mkdir(parents=True, exist_ok=True)

    exported: dict[str, Path] = {}

    with get_connection(db_path) as conn:
        # Export instruments
        instruments_path = output_path / "instruments.parquet"
        _export_instruments_metadata(conn, instruments_path)
        exported["instruments"] = instruments_path

        # Export roll events
        roll_events_path = output_path / "roll_events.parquet"
        _export_roll_events_metadata(conn, roll_events_path)
        exported["roll_events"] = roll_events_path

    return exported


def _export_instruments_metadata(conn: sqlite3.Connection, file_path: Path) -> None:
    """Export instruments table to Parquet."""
    df = pd.read_sql_query(
        "SELECT id, symbol, name, asset_class, lseg_ric FROM instruments ORDER BY symbol",
        conn,
    )
    if df.empty:
        return

    table = pa.Table.from_pandas(df, schema=INSTRUMENT_SCHEMA, preserve_index=False)
    pq.write_table(table, file_path, compression="snappy")


def _export_roll_events_metadata(conn: sqlite3.Connection, file_path: Path) -> None:
    """Export roll events with symbol join to Parquet."""
    df = pd.read_sql_query(
        """
        SELECT i.symbol, r.roll_date, r.from_contract, r.to_contract,
               r.from_price, r.to_price, r.price_gap, r.adjustment_factor,
               r.roll_method
        FROM roll_events r
        JOIN instruments i ON r.continuous_id = i.id
        ORDER BY i.symbol, r.roll_date
        """,
        conn,
    )
    if df.empty:
        # Write empty file with schema
        table = pa.Table.from_pydict(
            {f.name: [] for f in ROLL_EVENTS_SCHEMA}, schema=ROLL_EVENTS_SCHEMA
        )
        pq.write_table(table, file_path, compression="snappy")
        return

    df["roll_date"] = pd.to_datetime(df["roll_date"]).dt.date
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, file_path, compression="snappy")


# =============================================================================
# Convenience Functions
# =============================================================================


def export_symbol(
    db_path: str,
    symbol: str,
    output_dir: str = DEFAULT_PARQUET_DIR,
    granularity: Granularity = Granularity.DAILY,
) -> Path:
    """
    Export a single symbol to Parquet (no partitioning).

    Args:
        db_path: Path to SQLite database.
        symbol: Symbol to export.
        output_dir: Output directory.
        granularity: Data granularity.

    Returns:
        Path to created Parquet file.

    Raises:
        StorageError: If export fails or symbol not found.
    """
    files = export_to_parquet(
        db_path,
        output_dir,
        symbol=symbol,
        granularity=granularity,
        partition_by_year=False,
    )
    if not files:
        raise StorageError(f"No data to export for {symbol}")
    return files[0]


def export_all(
    db_path: str, output_dir: str = DEFAULT_PARQUET_DIR
) -> dict[str, list[Path]]:
    """
    Export all data and metadata to Parquet.

    Args:
        db_path: Path to SQLite database.
        output_dir: Output directory.

    Returns:
        Dict with 'data' and 'metadata' keys containing file lists.
    """
    data_files = export_to_parquet(db_path, output_dir)
    metadata = export_metadata(db_path, output_dir)
    return {"data": data_files, "metadata": list(metadata.values())}
