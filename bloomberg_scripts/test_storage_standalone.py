#!/usr/bin/env python3
"""Standalone test for ParquetStore - no package imports needed.

Dependencies:
    pip install pandas pyarrow

Usage:
    python test_storage_standalone.py
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# STORAGE MODULE (embedded for standalone testing)
# ============================================================================


class StorageMode(Enum):
    """Storage mode for parquet files."""
    SINGLE_FILE = "single"
    DAILY_FILES = "daily"


@dataclass
class StorageConfig:
    """Configuration for parquet storage."""
    compression: str = "snappy"
    row_group_size: int = 100_000


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
        return self.rows_after - self.rows_before


class ParquetStore:
    """Parquet storage manager for time series data."""

    def __init__(
        self,
        base_dir: str | Path,
        name: str,
        key_columns: Sequence[str] | None = None,
        date_column: str = "date",
        mode: StorageMode = StorageMode.SINGLE_FILE,
        config: StorageConfig | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.name = name
        self.key_columns = list(key_columns) if key_columns else None
        self.date_column = date_column
        self.mode = mode
        self.config = config or StorageConfig()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def file_path(self) -> Path:
        return self.base_dir / f"{self.name}.parquet"

    def _daily_file_path(self, dt: date) -> Path:
        return self.base_dir / f"{self.name}_{dt.isoformat()}.parquet"

    def _get_all_files(self) -> list[Path]:
        if self.mode == StorageMode.SINGLE_FILE:
            return [self.file_path] if self.file_path.exists() else []
        else:
            return sorted(self.base_dir.glob(f"{self.name}_*.parquet"))

    def exists(self) -> bool:
        return len(self._get_all_files()) > 0

    def read(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        columns: Sequence[str] | None = None,
    ) -> pd.DataFrame:
        files = self._get_all_files()
        if not files:
            return pd.DataFrame()

        filters = []
        if start_date and self.date_column:
            filters.append((self.date_column, ">=", start_date))
        if end_date and self.date_column:
            filters.append((self.date_column, "<=", end_date))

        dfs = []
        for file_path in files:
            try:
                table = pq.read_table(
                    file_path,
                    columns=columns,
                    filters=filters if filters else None,
                )
                dfs.append(table.to_pandas())
            except Exception as e:
                logger.warning("Error reading %s: %s", file_path, e)

        if not dfs:
            return pd.DataFrame()

        df = pd.concat(dfs, ignore_index=True)
        if self.date_column and self.date_column in df.columns:
            df = df.sort_values(self.date_column).reset_index(drop=True)
        return df

    def write(
        self,
        df: pd.DataFrame,
        deduplicate: bool = True,
        extraction_date: date | None = None,
    ) -> WriteResult:
        if df.empty:
            return WriteResult(
                path=self.file_path, rows_written=0, rows_before=0,
                rows_after=0, rows_deduplicated=0,
            )

        if extraction_date is None:
            extraction_date = date.today()

        existing_df: pd.DataFrame | None = None
        if self.mode == StorageMode.DAILY_FILES:
            output_path = self._daily_file_path(extraction_date)
            rows_before = 0
        else:
            output_path = self.file_path
            if self.exists():
                existing_df = self.read()
                rows_before = len(existing_df)
            else:
                rows_before = 0

        if self.mode == StorageMode.SINGLE_FILE and existing_df is not None and rows_before > 0:
            df = pd.concat([existing_df, df], ignore_index=True)

        rows_deduplicated = 0
        if deduplicate and self.key_columns:
            rows_before_dedup = len(df)
            df = df.drop_duplicates(subset=self.key_columns, keep="last")
            rows_deduplicated = rows_before_dedup - len(df)

        if self.date_column and self.date_column in df.columns:
            df = df.sort_values(self.date_column).reset_index(drop=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, output_path, compression=self.config.compression)

        return WriteResult(
            path=output_path, rows_written=len(df), rows_before=rows_before,
            rows_after=len(df), rows_deduplicated=rows_deduplicated,
        )

    def get_stats(self) -> dict[str, Any]:
        files = self._get_all_files()
        total_size = sum(f.stat().st_size for f in files)
        total_rows = 0
        for f in files:
            try:
                total_rows += pq.read_metadata(f).num_rows
            except Exception:
                pass

        return {
            "name": self.name,
            "mode": self.mode.value,
            "num_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_rows": total_rows,
        }


# ============================================================================
# TESTS
# ============================================================================


def create_sample_data(start_date: date, num_days: int, contracts: list[str]) -> pd.DataFrame:
    """Create sample bond basis data."""
    records = []
    for i in range(num_days):
        dt = start_date + timedelta(days=i)
        for contract in contracts:
            records.append({
                "date": dt,
                "contract": contract,
                "px_last": 110.0 + i * 0.1,
                "ctd_ticker": "T 4.125 11/15/32",
                "net_basis": 2.0 + i * 0.05,
                "gross_basis": 4.5 + i * 0.08,
            })
    return pd.DataFrame(records)


def test_single_file():
    """Test single file mode with append and deduplication."""
    print("\n" + "=" * 60)
    print("TEST 1: Single File Mode")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ParquetStore(
            base_dir=tmpdir,
            name="test_basis",
            key_columns=["date", "contract"],
            mode=StorageMode.SINGLE_FILE,
        )

        # Write initial data
        df1 = create_sample_data(date(2024, 1, 1), 5, ["TYH4", "TYM4"])
        print(f"\n1. Writing {len(df1)} rows...")
        result1 = store.write(df1)
        print(f"   Written: {result1.rows_written} rows")
        print(f"   File: {result1.path.stat().st_size:,} bytes")

        # Append overlapping data
        df2 = create_sample_data(date(2024, 1, 3), 5, ["TYH4", "TYM4"])
        print(f"\n2. Appending {len(df2)} overlapping rows...")
        result2 = store.write(df2)
        print(f"   Total rows: {result2.rows_written}")
        print(f"   Deduplicated: {result2.rows_deduplicated}")
        print(f"   Net added: {result2.rows_added}")

        # Read back
        df = store.read()
        print(f"\n3. Read back: {len(df)} rows")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")

        # Filtered read
        df_filtered = store.read(start_date=date(2024, 1, 3), end_date=date(2024, 1, 5))
        print(f"\n4. Filtered (Jan 3-5): {len(df_filtered)} rows")

        stats = store.get_stats()
        print(f"\n5. Stats: {stats['total_rows']} rows, {stats['total_size_mb']} MB")

        print("\n   PASSED")


def test_daily_files():
    """Test daily file mode."""
    print("\n" + "=" * 60)
    print("TEST 2: Daily Files Mode")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ParquetStore(
            base_dir=tmpdir,
            name="daily_basis",
            key_columns=["date", "contract"],
            mode=StorageMode.DAILY_FILES,
        )

        # Write 3 days
        for i in range(3):
            dt = date(2024, 1, 1) + timedelta(days=i)
            df = create_sample_data(dt, 1, ["TYH4", "TYM4"])
            result = store.write(df, extraction_date=dt)
            print(f"{i+1}. {dt}: {result.path.name}")

        # List files
        files = list(Path(tmpdir).glob("*.parquet"))
        print(f"\n4. Created {len(files)} files")

        # Read all
        df = store.read()
        print(f"5. Total rows: {len(df)}")

        print("\n   PASSED")


def test_performance():
    """Test with larger dataset."""
    print("\n" + "=" * 60)
    print("TEST 3: Performance (5 years of data)")
    print("=" * 60)

    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ParquetStore(
            base_dir=tmpdir,
            name="perf_test",
            key_columns=["date", "contract"],
        )

        contracts = ["TUH4", "TUM4", "FVH4", "FVM4", "TYH4", "TYM4"]
        num_days = 365 * 5

        print(f"\n1. Generating {num_days} days x {len(contracts)} contracts...")
        start = time.time()
        df = create_sample_data(date(2019, 1, 1), num_days, contracts)
        print(f"   {len(df):,} rows in {time.time() - start:.2f}s")

        print("\n2. Writing...")
        start = time.time()
        result = store.write(df)
        write_time = time.time() - start
        print(f"   {result.rows_written:,} rows in {write_time:.2f}s")
        print(f"   {result.path.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"   {result.rows_written / write_time:,.0f} rows/sec")

        print("\n3. Reading...")
        start = time.time()
        df = store.read()
        read_time = time.time() - start
        print(f"   {len(df):,} rows in {read_time:.2f}s")
        print(f"   {len(df) / read_time:,.0f} rows/sec")

        print("\n4. Filtered read (2023)...")
        start = time.time()
        df_2023 = store.read(start_date=date(2023, 1, 1), end_date=date(2023, 12, 31))
        print(f"   {len(df_2023):,} rows in {time.time() - start:.2f}s")

        print("\n   PASSED")


def main():
    print("=" * 60)
    print("ParquetStore Standalone Test")
    print("=" * 60)
    print(f"\nDependencies: pandas={pd.__version__}, pyarrow={pa.__version__}")

    test_single_file()
    test_daily_files()
    test_performance()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
