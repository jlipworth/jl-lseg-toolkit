"""
Database connection management for DuckDB storage.

This module provides connection utilities including the default path
and context manager for database connections.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from collections.abc import Generator

# Default path for DuckDB database
DEFAULT_DUCKDB_PATH: str = "data/timeseries.duckdb"


@contextmanager
def get_connection(
    db_path: str = DEFAULT_DUCKDB_PATH,
) -> Generator[duckdb.DuckDBPyConnection]:
    """
    Context manager for database connection.

    Args:
        db_path: Path to DuckDB database file.

    Yields:
        Database connection.
    """
    # Import here to avoid circular import
    from .schema import init_db

    conn = init_db(db_path)
    try:
        yield conn
    finally:
        conn.close()
