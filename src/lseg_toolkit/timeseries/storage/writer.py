"""
Time series data writing operations for TimescaleDB storage.

This module provides functions for saving time series data using the
PostgreSQL COPY protocol for maximum throughput on bulk inserts.

Performance characteristics:
- COPY protocol: ~100,000+ rows/sec
- COPY + staging upsert: ~50,000+ rows/sec
- Row-by-row INSERT: ~1,000 rows/sec (legacy, avoid)
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import pandas as pd
import psycopg
from psycopg import sql

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.enums import DataShape, Granularity

from .field_mapping import FieldMapper

if TYPE_CHECKING:
    pass

# Default batch size for COPY operations (matches DatabaseConfig)
DEFAULT_BATCH_SIZE = 50_000


@dataclass
class SaveContext:
    """
    Context for saving time series data.

    Encapsulates all parameters needed for save operations, providing
    cleaner function signatures and easier testing.

    Example:
        >>> ctx = SaveContext.for_instrument(conn, instrument_id)
        >>> save_timeseries(conn, df, ctx)
    """

    instrument_id: int
    granularity: Granularity
    data_shape: DataShape
    source_contract: str | None = None
    adjustment_factor: float = 1.0

    @classmethod
    def for_instrument(
        cls,
        conn: psycopg.Connection,
        instrument_id: int,
        granularity: Granularity = Granularity.DAILY,
        **kwargs,
    ) -> SaveContext:
        """
        Factory that looks up data_shape from database.

        Args:
            conn: Database connection.
            instrument_id: Instrument ID.
            granularity: Data granularity.
            **kwargs: Additional context fields (source_contract, adjustment_factor).

        Returns:
            SaveContext with data_shape looked up from instrument.
        """
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data_shape FROM instruments WHERE id = %s", [instrument_id]
            )
            result = cur.fetchone()
        data_shape = DataShape(result["data_shape"]) if result else DataShape.OHLCV
        return cls(
            instrument_id=instrument_id,
            granularity=granularity,
            data_shape=data_shape,
            **kwargs,
        )


def _convert_index_to_timestamp(idx) -> datetime:
    """Convert DataFrame index to timezone-aware timestamp."""
    if hasattr(idx, "to_pydatetime"):
        ts = idx.to_pydatetime()
    elif isinstance(idx, datetime):
        ts = idx
    elif isinstance(idx, date):
        ts = datetime.combine(idx, datetime.min.time())
    else:
        ts = datetime.fromisoformat(str(idx))

    # Ensure timezone-aware (required for TIMESTAMPTZ)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts


def _convert_index_to_date(idx) -> date:
    """Convert DataFrame index to date."""
    if hasattr(idx, "date"):
        return idx.date()
    elif isinstance(idx, date):
        return idx
    else:
        return date.fromisoformat(str(idx)[:10])


def _format_copy_value(value) -> str:
    """Format a value for PostgreSQL COPY protocol."""
    if value is None:
        return r"\N"
    if isinstance(value, float) and pd.isna(value):
        return r"\N"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "t" if value else "f"
    if isinstance(value, (int, float)):
        # Handle numpy types
        import numpy as np

        if isinstance(value, (np.integer,)):
            return str(int(value))
        if isinstance(value, (np.floating,)):
            if np.isnan(value):
                return r"\N"
            return str(float(value))
        return str(value)
    return str(value)


def _bulk_copy(
    conn: psycopg.Connection,
    table: str,
    columns: list[str],
    buffer: io.StringIO,
) -> int:
    """
    Execute COPY FROM for maximum throughput bulk insert.

    Args:
        conn: PostgreSQL connection.
        table: Target table name.
        columns: Column names in order.
        buffer: StringIO buffer with tab-separated COPY data.

    Returns:
        Number of rows copied.
    """
    content = buffer.getvalue()
    row_count = content.count("\n")

    if row_count == 0:
        return 0

    with conn.cursor() as cur:
        with cur.copy(
            sql.SQL("COPY {} ({}) FROM STDIN").format(
                sql.Identifier(table),
                sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            )
        ) as copy:
            copy.write(content)

    return row_count


def _copy_with_upsert(
    conn: psycopg.Connection,
    table: str,
    columns: list[str],
    buffer: io.StringIO,
    conflict_columns: list[str],
) -> int:
    """
    COPY with upsert using staging table pattern.

    This is the recommended approach for bulk upserts:
    1. Create unlogged staging table
    2. COPY data into staging
    3. INSERT ... ON CONFLICT from staging
    4. Truncate staging (reused for next batch)

    Args:
        conn: PostgreSQL connection.
        table: Target table name.
        columns: Column names in order.
        buffer: StringIO buffer with COPY data.
        conflict_columns: Columns that form the unique constraint.

    Returns:
        Number of rows upserted.
    """
    content = buffer.getvalue()
    row_count = content.count("\n")

    if row_count == 0:
        return 0

    staging_table = f"_staging_{table}"

    with conn.cursor() as cur:
        # Recreate staging table from the current target schema. This avoids
        # schema drift when new columns are added to the target table.
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(staging_table)))

        # Create unlogged staging table
        cur.execute(
            sql.SQL("CREATE UNLOGGED TABLE {} (LIKE {} INCLUDING DEFAULTS)").format(
                sql.Identifier(staging_table),
                sql.Identifier(table),
            )
        )

        # COPY into staging
        with cur.copy(
            sql.SQL("COPY {} ({}) FROM STDIN").format(
                sql.Identifier(staging_table),
                sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            )
        ) as copy:
            copy.write(content)

        # Build update clause (exclude conflict columns from update)
        update_columns = [c for c in columns if c not in conflict_columns]

        if update_columns:
            update_clause = sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
                for c in update_columns
            )

            cur.execute(
                sql.SQL(
                    """
                INSERT INTO {} ({})
                SELECT {} FROM {}
                ON CONFLICT ({}) DO UPDATE SET {}
            """
                ).format(
                    sql.Identifier(table),
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                    sql.Identifier(staging_table),
                    sql.SQL(", ").join(sql.Identifier(c) for c in conflict_columns),
                    update_clause,
                )
            )
        else:
            # No columns to update, just insert ignoring conflicts
            cur.execute(
                sql.SQL(
                    """
                INSERT INTO {} ({})
                SELECT {} FROM {}
                ON CONFLICT ({}) DO NOTHING
            """
                ).format(
                    sql.Identifier(table),
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                    sql.Identifier(staging_table),
                    sql.SQL(", ").join(sql.Identifier(c) for c in conflict_columns),
                )
            )

    return row_count


def save_timeseries(
    conn: psycopg.Connection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity = Granularity.DAILY,
    source_contract: str | None = None,
    adjustment_factor: float = 1.0,
    data_shape: DataShape | None = None,
    upsert: bool = True,
) -> int:
    """
    Save time series data to database using vectorized COPY.

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
        upsert: If True, update existing rows; if False, skip conflicts.

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
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data_shape FROM instruments WHERE id = %s", [instrument_id]
                )
                result = cur.fetchone()
            if result:
                data_shape = DataShape(result["data_shape"])
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
                upsert,
            )
        elif data_shape == DataShape.QUOTE:
            return _save_quote_data(conn, instrument_id, data, granularity, upsert)
        elif data_shape == DataShape.RATE:
            return _save_rate_data(conn, instrument_id, data, granularity, upsert)
        elif data_shape == DataShape.BOND:
            return _save_bond_data(conn, instrument_id, data, granularity, upsert)
        elif data_shape == DataShape.FIXING:
            return _save_fixing_data(conn, instrument_id, data, upsert)
        else:
            # Fallback to OHLCV for unknown shapes
            return _save_ohlcv_data(
                conn,
                instrument_id,
                data,
                granularity,
                source_contract,
                adjustment_factor,
                upsert,
            )
    except psycopg.Error as e:
        raise StorageError(f"Failed to save time series: {e}") from e


def _save_ohlcv_data(
    conn: psycopg.Connection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
    source_contract: str | None,
    adjustment_factor: float,
    upsert: bool,
) -> int:
    """Save OHLCV data using COPY protocol."""
    table = "timeseries_ohlcv"
    columns = [
        "instrument_id",
        "ts",
        "session_date",
        "granularity",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "settle",
        "open_interest",
        "bid",
        "ask",
        "mid",
        "implied_rate",
        "vwap",
        "source_contract",
        "adjustment_factor",
    ]
    conflict_columns = ["instrument_id", "ts", "granularity"]

    buffer = io.StringIO()
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)
        try:
            extracted = FieldMapper.extract_row(row, "ohlcv")
        except ValueError as exc:
            if "Required field 'close'" in str(exc):
                continue
            raise

        values = [
            _format_copy_value(instrument_id),
            _format_copy_value(ts),
            _format_copy_value(extracted.get("session_date")),
            _format_copy_value(granularity.value),
            _format_copy_value(extracted.get("open")),
            _format_copy_value(extracted.get("high")),
            _format_copy_value(extracted.get("low")),
            _format_copy_value(extracted.get("close")),
            _format_copy_value(extracted.get("volume")),
            _format_copy_value(extracted.get("settle")),
            _format_copy_value(extracted.get("open_interest")),
            _format_copy_value(extracted.get("bid")),
            _format_copy_value(extracted.get("ask")),
            _format_copy_value(extracted.get("mid")),
            _format_copy_value(extracted.get("implied_rate")),
            _format_copy_value(extracted.get("vwap")),
            _format_copy_value(row.get("source_contract", source_contract)),
            _format_copy_value(row.get("adjustment_factor", adjustment_factor)),
        ]
        buffer.write("\t".join(values) + "\n")

    buffer.seek(0)

    if upsert:
        return _copy_with_upsert(conn, table, columns, buffer, conflict_columns)
    else:
        return _bulk_copy(conn, table, columns, buffer)


def _save_quote_data(
    conn: psycopg.Connection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
    upsert: bool,
) -> int:
    """Save quote data using COPY protocol."""
    table = "timeseries_quote"
    columns = [
        "instrument_id",
        "ts",
        "granularity",
        "bid",
        "ask",
        "mid",
        "open_bid",
        "bid_high",
        "bid_low",
        "open_ask",
        "ask_high",
        "ask_low",
        "forward_points",
    ]
    conflict_columns = ["instrument_id", "ts", "granularity"]

    buffer = io.StringIO()
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)
        extracted = FieldMapper.extract_row(row, "quote")

        # Calculate mid if not provided
        mid = extracted.get("mid")
        if mid is None:
            mid = FieldMapper.calculate_mid(extracted.get("bid"), extracted.get("ask"))

        values = [
            _format_copy_value(instrument_id),
            _format_copy_value(ts),
            _format_copy_value(granularity.value),
            _format_copy_value(extracted.get("bid")),
            _format_copy_value(extracted.get("ask")),
            _format_copy_value(mid),
            _format_copy_value(extracted.get("open_bid")),
            _format_copy_value(extracted.get("bid_high")),
            _format_copy_value(extracted.get("bid_low")),
            _format_copy_value(extracted.get("open_ask")),
            _format_copy_value(extracted.get("ask_high")),
            _format_copy_value(extracted.get("ask_low")),
            _format_copy_value(extracted.get("forward_points")),
        ]
        buffer.write("\t".join(values) + "\n")

    buffer.seek(0)

    if upsert:
        return _copy_with_upsert(conn, table, columns, buffer, conflict_columns)
    else:
        return _bulk_copy(conn, table, columns, buffer)


def _save_rate_data(
    conn: psycopg.Connection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
    upsert: bool,
) -> int:
    """Save rate data using COPY protocol."""
    table = "timeseries_rate"
    columns = [
        "instrument_id",
        "ts",
        "granularity",
        "rate",
        "bid",
        "ask",
        "open_rate",
        "high_rate",
        "low_rate",
        "rate_2",
        "spread",
        "reference_rate",
        "side",
    ]
    conflict_columns = ["instrument_id", "ts", "granularity"]

    buffer = io.StringIO()
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)
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

        values = [
            _format_copy_value(instrument_id),
            _format_copy_value(ts),
            _format_copy_value(granularity.value),
            _format_copy_value(rate),
            _format_copy_value(extracted.get("bid")),
            _format_copy_value(extracted.get("ask")),
            _format_copy_value(open_rate),
            _format_copy_value(extracted.get("high_rate")),
            _format_copy_value(extracted.get("low_rate")),
            _format_copy_value(extracted.get("rate_2")),
            _format_copy_value(extracted.get("spread")),
            _format_copy_value(row.get("reference_rate")),
            _format_copy_value(row.get("side")),
        ]
        buffer.write("\t".join(values) + "\n")

    buffer.seek(0)

    if upsert:
        return _copy_with_upsert(conn, table, columns, buffer, conflict_columns)
    else:
        return _bulk_copy(conn, table, columns, buffer)


def _save_bond_data(
    conn: psycopg.Connection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity,
    upsert: bool,
) -> int:
    """Save bond data using COPY protocol."""
    table = "timeseries_bond"
    columns = [
        "instrument_id",
        "ts",
        "granularity",
        "price",
        "dirty_price",
        "accrued_interest",
        "bid",
        "ask",
        "open_price",
        "open_yield",
        "yield",
        "yield_bid",
        "yield_ask",
        "yield_high",
        "yield_low",
        "mac_duration",
        "mod_duration",
        "convexity",
        "dv01",
        "z_spread",
        "oas",
    ]
    conflict_columns = ["instrument_id", "ts", "granularity"]

    buffer = io.StringIO()
    for idx, row in data.iterrows():
        ts = _convert_index_to_timestamp(idx)
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

        values = [
            _format_copy_value(instrument_id),
            _format_copy_value(ts),
            _format_copy_value(granularity.value),
            _format_copy_value(clean_price),
            _format_copy_value(dirty),
            _format_copy_value(accrued),
            _format_copy_value(extracted.get("bid")),
            _format_copy_value(extracted.get("ask")),
            _format_copy_value(extracted.get("open_price")),
            _format_copy_value(extracted.get("open_yield")),
            _format_copy_value(yld),
            _format_copy_value(extracted.get("yield_bid")),
            _format_copy_value(extracted.get("yield_ask")),
            _format_copy_value(extracted.get("yield_high")),
            _format_copy_value(extracted.get("yield_low")),
            _format_copy_value(extracted.get("mac_duration")),
            _format_copy_value(extracted.get("mod_duration")),
            _format_copy_value(extracted.get("convexity")),
            _format_copy_value(extracted.get("dv01")),
            _format_copy_value(extracted.get("z_spread")),
            _format_copy_value(extracted.get("oas")),
        ]
        buffer.write("\t".join(values) + "\n")

    buffer.seek(0)

    if upsert:
        return _copy_with_upsert(conn, table, columns, buffer, conflict_columns)
    else:
        return _bulk_copy(conn, table, columns, buffer)


def _save_fixing_data(
    conn: psycopg.Connection,
    instrument_id: int,
    data: pd.DataFrame,
    upsert: bool,
) -> int:
    """Save fixing data using COPY protocol."""
    table = "timeseries_fixing"
    columns = ["instrument_id", "date", "value", "volume"]
    conflict_columns = ["instrument_id", "date"]

    buffer = io.StringIO()
    for idx, row in data.iterrows():
        dt = _convert_index_to_date(idx)
        extracted = FieldMapper.extract_row(row, "fixing")

        values = [
            _format_copy_value(instrument_id),
            _format_copy_value(dt),
            _format_copy_value(extracted.get("value")),
            _format_copy_value(extracted.get("volume")),
        ]
        buffer.write("\t".join(values) + "\n")

    buffer.seek(0)

    if upsert:
        return _copy_with_upsert(conn, table, columns, buffer, conflict_columns)
    else:
        return _bulk_copy(conn, table, columns, buffer)
