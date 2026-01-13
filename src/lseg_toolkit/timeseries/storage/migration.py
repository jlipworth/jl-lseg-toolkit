"""
Database migration utilities.

DEPRECATED: This module provides SQLite-to-DuckDB migration, which is no longer
the primary storage path. For migrating to PostgreSQL/TimescaleDB, use the
migrate_to_tsdb module instead.
"""

from __future__ import annotations

import warnings

import duckdb

from lseg_toolkit.exceptions import StorageError

# Emit deprecation warning when module is imported
warnings.warn(
    "migration module (SQLite-to-DuckDB) is deprecated. "
    "Use migrate_to_tsdb for PostgreSQL/TimescaleDB migration.",
    DeprecationWarning,
    stacklevel=2,
)


def migrate_from_sqlite(
    sqlite_path: str,
    duckdb_conn: duckdb.DuckDBPyConnection,
) -> dict[str, int]:
    """
    Migrate data from SQLite to DuckDB.

    Args:
        sqlite_path: Path to SQLite database.
        duckdb_conn: DuckDB connection to migrate into.

    Returns:
        Dict with counts of migrated records per table.

    Raises:
        StorageError: If migration fails.
    """
    try:
        # Install and load SQLite extension
        duckdb_conn.execute("INSTALL sqlite; LOAD sqlite;")

        # Attach SQLite database
        duckdb_conn.execute(f"ATTACH '{sqlite_path}' AS sqlite_db (TYPE SQLITE)")

        counts = {}

        # Migrate instruments
        duckdb_conn.execute("""
            INSERT INTO instruments (id, symbol, name, asset_class, lseg_ric, created_at, updated_at)
            SELECT id, symbol, name, asset_class, lseg_ric, created_at, updated_at
            FROM sqlite_db.instruments
            ON CONFLICT (symbol) DO NOTHING
        """)
        counts["instruments"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM instruments"
        ).fetchone()[0]

        # Update sequence
        max_id = duckdb_conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM instruments"
        ).fetchone()[0]
        if max_id > 0:
            duckdb_conn.execute(f"SELECT setval('seq_instruments', {max_id + 1})")

        # Migrate futures_contracts
        duckdb_conn.execute("""
            INSERT INTO futures_contracts
            SELECT * FROM sqlite_db.futures_contracts
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["futures_contracts"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM futures_contracts"
        ).fetchone()[0]

        # Migrate fx_spots
        duckdb_conn.execute("""
            INSERT INTO fx_spots
            SELECT * FROM sqlite_db.fx_spots
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["fx_spots"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM fx_spots"
        ).fetchone()[0]

        # Migrate ois_rates
        duckdb_conn.execute("""
            INSERT INTO ois_rates
            SELECT * FROM sqlite_db.ois_rates
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["ois_rates"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM ois_rates"
        ).fetchone()[0]

        # Migrate govt_yields
        duckdb_conn.execute("""
            INSERT INTO govt_yields
            SELECT * FROM sqlite_db.govt_yields
            ON CONFLICT (instrument_id) DO NOTHING
        """)
        counts["govt_yields"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM govt_yields"
        ).fetchone()[0]

        # Migrate ohlcv_daily
        duckdb_conn.execute("""
            INSERT INTO ohlcv_daily
            SELECT * FROM sqlite_db.ohlcv_daily
            ON CONFLICT (instrument_id, date) DO NOTHING
        """)
        counts["ohlcv_daily"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM ohlcv_daily"
        ).fetchone()[0]

        # Migrate ohlcv_intraday
        duckdb_conn.execute("""
            INSERT INTO ohlcv_intraday
            SELECT * FROM sqlite_db.ohlcv_intraday
            ON CONFLICT (instrument_id, timestamp, granularity) DO NOTHING
        """)
        counts["ohlcv_intraday"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM ohlcv_intraday"
        ).fetchone()[0]

        # Migrate roll_events
        duckdb_conn.execute("""
            INSERT INTO roll_events
            SELECT * FROM sqlite_db.roll_events
            ON CONFLICT DO NOTHING
        """)
        counts["roll_events"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM roll_events"
        ).fetchone()[0]

        # Update roll_events sequence
        max_roll_id = duckdb_conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM roll_events"
        ).fetchone()[0]
        if max_roll_id > 0:
            duckdb_conn.execute(f"SELECT setval('seq_roll_events', {max_roll_id + 1})")

        # Migrate extraction_log
        duckdb_conn.execute("""
            INSERT INTO extraction_log
            SELECT * FROM sqlite_db.extraction_log
            ON CONFLICT DO NOTHING
        """)
        counts["extraction_log"] = duckdb_conn.execute(
            "SELECT COUNT(*) FROM extraction_log"
        ).fetchone()[0]

        # Update extraction_log sequence
        max_log_id = duckdb_conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM extraction_log"
        ).fetchone()[0]
        if max_log_id > 0:
            duckdb_conn.execute(
                f"SELECT setval('seq_extraction_log', {max_log_id + 1})"
            )

        # Detach SQLite database
        duckdb_conn.execute("DETACH sqlite_db")

        return counts
    except duckdb.Error as e:
        raise StorageError(f"Failed to migrate from SQLite: {e}") from e
