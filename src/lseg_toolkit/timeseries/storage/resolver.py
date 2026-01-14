"""
Symbol resolution utilities for storage operations.

This module provides the SymbolResolver class for resolving symbols/RICs
to instrument IDs with in-memory caching.
"""

from __future__ import annotations

import psycopg

from lseg_toolkit.exceptions import StorageError

from .queries import Queries


class SymbolResolver:
    """
    Resolves symbols/RICs to instrument IDs with caching.

    This class provides efficient symbol resolution by caching lookups
    in memory. Useful when performing batch operations on the same
    instruments.

    Example:
        >>> with get_connection() as conn:
        ...     resolver = SymbolResolver(conn)
        ...     id1 = resolver.resolve("TYc1")  # DB lookup
        ...     id2 = resolver.resolve("TYc1")  # Cache hit
    """

    def __init__(self, conn: psycopg.Connection):
        """
        Initialize resolver with database connection.

        Args:
            conn: PostgreSQL connection.
        """
        self.conn = conn
        self._cache: dict[str, int] = {}

    def resolve(self, symbol_or_ric: str) -> int:
        """
        Resolve symbol or RIC to instrument ID.

        Args:
            symbol_or_ric: Internal symbol or LSEG RIC.

        Returns:
            Instrument ID.

        Raises:
            StorageError: If symbol not found.
        """
        if symbol_or_ric in self._cache:
            return self._cache[symbol_or_ric]

        sql, params = Queries.get_instrument_id(symbol_or_ric)
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            result = cur.fetchone()

        if not result:
            raise StorageError(f"Unknown symbol/RIC: {symbol_or_ric}")

        instrument_id = result["id"]
        self._cache[symbol_or_ric] = instrument_id
        return instrument_id

    def resolve_many(self, symbols: list[str]) -> dict[str, int]:
        """
        Resolve multiple symbols to instrument IDs.

        Args:
            symbols: List of symbols or RICs.

        Returns:
            Dict mapping symbol -> instrument_id.

        Raises:
            StorageError: If any symbol not found.
        """
        return {symbol: self.resolve(symbol) for symbol in symbols}

    def try_resolve(self, symbol_or_ric: str) -> int | None:
        """
        Try to resolve symbol, returning None if not found.

        Args:
            symbol_or_ric: Internal symbol or LSEG RIC.

        Returns:
            Instrument ID or None if not found.
        """
        try:
            return self.resolve(symbol_or_ric)
        except StorageError:
            return None

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()

    def preload(self, symbols: list[str] | None = None) -> int:
        """
        Preload cache with instruments.

        Args:
            symbols: Optional list of symbols to preload. If None, loads all.

        Returns:
            Number of instruments loaded.
        """
        with self.conn.cursor() as cur:
            if symbols:
                placeholders = ", ".join("%s" for _ in symbols)
                cur.execute(
                    f"SELECT symbol, id FROM instruments WHERE symbol IN ({placeholders})",  # noqa: S608
                    symbols,
                )
            else:
                cur.execute("SELECT symbol, id FROM instruments")

            count = 0
            for row in cur.fetchall():
                self._cache[row[0]] = row[1]
                count += 1

        return count
