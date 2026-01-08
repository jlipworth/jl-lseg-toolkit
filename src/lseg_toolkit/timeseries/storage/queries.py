"""
Common SQL query patterns for storage operations.

This module provides reusable query builders to reduce SQL duplication
across the storage layer.
"""

from __future__ import annotations

from lseg_toolkit.timeseries.enums import DataShape


class Queries:
    """Common SQL query patterns."""

    @staticmethod
    def instrument_exists(symbol: str) -> tuple[str, list]:
        """Check if instrument exists by symbol."""
        return "SELECT id FROM instruments WHERE symbol = ?", [symbol]

    @staticmethod
    def get_instrument_id(symbol_or_ric: str) -> tuple[str, list]:
        """Get instrument ID by symbol or RIC."""
        return (
            "SELECT id FROM instruments WHERE symbol = ? OR lseg_ric = ?",
            [symbol_or_ric, symbol_or_ric],
        )

    @staticmethod
    def get_instrument_with_shape(symbol: str) -> tuple[str, list]:
        """Get instrument ID and data_shape by symbol."""
        return "SELECT id, data_shape FROM instruments WHERE symbol = ?", [symbol]

    @staticmethod
    def get_data_shape(instrument_id: int) -> tuple[str, list]:
        """Get data_shape for an instrument."""
        return "SELECT data_shape FROM instruments WHERE id = ?", [instrument_id]

    @staticmethod
    def get_date_range(data_shape: DataShape, granularity: str | None = None) -> str:
        """
        Get date range query for a data shape.

        Args:
            data_shape: The data shape to query.
            granularity: Granularity value (not used for FIXING).

        Returns:
            SQL query string with placeholders for instrument_id (and granularity if applicable).
        """
        table = _get_table_for_shape(data_shape)

        if data_shape == DataShape.FIXING:
            return f"""
                SELECT MIN(date), MAX(date)
                FROM {table}
                WHERE instrument_id = ?
            """
        else:
            return f"""
                SELECT CAST(MIN(ts) AS DATE), CAST(MAX(ts) AS DATE)
                FROM {table}
                WHERE instrument_id = ? AND granularity = ?
            """

    @staticmethod
    def count_rows(data_shape: DataShape) -> str:
        """
        Get row count query for a data shape.

        Args:
            data_shape: The data shape to query.

        Returns:
            SQL query string with placeholders for instrument_id (and granularity if applicable).
        """
        table = _get_table_for_shape(data_shape)

        if data_shape == DataShape.FIXING:
            return f"SELECT COUNT(*) FROM {table} WHERE instrument_id = ?"
        else:
            return f"SELECT COUNT(*) FROM {table} WHERE instrument_id = ? AND granularity = ?"


def _get_table_for_shape(data_shape: DataShape) -> str:
    """Map DataShape to table name."""
    return {
        DataShape.OHLCV: "timeseries_ohlcv",
        DataShape.QUOTE: "timeseries_quote",
        DataShape.RATE: "timeseries_rate",
        DataShape.BOND: "timeseries_bond",
        DataShape.FIXING: "timeseries_fixing",
    }.get(data_shape, "timeseries_ohlcv")
