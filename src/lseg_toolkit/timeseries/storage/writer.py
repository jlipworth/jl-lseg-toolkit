"""
Time series data writing operations for DuckDB storage.

This module provides functions for saving time series data to the database,
with support for all data shapes (OHLCV, Quote, Rate, Bond, Fixing).
"""

from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.enums import DataShape, Granularity

from .field_mapping import FieldMapper


def _convert_index_to_timestamp(idx) -> datetime:
    """Convert DataFrame index to timestamp."""
    if hasattr(idx, "to_pydatetime"):
        return idx.to_pydatetime()
    elif isinstance(idx, datetime):
        return idx
    elif isinstance(idx, date):
        return datetime.combine(idx, datetime.min.time())
    else:
        return datetime.fromisoformat(str(idx))


def _to_native(value):
    """Convert numpy types to native Python types for DuckDB compatibility."""
    import numpy as np

    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _bulk_insert(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    records: list[dict],
    conflict: str = "REPLACE",
) -> int:
    """
    Bulk insert records into a table.

    Args:
        conn: Database connection.
        table: Target table name.
        records: List of dicts with column -> value.
        conflict: 'REPLACE' or 'IGNORE'.

    Returns:
        Number of rows inserted.
    """
    if not records:
        return 0

    columns = list(records[0].keys())
    placeholders = ", ".join(["?" for _ in columns])
    col_list = ", ".join(columns)

    sql = f"INSERT OR {conflict} INTO {table} ({col_list}) VALUES ({placeholders})"  # noqa: S608

    for record in records:
        # Convert numpy types to native Python types
        values = [_to_native(record[col]) for col in columns]
        conn.execute(sql, values)

    return len(records)


def save_timeseries(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity = Granularity.DAILY,
    source_contract: str | None = None,
    adjustment_factor: float = 1.0,
    data_shape: DataShape | None = None,
) -> int:
    """
    Save time series data to database.

    Routes data to the correct timeseries table based on data_shape:
    - OHLCV: timeseries_ohlcv (futures, equities, commodities)
    - QUOTE: timeseries_quote (FX spot, FX forwards)
    - RATE: timeseries_rate (OIS, IRS, FRA, repo)
    - BOND: timeseries_bond (govt yields, corp bonds)
    - FIXING: timeseries_fixing (SOFR, ESTR, SONIA)

    Args:
        conn: Database connection.
        instrument_id: Instrument ID.
        data: DataFrame with DatetimeIndex and appropriate columns.
        granularity: Data granularity.
        source_contract: Source contract for continuous series (OHLCV only).
        adjustment_factor: Adjustment factor for continuous series (OHLCV only).
        data_shape: Data shape for routing (auto-detected from instrument if None).

    Returns:
        Number of rows saved.

    Raises:
        StorageError: If save fails.
    """
    if data.empty:
        return 0

    try:
        # Auto-detect data_shape from instrument if not provided
        if data_shape is None:
            result = conn.execute(
                "SELECT data_shape FROM instruments WHERE id = ?", [instrument_id]
            ).fetchone()
            if result:
                data_shape = DataShape(result[0])
            else:
                data_shape = DataShape.OHLCV  # Default fallback

        # Route to appropriate save function based on data_shape
        if data_shape == DataShape.OHLCV:
            return _save_ohlcv_data(
                conn,
                instrument_id,
                data,
                granularity,
                source_contract,
                adjustment_factor,
            )
        elif data_shape == DataShape.QUOTE:
            return _save_quote_data(conn, instrument_id, data, granularity)
        elif data_shape == DataShape.RATE:
            return _save_rate_data(conn, instrument_id, data, granularity)
        elif data_shape == DataShape.BOND:
            return _save_bond_data(conn, instrument_id, data, granularity)
        elif data_shape == DataShape.FIXING:
            return _save_fixing_data(conn, instrument_id, data)
        else:
            # Fallback to OHLCV for unknown shapes
            return _save_ohlcv_data(
                conn,
                instrument_id,
                data,
                granularity,
                source_contract,
                adjustment_factor,
            )
    except duckdb.Error as e:
        raise StorageError(f"Failed to save time series: {e}") from e


def _save_ohlcv_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
    source_contract: str | None,
    adjustment_factor: float,
) -> int:
    """Save OHLCV data (futures, equities, commodities) to timeseries_ohlcv."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Use FieldMapper for field extraction with fallbacks
        extracted = FieldMapper.extract_row(row, "ohlcv")

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "open": extracted.get("open"),
                "high": extracted.get("high"),
                "low": extracted.get("low"),
                "close": extracted.get("close"),
                "volume": extracted.get("volume"),
                "settle": extracted.get("settle"),
                "open_interest": extracted.get("open_interest"),
                "vwap": extracted.get("vwap"),
                "source_contract": source_contract,
                "adjustment_factor": adjustment_factor,
            }
        )

    return _bulk_insert(conn, "timeseries_ohlcv", rows)


def _save_quote_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save quote data (FX spot, FX forwards) to timeseries_quote."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Use FieldMapper for field extraction with fallbacks
        extracted = FieldMapper.extract_row(row, "quote")

        # Calculate mid if not provided
        mid = extracted.get("mid")
        if mid is None:
            mid = FieldMapper.calculate_mid(extracted.get("bid"), extracted.get("ask"))

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "bid": extracted.get("bid"),
                "ask": extracted.get("ask"),
                "mid": mid,
                "open_bid": extracted.get("open_bid"),
                "bid_high": extracted.get("bid_high"),
                "bid_low": extracted.get("bid_low"),
                "open_ask": extracted.get("open_ask"),
                "ask_high": extracted.get("ask_high"),
                "ask_low": extracted.get("ask_low"),
                "forward_points": extracted.get("forward_points"),
            }
        )

    return _bulk_insert(conn, "timeseries_quote", rows)


def _save_rate_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save rate data (OIS, IRS, FRA, repo) to timeseries_rate."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Use FieldMapper for field extraction with fallbacks
        extracted = FieldMapper.extract_row(row, "rate")

        # Calculate rate from bid/ask if not provided
        rate = extracted.get("rate")
        if rate is None:
            rate = FieldMapper.calculate_mid(extracted.get("bid"), extracted.get("ask"))

        # Calculate open_rate from open_bid/open_ask if needed
        open_rate = extracted.get("open_rate")
        if open_rate is None:
            open_bid = row.get("open_bid") or row.get("OPEN_BID")
            open_ask = row.get("open_ask") or row.get("OPEN_ASK")
            if open_bid is not None and open_ask is not None:
                if not pd.isna(open_bid) and not pd.isna(open_ask):
                    open_rate = (float(open_bid) + float(open_ask)) / 2

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "rate": rate,
                "bid": extracted.get("bid"),
                "ask": extracted.get("ask"),
                "open_rate": open_rate,
                "high_rate": extracted.get("high_rate"),
                "low_rate": extracted.get("low_rate"),
                "rate_2": extracted.get("rate_2"),
                "spread": extracted.get("spread"),
                "reference_rate": row.get("reference_rate"),
                "side": row.get("side"),
            }
        )

    return _bulk_insert(conn, "timeseries_rate", rows)


def _save_bond_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
) -> int:
    """Save bond data (govt yields, corp bonds) to timeseries_bond."""
    rows = []
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)

        # Use FieldMapper for field extraction with fallbacks
        extracted = FieldMapper.extract_row(row, "bond")

        # Calculate yield from bid/ask if not provided
        yld = extracted.get("yield")
        if yld is None:
            yld = FieldMapper.calculate_mid(
                extracted.get("yield_bid"), extracted.get("yield_ask")
            )

        # Calculate dirty price if we have clean + accrued but no dirty
        dirty = extracted.get("dirty_price")
        clean_price = extracted.get("price")
        accrued = extracted.get("accrued_interest")
        if dirty is None and clean_price is not None and accrued is not None:
            if not pd.isna(clean_price) and not pd.isna(accrued):
                dirty = float(clean_price) + float(accrued)

        rows.append(
            {
                "instrument_id": instrument_id,
                "ts": ts,
                "granularity": granularity.value,
                "price": clean_price,
                "dirty_price": dirty,
                "accrued_interest": accrued,
                "bid": extracted.get("bid"),
                "ask": extracted.get("ask"),
                "open_price": extracted.get("open_price"),
                "open_yield": extracted.get("open_yield"),
                "yield": yld,
                "yield_bid": extracted.get("yield_bid"),
                "yield_ask": extracted.get("yield_ask"),
                "yield_high": extracted.get("yield_high"),
                "yield_low": extracted.get("yield_low"),
                "mac_duration": extracted.get("mac_duration"),
                "mod_duration": extracted.get("mod_duration"),
                "convexity": extracted.get("convexity"),
                "dv01": extracted.get("dv01"),
                "z_spread": extracted.get("z_spread"),
                "oas": extracted.get("oas"),
            }
        )

    return _bulk_insert(conn, "timeseries_bond", rows)


def _save_fixing_data(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
) -> int:
    """Save fixing data (SOFR, ESTR, SONIA) to timeseries_fixing.

    Note: Fixings are daily only, no granularity parameter.
    """
    rows = []
    for idx, row in data.iterrows():
        # Convert index to date
        if hasattr(idx, "date"):
            dt = idx.date()
        elif isinstance(idx, date):
            dt = idx
        else:
            dt = date.fromisoformat(str(idx)[:10])

        # Use FieldMapper for field extraction with fallbacks
        extracted = FieldMapper.extract_row(row, "fixing")

        rows.append(
            {
                "instrument_id": instrument_id,
                "date": dt,
                "value": extracted.get("value"),
                "volume": extracted.get("volume"),
            }
        )

    return _bulk_insert(conn, "timeseries_fixing", rows)
