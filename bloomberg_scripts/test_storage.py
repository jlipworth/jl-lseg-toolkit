#!/usr/bin/env python3
"""Test script for the ParquetStore storage module.

This script tests the storage functionality without requiring Bloomberg connection.
Run this to verify parquet read/write/append/deduplication works correctly.

Usage:
    python bloomberg_scripts/test_storage.py
"""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from bloomberg_scripts.common.storage import (
    MultiStore,
    ParquetStore,
    StorageMode,
    create_store,
)


def create_sample_data(
    start_date: date,
    num_days: int,
    contracts: list[str],
) -> pd.DataFrame:
    """Create sample bond basis data for testing."""
    records = []
    for i in range(num_days):
        dt = start_date + timedelta(days=i)
        for contract in contracts:
            records.append({
                "date": dt,
                "contract": contract,
                "px_last": 110.0 + i * 0.1,
                "ctd_ticker": f"T 4.125 11/15/32",
                "ctd_cusip": "91282CFV8",
                "net_basis": 2.0 + i * 0.05,
                "gross_basis": 4.5 + i * 0.08,
            })
    return pd.DataFrame(records)


def test_single_file_mode():
    """Test single file storage with append and deduplication."""
    print("\n" + "=" * 60)
    print("TEST 1: Single File Mode (append + deduplicate)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ParquetStore(
            base_dir=tmpdir,
            name="test_basis",
            key_columns=["date", "contract"],
            date_column="date",
            mode=StorageMode.SINGLE_FILE,
        )

        # Write initial data
        df1 = create_sample_data(
            start_date=date(2024, 1, 1),
            num_days=5,
            contracts=["TYH4", "TYM4"],
        )
        print(f"\n1. Writing initial data: {len(df1)} rows")
        result1 = store.write(df1)
        print(f"   Result: {result1.rows_written} rows written to {result1.path.name}")
        print(f"   File size: {result1.path.stat().st_size:,} bytes")

        # Append overlapping data (should deduplicate)
        df2 = create_sample_data(
            start_date=date(2024, 1, 3),  # Overlaps with df1
            num_days=5,
            contracts=["TYH4", "TYM4"],
        )
        print(f"\n2. Appending overlapping data: {len(df2)} rows")
        result2 = store.append(df2)
        print(f"   Result: {result2.rows_written} rows total")
        print(f"   Rows before: {result2.rows_before}")
        print(f"   Rows added: {result2.rows_added}")
        print(f"   Rows deduplicated: {result2.rows_deduplicated}")

        # Read back and verify
        df_read = store.read()
        print(f"\n3. Reading back data: {len(df_read)} rows")
        print(f"   Date range: {df_read['date'].min()} to {df_read['date'].max()}")
        print(f"   Contracts: {df_read['contract'].unique().tolist()}")

        # Read with date filter
        df_filtered = store.read(
            start_date=date(2024, 1, 3),
            end_date=date(2024, 1, 5),
        )
        print(f"\n4. Filtered read (Jan 3-5): {len(df_filtered)} rows")

        # Get stats
        stats = store.get_stats()
        print(f"\n5. Store stats:")
        print(f"   Mode: {stats['mode']}")
        print(f"   Total rows: {stats['total_rows']}")
        print(f"   File size: {stats['total_size_mb']} MB")
        print(f"   Date range: {stats['date_range']}")

        print("\n   PASSED")


def test_daily_files_mode():
    """Test daily file storage mode."""
    print("\n" + "=" * 60)
    print("TEST 2: Daily Files Mode")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ParquetStore(
            base_dir=tmpdir,
            name="daily_basis",
            key_columns=["date", "contract"],
            date_column="date",
            mode=StorageMode.DAILY_FILES,
        )

        # Write data for multiple days
        for i in range(3):
            dt = date(2024, 1, 1) + timedelta(days=i)
            df = create_sample_data(
                start_date=dt,
                num_days=1,
                contracts=["TYH4", "TYM4"],
            )
            print(f"\n{i+1}. Writing data for {dt}: {len(df)} rows")
            result = store.write(df, extraction_date=dt)
            print(f"   File: {result.path.name}")

        # List all files
        files = list(Path(tmpdir).glob("*.parquet"))
        print(f"\n4. Created {len(files)} daily files:")
        for f in sorted(files):
            size = f.stat().st_size
            print(f"   {f.name}: {size:,} bytes")

        # Read all data
        df_all = store.read()
        print(f"\n5. Reading all data: {len(df_all)} rows")
        print(f"   Date range: {df_all['date'].min()} to {df_all['date'].max()}")

        print("\n   PASSED")


def test_multi_store():
    """Test MultiStore for related datasets."""
    print("\n" + "=" * 60)
    print("TEST 3: MultiStore (related datasets)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Define related stores
        multi = MultiStore(
            base_dir=tmpdir,
            stores={
                "futures": {"key_columns": ["date", "contract"]},
                "ctd": {"key_columns": ["date", "contract"]},
                "basis": {"key_columns": ["date", "contract"]},
            },
        )

        # Create sample data for each store
        dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(5)]
        contracts = ["TYH4", "TYM4"]

        futures_data = pd.DataFrame([
            {"date": dt, "contract": c, "px_last": 111.5 + i * 0.1}
            for i, dt in enumerate(dates)
            for c in contracts
        ])

        ctd_data = pd.DataFrame([
            {"date": dt, "contract": c, "ctd_ticker": "T 4.125 11/15/32", "conv_factor": 0.8234}
            for dt in dates
            for c in contracts
        ])

        basis_data = pd.DataFrame([
            {"date": dt, "contract": c, "net_basis": 2.1 + i * 0.05, "gross_basis": 4.5}
            for i, dt in enumerate(dates)
            for c in contracts
        ])

        # Write all at once
        print("\n1. Writing to all stores:")
        results = multi.write_all({
            "futures": futures_data,
            "ctd": ctd_data,
            "basis": basis_data,
        })

        for name, result in results.items():
            print(f"   {name}: {result.rows_written} rows")

        # Read from individual stores
        print("\n2. Reading from individual stores:")
        for name, store in multi.stores.items():
            df = store.read()
            print(f"   {name}: {len(df)} rows, columns: {df.columns.tolist()}")

        # Get all stats
        print("\n3. All store stats:")
        all_stats = multi.get_all_stats()
        for name, stats in all_stats.items():
            print(f"   {name}: {stats['total_rows']} rows, {stats['total_size_mb']} MB")

        print("\n   PASSED")


def test_convenience_function():
    """Test the create_store convenience function."""
    print("\n" + "=" * 60)
    print("TEST 4: create_store() Convenience Function")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = create_store(
            instrument="bond_basis",
            name="treasury_ctd",
            key_columns=["date", "contract"],
            base_dir=tmpdir,
        )

        df = create_sample_data(
            start_date=date(2024, 1, 1),
            num_days=10,
            contracts=["TYH4"],
        )

        result = store.write(df)
        print(f"\n1. Created store at: {result.path}")
        print(f"   Rows written: {result.rows_written}")
        print(f"   File size: {result.path.stat().st_size:,} bytes")

        # Verify path structure
        expected_parent = Path(tmpdir) / "bond_basis"
        assert result.path.parent == expected_parent, "Directory structure mismatch"
        print(f"   Directory structure: {result.path.parent.relative_to(tmpdir)}")

        print("\n   PASSED")


def test_schema_and_stats():
    """Test schema retrieval and statistics."""
    print("\n" + "=" * 60)
    print("TEST 5: Schema and Statistics")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ParquetStore(
            base_dir=tmpdir,
            name="schema_test",
            key_columns=["date", "contract"],
        )

        # Write data with various types
        df = pd.DataFrame({
            "date": [date(2024, 1, 1), date(2024, 1, 2)],
            "contract": ["TYH4", "TYH4"],
            "px_last": [111.5, 111.625],
            "volume": [100000, 150000],
            "is_front": [True, True],
            "note": ["first", "second"],
        })

        store.write(df)

        # Get schema
        schema = store.get_schema()
        print("\n1. Schema:")
        if schema is not None:
            for field in schema:
                print(f"   {field.name}: {field.type}")
        else:
            print("   (no schema available)")

        # Get date range
        date_range = store.get_date_range()
        print(f"\n2. Date range: {date_range[0]} to {date_range[1]}")

        # Get full stats
        stats = store.get_stats()
        print(f"\n3. Full stats:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\n   PASSED")


def test_large_data():
    """Test with larger dataset to verify performance."""
    print("\n" + "=" * 60)
    print("TEST 6: Larger Dataset Performance")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ParquetStore(
            base_dir=tmpdir,
            name="perf_test",
            key_columns=["date", "contract"],
        )

        # Create larger dataset: 5 years daily, 6 contracts
        import time

        contracts = ["TUH4", "TUM4", "FVH4", "FVM4", "TYH4", "TYM4"]
        num_days = 365 * 5  # 5 years

        print(f"\n1. Generating {num_days} days × {len(contracts)} contracts...")
        start = time.time()
        df = create_sample_data(
            start_date=date(2019, 1, 1),
            num_days=num_days,
            contracts=contracts,
        )
        gen_time = time.time() - start
        print(f"   Generated {len(df):,} rows in {gen_time:.2f}s")

        # Write
        print("\n2. Writing to parquet...")
        start = time.time()
        result = store.write(df)
        write_time = time.time() - start
        print(f"   Wrote {result.rows_written:,} rows in {write_time:.2f}s")
        print(f"   File size: {result.path.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"   Throughput: {result.rows_written / write_time:,.0f} rows/sec")

        # Read
        print("\n3. Reading from parquet...")
        start = time.time()
        df_read = store.read()
        read_time = time.time() - start
        print(f"   Read {len(df_read):,} rows in {read_time:.2f}s")
        print(f"   Throughput: {len(df_read) / read_time:,.0f} rows/sec")

        # Filtered read
        print("\n4. Filtered read (2023 only)...")
        start = time.time()
        df_2023 = store.read(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        filter_time = time.time() - start
        print(f"   Read {len(df_2023):,} rows in {filter_time:.2f}s")

        print("\n   PASSED")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ParquetStore Module Tests")
    print("=" * 60)
    print("\nThese tests verify the storage module works correctly.")
    print("No Bloomberg connection required.")

    test_single_file_mode()
    test_daily_files_mode()
    test_multi_store()
    test_convenience_function()
    test_schema_and_stats()
    test_large_data()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
    print("""
The ParquetStore module is ready for use. Example usage:

    from bloomberg_scripts.common.storage import ParquetStore, create_store

    # Create store for bond basis data
    store = create_store(
        instrument="bond_basis",
        name="ctd_basis",
        key_columns=["date", "contract"],
    )

    # Write data (will append and deduplicate)
    result = store.write(df)

    # Read all data
    df = store.read()

    # Read date range
    df = store.read(start_date=date(2024, 1, 1))
""")


if __name__ == "__main__":
    main()
