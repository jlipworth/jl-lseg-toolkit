"""
Database connection management for TimescaleDB/PostgreSQL storage.

This module provides connection utilities including connection pooling
and context managers for database connections.

Replaces the previous DuckDB connection layer with psycopg for
TimescaleDB/PostgreSQL support.
"""

from __future__ import annotations

import threading
import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from lseg_toolkit.timeseries.config import DatabaseConfig

if TYPE_CHECKING:
    from collections.abc import Generator

# Module-level connection pool (singleton) with thread-safe access
_pool: ConnectionPool | None = None
_pool_config: DatabaseConfig | None = None
_pool_lock = threading.Lock()

# Legacy compatibility constant
DEFAULT_DUCKDB_PATH: str = "data/timeseries.duckdb"


def get_pool(config: DatabaseConfig | None = None) -> ConnectionPool:
    """
    Get or create the connection pool (thread-safe).

    The pool is created as a singleton on first call. Subsequent calls
    return the same pool instance.

    Args:
        config: Database configuration. If not provided, loads from
                environment variables via DatabaseConfig.from_env().

    Returns:
        ConnectionPool instance for the configured database.

    Example:
        >>> pool = get_pool()
        >>> with pool.connection() as conn:
        ...     conn.execute("SELECT 1")
    """
    global _pool, _pool_config

    if config is None:
        config = DatabaseConfig.from_env()

    # Thread-safe pool creation
    with _pool_lock:
        # Check if pool needs to be created or recreated
        # Only recreate if connection-critical settings changed
        needs_recreate = (
            _pool is None
            or _pool_config is None
            or _pool_config.host != config.host
            or _pool_config.port != config.port
            or _pool_config.database != config.database
            or _pool_config.user != config.user
            or _pool_config.password != config.password
        )

        if needs_recreate:
            if _pool is not None:
                try:
                    _pool.close()
                except Exception:
                    pass  # Ignore errors closing old pool

            _pool = ConnectionPool(
                config.dsn,
                min_size=config.pool_min_size,
                max_size=config.pool_max_size,
                kwargs={"row_factory": dict_row},
            )
            _pool_config = config

        return _pool


def close_pool() -> None:
    """
    Close the connection pool.

    Call this when shutting down the application to cleanly
    release all connections.
    """
    global _pool, _pool_config

    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
            _pool = None
            _pool_config = None


@contextmanager
def get_connection(
    dsn: str | None = None,
    config: DatabaseConfig | None = None,
    use_pool: bool = True,
    # Legacy parameter for backwards compatibility
    db_path: str | None = None,
) -> Generator[psycopg.Connection]:
    """
    Context manager for database connection.

    Provides a connection that automatically commits on success
    and rolls back on exception.

    Args:
        dsn: Direct connection string. If provided, creates a new
             connection instead of using the pool.
        config: Database configuration. Ignored if dsn is provided.
        use_pool: Whether to use connection pooling. Set to False
                  for one-off connections (migrations, scripts).
        db_path: DEPRECATED - Legacy parameter for DuckDB compatibility.
                 Ignored, uses PostgreSQL connection instead.

    Yields:
        Database connection with dict row factory.

    Example:
        >>> with get_connection() as conn:
        ...     result = conn.execute("SELECT * FROM instruments").fetchall()

        >>> # Direct connection (no pooling)
        >>> with get_connection(dsn="postgresql://...", use_pool=False) as conn:
        ...     conn.execute("CREATE TABLE ...")
    """
    # Handle legacy db_path parameter
    if db_path is not None:
        warnings.warn(
            "db_path parameter is deprecated. Connection now uses PostgreSQL via "
            "DatabaseConfig. Set TSDB_* environment variables instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Ignore db_path, use default PostgreSQL connection

    if dsn is not None:
        # Direct connection without pooling
        conn = psycopg.connect(dsn, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    elif use_pool:
        # Pooled connection
        pool = get_pool(config)
        with pool.connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    else:
        # Non-pooled connection using config
        if config is None:
            config = DatabaseConfig.from_env()
        conn = psycopg.connect(config.dsn, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db(config: DatabaseConfig | None = None) -> None:
    """
    Initialize the database schema.

    Creates all tables if they don't exist and configures
    TimescaleDB hypertables.

    Args:
        config: Database configuration.
    """
    from .pg_schema import init_schema

    with get_connection(config=config, use_pool=False) as conn:
        init_schema(conn)
