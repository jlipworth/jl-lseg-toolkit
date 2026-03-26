"""Parquet storage module for Bloomberg data extraction.

This module provides a unified interface for storing and retrieving
time series data from Bloomberg extractions. It supports:

- Single-file storage with append/merge capability
- Daily partitioned files
- Deduplication based on key columns
- Schema validation and evolution
- Metadata tracking

Usage:
    from bloomberg_scripts.common.storage import ParquetStore

    # Create a store for bond basis data
    store = ParquetStore(
        base_dir="data/bloomberg/bond_basis",
        name="ctd_basis",
        key_columns=["date", "contract"],
    )

    # Write new data (appends and deduplicates)
    store.write(df)

    # Read all data
    df = store.read()

    # Read date range
    df = store.read(start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pandas as pd

logger = logging.getLogger(__name__)


class StorageMode(Enum):
    """Storage mode for parquet files."""

    SINGLE_FILE = "single"  # One file, append/merge new data
    DAILY_FILES = "daily"  # Separate file per extraction date
    PARTITIONED = "partitioned"  # Hive-style partitioning by columns


@dataclass
class StorageConfig:
    """Configuration for parquet storage."""

    compression: str = "snappy"  # snappy, gzip, zstd, none
    row_group_size: int = 100_000  # Rows per row group
    use_dictionary: bool = True  # Use dictionary encoding for strings
    write_statistics: bool = True  # Write column statistics
    coerce_timestamps: str = "us"  # Timestamp precision: us, ms, ns


@dataclass
class WriteResult:
    """Result of a write operation."""

    path: Path
    rows_written: int
    rows_before: int
    rows_after: int
    rows_deduplicated: int
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def rows_added(self) -> int:
        """Net rows added after deduplication."""
        return self.rows_after - self.rows_before


class ParquetStore:
    """Parquet storage manager for time series data.

    Provides read/write/append operations with automatic deduplication
    based on key columns.
    """

    def __init__(
        self,
        base_dir: str | Path,
        name: str,
        key_columns: Sequence[str] | None = None,
        date_column: str = "date",
        mode: StorageMode = StorageMode.SINGLE_FILE,
        config: StorageConfig | None = None,
    ) -> None:
        """Initialize parquet store.

        Args:
            base_dir: Base directory for data files
            name: Base name for files (e.g., 'ctd_basis')
            key_columns: Columns that uniquely identify a row (for deduplication)
            date_column: Column containing dates (for filtering and partitioning)
            mode: Storage mode (single file, daily files, or partitioned)
            config: Storage configuration options
        """
        self.base_dir = Path(base_dir)
        self.name = name
        self.key_columns = list(key_columns) if key_columns else None
        self.date_column = date_column
        self.mode = mode
        self.config = config or StorageConfig()

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def file_path(self) -> Path:
        """Primary file path for single-file mode."""
        return self.base_dir / f"{self.name}.parquet"

    def _daily_file_path(self, dt: date) -> Path:
        """Get file path for a specific date in daily mode."""
        return self.base_dir / f"{self.name}_{dt.isoformat()}.parquet"

    def _get_all_files(self) -> list[Path]:
        """Get all parquet files for this store."""
        if self.mode == StorageMode.SINGLE_FILE:
            if self.file_path.exists():
                return [self.file_path]
            return []
        elif self.mode == StorageMode.DAILY_FILES:
            pattern = f"{self.name}_*.parquet"
            return sorted(self.base_dir.glob(pattern))
        else:
            # Partitioned mode - find all parquet files recursively
            return sorted(self.base_dir.rglob("*.parquet"))

    def exists(self) -> bool:
        """Check if any data exists."""
        return len(self._get_all_files()) > 0

    def read(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        columns: Sequence[str] | None = None,
        filters: list[tuple] | None = None,
    ) -> "pd.DataFrame":
        """Read data from store.

        Args:
            start_date: Filter to data on or after this date
            end_date: Filter to data on or before this date
            columns: Specific columns to read (None for all)
            filters: PyArrow filter expressions

        Returns:
            DataFrame with requested data
        """
        import pandas as pd

        files = self._get_all_files()
        if not files:
            logger.debug("No files found for %s", self.name)
            return pd.DataFrame()

        # Build filters
        arrow_filters = list(filters) if filters else []

        if start_date and self.date_column:
            arrow_filters.append((self.date_column, ">=", start_date))
        if end_date and self.date_column:
            arrow_filters.append((self.date_column, "<=", end_date))

        # Read files
        dfs = []
        for file_path in files:
            try:
                table = pq.read_table(
                    file_path,
                    columns=columns,
                    filters=arrow_filters if arrow_filters else None,
                )
                dfs.append(table.to_pandas())
            except Exception as e:
                logger.warning("Error reading %s: %s", file_path, e)

        if not dfs:
            return pd.DataFrame()

        df = pd.concat(dfs, ignore_index=True)

        # Sort by date if present
        if self.date_column and self.date_column in df.columns:
            df = df.sort_values(self.date_column).reset_index(drop=True)

        return df

    def write(
        self,
        df: "pd.DataFrame",
        deduplicate: bool = True,
        extraction_date: date | None = None,
    ) -> WriteResult:
        """Write data to store.

        For SINGLE_FILE mode: appends to existing file with deduplication.
        For DAILY_FILES mode: writes to date-specific file.

        Args:
            df: DataFrame to write
            deduplicate: Remove duplicates based on key_columns
            extraction_date: Date for daily file naming (default: today)

        Returns:
            WriteResult with operation details
        """
        import pandas as pd

        if df.empty:
            logger.warning("Empty DataFrame, nothing to write")
            return WriteResult(
                path=self.file_path,
                rows_written=0,
                rows_before=0,
                rows_after=0,
                rows_deduplicated=0,
            )

        if extraction_date is None:
            extraction_date = date.today()

        # Determine output path and handle existing data
        existing_df: pd.DataFrame | None = None
        if self.mode == StorageMode.DAILY_FILES:
            output_path = self._daily_file_path(extraction_date)
            rows_before = 0  # Daily files are standalone
        else:
            output_path = self.file_path
            # Read existing data for merge
            if self.exists():
                existing_df = self.read()
                rows_before = len(existing_df)
            else:
                rows_before = 0

        # Merge with existing data for single-file mode
        if self.mode == StorageMode.SINGLE_FILE and existing_df is not None and rows_before > 0:
            df = pd.concat([existing_df, df], ignore_index=True)

        # Deduplicate
        rows_deduplicated = 0
        if deduplicate and self.key_columns:
            rows_before_dedup = len(df)
            df = df.drop_duplicates(subset=self.key_columns, keep="last")
            rows_deduplicated = rows_before_dedup - len(df)
            if rows_deduplicated > 0:
                logger.debug("Deduplicated %d rows", rows_deduplicated)

        # Sort by date if present
        if self.date_column and self.date_column in df.columns:
            df = df.sort_values(self.date_column).reset_index(drop=True)

        # Write to parquet
        self._write_parquet(df, output_path)

        result = WriteResult(
            path=output_path,
            rows_written=len(df),
            rows_before=rows_before,
            rows_after=len(df),
            rows_deduplicated=rows_deduplicated,
        )

        logger.info(
            "Wrote %d rows to %s (added %d, deduplicated %d)",
            result.rows_written,
            output_path.name,
            result.rows_added,
            result.rows_deduplicated,
        )

        return result

    def append(
        self,
        df: "pd.DataFrame",
        deduplicate: bool = True,
    ) -> WriteResult:
        """Append data to store (alias for write with merge semantics).

        Args:
            df: DataFrame to append
            deduplicate: Remove duplicates based on key_columns

        Returns:
            WriteResult with operation details
        """
        return self.write(df, deduplicate=deduplicate)

    def _write_parquet(self, df: "pd.DataFrame", path: Path) -> None:
        """Write DataFrame to parquet file with configured options."""
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to PyArrow table
        table = pa.Table.from_pandas(df, preserve_index=False)

        # Write with configuration
        pq.write_table(
            table,
            path,
            compression=self.config.compression,
            row_group_size=self.config.row_group_size,
            use_dictionary=self.config.use_dictionary,
            write_statistics=self.config.write_statistics,
            coerce_timestamps=self.config.coerce_timestamps,
        )

    def get_schema(self) -> pa.Schema | None:
        """Get schema from existing data."""
        files = self._get_all_files()
        if not files:
            return None
        return pq.read_schema(files[0])

    def get_date_range(self) -> tuple[date | None, date | None]:
        """Get min/max dates in store."""
        df = self.read(columns=[self.date_column] if self.date_column else None)
        if df.empty or self.date_column not in df.columns:
            return None, None

        dates = df[self.date_column]
        # Handle both date and datetime types
        if hasattr(dates.min(), "date"):
            return dates.min().date(), dates.max().date()
        return dates.min(), dates.max()

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        files = self._get_all_files()

        total_size = sum(f.stat().st_size for f in files)
        total_rows = 0

        for f in files:
            try:
                metadata = pq.read_metadata(f)
                total_rows += metadata.num_rows
            except Exception:
                pass

        date_range = self.get_date_range()

        return {
            "name": self.name,
            "mode": self.mode.value,
            "num_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_rows": total_rows,
            "date_range": date_range,
            "key_columns": self.key_columns,
        }

    def delete(self, before_date: date | None = None) -> int:
        """Delete data from store.

        Args:
            before_date: Delete data before this date (None = delete all)

        Returns:
            Number of rows deleted
        """
        import pandas as pd

        if before_date is None:
            # Delete all files
            files = self._get_all_files()
            for f in files:
                f.unlink()
            logger.info("Deleted %d files from %s", len(files), self.name)
            return -1  # Unknown row count

        if self.mode == StorageMode.SINGLE_FILE:
            # Read, filter, rewrite
            df = self.read()
            if df.empty:
                return 0

            rows_before = len(df)
            df = df[df[self.date_column] >= before_date]
            rows_deleted = rows_before - len(df)

            if rows_deleted > 0:
                if df.empty:
                    self.file_path.unlink(missing_ok=True)
                else:
                    self._write_parquet(df, self.file_path)

            return rows_deleted
        else:
            # Delete daily files before date
            deleted = 0
            for f in self._get_all_files():
                # Parse date from filename
                try:
                    date_str = f.stem.replace(f"{self.name}_", "")
                    file_date = date.fromisoformat(date_str)
                    if file_date < before_date:
                        f.unlink()
                        deleted += 1
                except ValueError:
                    continue
            logger.info("Deleted %d files before %s", deleted, before_date)
            return deleted


class MultiStore:
    """Manager for multiple related parquet stores.

    Useful for instruments that have multiple related datasets
    (e.g., futures prices + CTD data + basis data).
    """

    def __init__(
        self,
        base_dir: str | Path,
        stores: dict[str, dict[str, Any]],
    ) -> None:
        """Initialize multi-store manager.

        Args:
            base_dir: Base directory for all stores
            stores: Dict mapping store names to their configurations
                    Each config should have 'key_columns' and optionally
                    'date_column', 'mode', 'config'

        Example:
            stores = {
                "futures": {"key_columns": ["date", "contract"]},
                "ctd": {"key_columns": ["date", "contract"]},
                "basis": {"key_columns": ["date", "contract", "bond"]},
            }
            multi = MultiStore("data/bloomberg/bond_basis", stores)
        """
        self.base_dir = Path(base_dir)
        self._stores: dict[str, ParquetStore] = {}

        for name, config in stores.items():
            self._stores[name] = ParquetStore(
                base_dir=self.base_dir,
                name=name,
                key_columns=config.get("key_columns"),
                date_column=config.get("date_column", "date"),
                mode=config.get("mode", StorageMode.SINGLE_FILE),
                config=config.get("config"),
            )

    def __getitem__(self, name: str) -> ParquetStore:
        """Get store by name."""
        return self._stores[name]

    def __contains__(self, name: str) -> bool:
        """Check if store exists."""
        return name in self._stores

    @property
    def stores(self) -> dict[str, ParquetStore]:
        """Get all stores."""
        return self._stores

    def write_all(
        self,
        data: dict[str, "pd.DataFrame"],
        deduplicate: bool = True,
    ) -> dict[str, WriteResult]:
        """Write data to multiple stores.

        Args:
            data: Dict mapping store names to DataFrames
            deduplicate: Remove duplicates

        Returns:
            Dict mapping store names to WriteResults
        """
        results = {}
        for name, df in data.items():
            if name in self._stores:
                results[name] = self._stores[name].write(df, deduplicate=deduplicate)
            else:
                logger.warning("Unknown store: %s", name)
        return results

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats for all stores."""
        return {name: store.get_stats() for name, store in self._stores.items()}


def create_store(
    instrument: str,
    name: str,
    key_columns: Sequence[str],
    base_dir: str | Path | None = None,
    mode: StorageMode = StorageMode.SINGLE_FILE,
) -> ParquetStore:
    """Convenience function to create a store with standard settings.

    Args:
        instrument: Instrument type (e.g., 'bond_basis', 'jgb')
        name: Dataset name (e.g., 'ctd_basis', 'yields')
        key_columns: Columns for deduplication
        base_dir: Base directory (default: data/bloomberg)
        mode: Storage mode

    Returns:
        Configured ParquetStore instance
    """
    if base_dir is None:
        base_dir = Path("data/bloomberg")

    return ParquetStore(
        base_dir=Path(base_dir) / instrument,
        name=name,
        key_columns=key_columns,
        mode=mode,
    )
