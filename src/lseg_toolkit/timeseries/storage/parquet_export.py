"""
Parquet export functionality for DuckDB storage.

This module provides functions for exporting time series data to Parquet format,
leveraging DuckDB's native Parquet support for efficient exports.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.enums import AssetClass, DataShape, Granularity


def export_to_parquet(
    conn: duckdb.DuckDBPyConnection,
    output_path: str,
    symbol: str | None = None,
    asset_class: AssetClass | None = None,
    data_shape: DataShape | None = None,
    granularity: Granularity = Granularity.DAILY,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    """
    Export data to Parquet using DuckDB's native COPY.

    Supports all data shapes and routes to the correct timeseries table.

    Args:
        conn: Database connection.
        output_path: Output file path (should end with .parquet).
        symbol: Filter by instrument symbol.
        asset_class: Filter by asset class.
        data_shape: Filter by data shape (infers table to export from).
        granularity: Data granularity (default: daily).
        start_date: Filter by start date.
        end_date: Filter by end date.

    Returns:
        Path to exported file.

    Raises:
        StorageError: If export fails.
    """
    try:
        # Create output directory if needed
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Determine which table to export from
        if data_shape is None:
            data_shape = DataShape.OHLCV  # Default to OHLCV

        # Build query based on data_shape
        if data_shape == DataShape.OHLCV:
            query = f"""
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.open,
                    t.high,
                    t.low,
                    t.close,
                    t.volume,
                    t.settle,
                    t.open_interest,
                    t.vwap,
                    t.source_contract,
                    t.adjustment_factor
                FROM timeseries_ohlcv t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.QUOTE:
            query = f"""
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.bid,
                    t.ask,
                    t.mid,
                    t.open_bid,
                    t.bid_high,
                    t.bid_low,
                    t.open_ask,
                    t.ask_high,
                    t.ask_low,
                    t.forward_points
                FROM timeseries_quote t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.RATE:
            query = f"""
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.rate,
                    t.bid,
                    t.ask,
                    t.open_rate,
                    t.high_rate,
                    t.low_rate,
                    t.rate_2,
                    t.spread,
                    t.reference_rate,
                    t.side
                FROM timeseries_rate t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.BOND:
            query = f"""
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.ts as timestamp,
                    t.granularity,
                    t.price,
                    t.dirty_price,
                    t.accrued_interest,
                    t.bid,
                    t.ask,
                    t.open_price,
                    t.open_yield,
                    t.yield,
                    t.yield_bid,
                    t.yield_ask,
                    t.yield_high,
                    t.yield_low,
                    t.mac_duration,
                    t.mod_duration,
                    t.convexity,
                    t.dv01,
                    t.z_spread,
                    t.oas
                FROM timeseries_bond t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE t.granularity = '{granularity.value}'
            """
        elif data_shape == DataShape.FIXING:
            query = """
                SELECT
                    i.symbol,
                    i.asset_class,
                    i.data_shape,
                    i.lseg_ric,
                    t.date,
                    t.value,
                    t.volume
                FROM timeseries_fixing t
                JOIN instruments i ON i.id = t.instrument_id
                WHERE 1=1
            """
        else:
            raise StorageError(f"Unknown data shape: {data_shape}")

        # Add filters
        conditions = []

        if symbol:
            conditions.append(f"AND i.symbol = '{symbol}'")
        if asset_class:
            conditions.append(f"AND i.asset_class = '{asset_class.value}'")
        if start_date:
            if data_shape == DataShape.FIXING:
                conditions.append(f"AND t.date >= '{start_date.isoformat()}'")
            else:
                conditions.append(f"AND t.ts >= '{start_date.isoformat()}'")
        if end_date:
            if data_shape == DataShape.FIXING:
                conditions.append(f"AND t.date <= '{end_date.isoformat()}'")
            else:
                conditions.append(f"AND t.ts <= '{end_date.isoformat()}'")

        query += " " + " ".join(conditions)
        if data_shape == DataShape.FIXING:
            query += " ORDER BY i.symbol, t.date"
        else:
            query += " ORDER BY i.symbol, t.ts"

        # Export to Parquet
        conn.execute(
            f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
        )

        return output_path
    except duckdb.Error as e:
        raise StorageError(f"Failed to export to Parquet: {e}") from e


def export_symbol_to_parquet(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    output_dir: str,
    granularity: Granularity = Granularity.DAILY,
    partition_by_year: bool = True,
) -> list[str]:
    """
    Export a single symbol to Parquet, optionally partitioned by year.

    Routes to the correct timeseries table based on the instrument's data_shape.

    Args:
        conn: Database connection.
        symbol: Instrument symbol to export.
        output_dir: Output directory.
        granularity: Data granularity (default: daily).
        partition_by_year: Whether to partition by year.

    Returns:
        List of exported file paths.

    Raises:
        StorageError: If export fails.
    """
    try:
        # Get instrument info including data_shape
        result = conn.execute(
            "SELECT id, data_shape FROM instruments WHERE symbol = ?", [symbol]
        ).fetchone()
        if result is None:
            raise StorageError(f"Instrument not found: {symbol}")

        instrument_id, instr_data_shape = result
        data_shape = (
            DataShape(instr_data_shape) if instr_data_shape else DataShape.OHLCV
        )

        output_path = Path(output_dir) / symbol
        output_path.mkdir(parents=True, exist_ok=True)

        exported_files = []

        # Build the SELECT clause based on data_shape
        if data_shape == DataShape.OHLCV:
            select_cols = (
                "ts as timestamp, open, high, low, close, volume, "
                "settle, open_interest, vwap"
            )
            table_name = "timeseries_ohlcv"
            time_col = "ts"
        elif data_shape == DataShape.QUOTE:
            select_cols = (
                "ts as timestamp, bid, ask, mid, open_bid, "
                "bid_high, bid_low, forward_points"
            )
            table_name = "timeseries_quote"
            time_col = "ts"
        elif data_shape == DataShape.RATE:
            select_cols = (
                "ts as timestamp, rate, bid, ask, open_rate, high_rate, low_rate, "
                "rate_2, spread, reference_rate, side"
            )
            table_name = "timeseries_rate"
            time_col = "ts"
        elif data_shape == DataShape.BOND:
            select_cols = (
                "ts as timestamp, price, dirty_price, accrued_interest, bid, ask, "
                "open_price, open_yield, yield, yield_bid, yield_ask, "
                "yield_high, yield_low, mac_duration, mod_duration, convexity, dv01"
            )
            table_name = "timeseries_bond"
            time_col = "ts"
        elif data_shape == DataShape.FIXING:
            select_cols = "date, value, volume"
            table_name = "timeseries_fixing"
            time_col = "date"
        else:
            raise StorageError(f"Unknown data shape: {data_shape}")

        if partition_by_year:
            # Get distinct years
            if data_shape == DataShape.FIXING:
                year_query = f"""
                    SELECT DISTINCT EXTRACT(YEAR FROM {time_col}) as year
                    FROM {table_name}
                    WHERE instrument_id = ?
                    ORDER BY year
                """
                params = [instrument_id]
            else:
                year_query = f"""
                    SELECT DISTINCT EXTRACT(YEAR FROM {time_col}) as year
                    FROM {table_name}
                    WHERE instrument_id = ? AND granularity = ?
                    ORDER BY year
                """
                params = [instrument_id, granularity.value]

            years = conn.execute(year_query, params).fetchall()

            for (year,) in years:
                file_path = str(output_path / f"{int(year)}.parquet")
                if data_shape == DataShape.FIXING:
                    query = f"""
                        SELECT {select_cols}
                        FROM {table_name}
                        WHERE instrument_id = {instrument_id}
                        AND EXTRACT(YEAR FROM {time_col}) = {int(year)}
                        ORDER BY {time_col}
                    """
                else:
                    query = f"""
                        SELECT {select_cols}
                        FROM {table_name}
                        WHERE instrument_id = {instrument_id}
                        AND granularity = '{granularity.value}'
                        AND EXTRACT(YEAR FROM {time_col}) = {int(year)}
                        ORDER BY {time_col}
                    """
                conn.execute(
                    f"COPY ({query}) TO '{file_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
                )
                exported_files.append(file_path)
        else:
            file_path = str(output_path / f"{symbol}.parquet")
            if data_shape == DataShape.FIXING:
                query = f"""
                    SELECT {select_cols}
                    FROM {table_name}
                    WHERE instrument_id = {instrument_id}
                    ORDER BY {time_col}
                """
            else:
                query = f"""
                    SELECT {select_cols}
                    FROM {table_name}
                    WHERE instrument_id = {instrument_id}
                    AND granularity = '{granularity.value}'
                    ORDER BY {time_col}
                """
            conn.execute(
                f"COPY ({query}) TO '{file_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
            )
            exported_files.append(file_path)

        return exported_files
    except duckdb.Error as e:
        raise StorageError(f"Failed to export {symbol} to Parquet: {e}") from e
