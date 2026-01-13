"""
Migration utility for DuckDB to TimescaleDB.

This module provides functions to migrate existing data from the legacy
DuckDB database to the new TimescaleDB storage layer.

Usage:
    python -m lseg_toolkit.timeseries.storage.migrate_to_tsdb \
        --duckdb data/timeseries.duckdb \
        --pg-dsn "postgresql://postgres@192.168.x.x:5432/timeseries"
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import pandas as pd
import psycopg
from psycopg import sql

from lseg_toolkit.exceptions import StorageError

if TYPE_CHECKING:
    pass


def _format_copy_value(value) -> str:
    """Format a value for PostgreSQL COPY protocol."""
    if value is None:
        return r"\N"
    if isinstance(value, float) and pd.isna(value):
        return r"\N"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "t" if value else "f"
    if isinstance(value, (int, float)):
        import numpy as np

        if isinstance(value, (np.integer,)):
            return str(int(value))
        if isinstance(value, (np.floating,)):
            if np.isnan(value):
                return r"\N"
            return str(float(value))
        return str(value)
    return str(value)


def _dataframe_to_copy_buffer(df: pd.DataFrame, columns: list[str]) -> io.StringIO:
    """Convert DataFrame to COPY-compatible text buffer."""
    buffer = io.StringIO()

    for _, row in df.iterrows():
        values = [_format_copy_value(row[col] if col in row.index else None) for col in columns]
        buffer.write("\t".join(values) + "\n")

    buffer.seek(0)
    return buffer


def _bulk_copy(
    pg_conn: psycopg.Connection,
    table: str,
    columns: list[str],
    buffer: io.StringIO,
) -> int:
    """Execute COPY FROM for bulk insert."""
    content = buffer.getvalue()
    row_count = content.count("\n")

    if row_count == 0:
        return 0

    with pg_conn.cursor() as cur:
        with cur.copy(
            sql.SQL("COPY {} ({}) FROM STDIN").format(
                sql.Identifier(table),
                sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            )
        ) as copy:
            copy.write(content)

    return row_count


def _migrate_table(
    duck_conn: duckdb.DuckDBPyConnection,
    pg_conn: psycopg.Connection,
    table: str,
    columns: list[str] | None,
    batch_size: int,
    show_progress: bool,
) -> int:
    """Migrate a single table from DuckDB to PostgreSQL."""
    # Check if table exists in DuckDB
    try:
        total = duck_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
    except duckdb.CatalogException:
        # Table doesn't exist
        return 0

    if total == 0:
        return 0

    # Get columns if not specified
    if columns is None:
        desc = duck_conn.execute(f"DESCRIBE {table}").fetchall()  # noqa: S608
        columns = [row[0] for row in desc]

    # Migrate in batches
    offset = 0
    migrated = 0

    while offset < total:
        df = duck_conn.execute(
            f"SELECT * FROM {table} LIMIT {batch_size} OFFSET {offset}"  # noqa: S608
        ).fetchdf()

        if df.empty:
            break

        buffer = _dataframe_to_copy_buffer(df, columns)
        migrated += _bulk_copy(pg_conn, table, columns, buffer)

        offset += batch_size

        if show_progress:
            pct = min(100, int(offset / total * 100))
            print(f"  {table}: {pct}% ({migrated:,} rows)", end="\r")

    if show_progress:
        print(f"  {table}: 100% ({migrated:,} rows)")

    return migrated


def _update_sequences(pg_conn: psycopg.Connection) -> None:
    """Update PostgreSQL sequences after migration."""
    sequences = [
        ("instruments_id_seq", "instruments", "id"),
        ("roll_events_id_seq", "roll_events", "id"),
        ("extraction_log_id_seq", "extraction_log", "id"),
        ("extraction_progress_id_seq", "extraction_progress", "id"),
    ]

    with pg_conn.cursor() as cur:
        for seq_name, table, column in sequences:
            try:
                cur.execute(
                    sql.SQL(
                        "SELECT setval(%s, COALESCE((SELECT MAX({}) FROM {}), 0) + 1, false)"
                    ).format(sql.Identifier(column), sql.Identifier(table)),
                    [seq_name],
                )
            except psycopg.Error:
                # Sequence may not exist yet
                pass


def migrate_duckdb_to_timescaledb(
    duckdb_path: str,
    pg_dsn: str,
    batch_size: int = 50_000,
    show_progress: bool = True,
    init_schema: bool = True,
) -> dict[str, int]:
    """
    Migrate all data from DuckDB to TimescaleDB.

    This function handles the complete migration process:
    1. Initializes the TimescaleDB schema (if requested)
    2. Migrates all instrument tables
    3. Migrates all timeseries tables
    4. Migrates metadata tables
    5. Updates sequences

    Args:
        duckdb_path: Path to DuckDB database file.
        pg_dsn: PostgreSQL connection string.
        batch_size: Rows per batch for COPY.
        show_progress: Show progress during migration.
        init_schema: Initialize schema before migration.

    Returns:
        Dict with migrated row counts per table.

    Raises:
        StorageError: If migration fails.
    """
    if not Path(duckdb_path).exists():
        raise StorageError(f"DuckDB file not found: {duckdb_path}")

    counts: dict[str, int] = {}

    # Connect to both databases
    duck_conn = duckdb.connect(duckdb_path, read_only=True)
    pg_conn = psycopg.connect(pg_dsn)

    try:
        # Initialize schema if requested
        if init_schema:
            if show_progress:
                print("Initializing TimescaleDB schema...")
            from .pg_schema import init_schema as _init_schema

            _init_schema(pg_conn)
            pg_conn.commit()

        if show_progress:
            print("\nMigrating tables...")

        # 1. Migrate instruments first (foreign key dependency)
        counts["instruments"] = _migrate_table(
            duck_conn,
            pg_conn,
            "instruments",
            [
                "id",
                "symbol",
                "name",
                "asset_class",
                "data_shape",
                "lseg_ric",
                "exchange",
                "currency",
                "description",
                "created_at",
                "updated_at",
            ],
            batch_size,
            show_progress,
        )

        # 2. Migrate instrument detail tables
        detail_tables = [
            "instrument_futures",
            "instrument_fx",
            "instrument_rate",
            "instrument_bond",
            "instrument_fixing",
            "instrument_equity",
            "instrument_etf",
            "instrument_index",
            "instrument_commodity",
            "instrument_cds",
            "instrument_option",
        ]

        for table in detail_tables:
            counts[table] = _migrate_table(
                duck_conn, pg_conn, table, None, batch_size, show_progress
            )

        # 3. Migrate timeseries tables (largest)
        timeseries_tables = [
            "timeseries_ohlcv",
            "timeseries_quote",
            "timeseries_rate",
            "timeseries_bond",
            "timeseries_fixing",
        ]

        for table in timeseries_tables:
            counts[table] = _migrate_table(
                duck_conn, pg_conn, table, None, batch_size, show_progress
            )

        # 4. Migrate metadata tables
        meta_tables = ["roll_events", "extraction_log", "extraction_progress"]

        for table in meta_tables:
            counts[table] = _migrate_table(
                duck_conn, pg_conn, table, None, batch_size, show_progress
            )

        # 5. Update sequences
        if show_progress:
            print("\nUpdating sequences...")
        _update_sequences(pg_conn)

        # Commit all changes
        pg_conn.commit()

        if show_progress:
            print("\nMigration complete!")
            total_rows = sum(counts.values())
            print(f"Total rows migrated: {total_rows:,}")

        return counts

    except Exception as e:
        pg_conn.rollback()
        raise StorageError(f"Migration failed: {e}") from e
    finally:
        duck_conn.close()
        pg_conn.close()


def verify_migration(
    duckdb_path: str,
    pg_dsn: str,
) -> dict[str, dict[str, int]]:
    """
    Verify migration by comparing row counts.

    Args:
        duckdb_path: Path to DuckDB database file.
        pg_dsn: PostgreSQL connection string.

    Returns:
        Dict with {table: {duckdb: count, postgres: count, match: bool}}
    """
    duck_conn = duckdb.connect(duckdb_path, read_only=True)
    pg_conn = psycopg.connect(pg_dsn)

    results = {}

    tables = [
        "instruments",
        "timeseries_ohlcv",
        "timeseries_quote",
        "timeseries_rate",
        "timeseries_bond",
        "timeseries_fixing",
        "roll_events",
    ]

    try:
        for table in tables:
            # Get DuckDB count
            try:
                duck_count = duck_conn.execute(
                    f"SELECT COUNT(*) FROM {table}"  # noqa: S608
                ).fetchone()[0]
            except duckdb.CatalogException:
                duck_count = 0

            # Get PostgreSQL count
            try:
                with pg_conn.cursor() as cur:
                    cur.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))
                    )
                    pg_count = cur.fetchone()[0]
            except psycopg.Error:
                pg_count = 0

            results[table] = {
                "duckdb": duck_count,
                "postgres": pg_count,
                "match": duck_count == pg_count,
            }

        return results

    finally:
        duck_conn.close()
        pg_conn.close()


def main():
    """CLI entry point for migration."""
    parser = argparse.ArgumentParser(
        description="Migrate data from DuckDB to TimescaleDB"
    )
    parser.add_argument(
        "--duckdb",
        required=True,
        help="Path to DuckDB database file",
    )
    parser.add_argument(
        "--pg-dsn",
        required=True,
        help="PostgreSQL connection string (e.g., postgresql://user@host:5432/db)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50_000,
        help="Rows per batch (default: 50000)",
    )
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="Skip schema initialization (if already created)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration after completion",
    )

    args = parser.parse_args()

    try:
        # Run migration
        counts = migrate_duckdb_to_timescaledb(
            duckdb_path=args.duckdb,
            pg_dsn=args.pg_dsn,
            batch_size=args.batch_size,
            show_progress=True,
            init_schema=not args.no_schema,
        )

        # Print summary
        print("\n" + "=" * 50)
        print("Migration Summary:")
        print("=" * 50)
        for table, count in sorted(counts.items()):
            if count > 0:
                print(f"  {table}: {count:,} rows")

        # Verify if requested
        if args.verify:
            print("\n" + "=" * 50)
            print("Verification:")
            print("=" * 50)
            results = verify_migration(args.duckdb, args.pg_dsn)
            all_match = True
            for table, info in sorted(results.items()):
                status = "✓" if info["match"] else "✗"
                print(
                    f"  {status} {table}: DuckDB={info['duckdb']:,}, "
                    f"PostgreSQL={info['postgres']:,}"
                )
                if not info["match"]:
                    all_match = False

            if all_match:
                print("\nAll tables verified successfully!")
            else:
                print("\nWARNING: Some tables have mismatched counts!")
                sys.exit(1)

    except StorageError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nMigration cancelled.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
