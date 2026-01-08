"""
Extraction progress tracking for batch data operations.

This module provides functions for tracking the progress of data extractions,
including extraction logs and batch progress records.
"""

from __future__ import annotations

from datetime import date

import duckdb

from lseg_toolkit.timeseries.enums import Granularity

from .instruments import get_instrument_id


def log_extraction(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    start_date: date,
    end_date: date,
    granularity: Granularity,
    rows_fetched: int,
) -> None:
    """
    Log an extraction event.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        start_date: Extraction start date.
        end_date: Extraction end date.
        granularity: Data granularity.
        rows_fetched: Number of rows fetched.
    """
    instrument_id = get_instrument_id(conn, symbol)
    if instrument_id is None:
        return

    log_id = conn.execute("SELECT nextval('seq_extraction_log')").fetchone()[0]
    conn.execute(
        """
        INSERT INTO extraction_log (
            id, instrument_id, start_date, end_date, granularity, rows_fetched
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [log_id, instrument_id, start_date, end_date, granularity.value, rows_fetched],
    )


def create_extraction_progress(
    conn: duckdb.DuckDBPyConnection,
    asset_class: str,
    instrument: str,
    start_date: date,
    end_date: date,
) -> int:
    """
    Create an extraction progress record.

    Args:
        conn: Database connection.
        asset_class: Asset class being extracted.
        instrument: Instrument symbol.
        start_date: Extraction start date.
        end_date: Extraction end date.

    Returns:
        Progress record ID.
    """
    progress_id = conn.execute("SELECT nextval('seq_extraction_progress')").fetchone()[
        0
    ]
    conn.execute(
        """
        INSERT INTO extraction_progress (
            id, asset_class, instrument, start_date, end_date, status
        )
        VALUES (?, ?, ?, ?, ?, 'pending')
        """,
        [progress_id, asset_class, instrument, start_date, end_date],
    )
    return progress_id


def update_extraction_progress(
    conn: duckdb.DuckDBPyConnection,
    progress_id: int,
    status: str,
    rows_fetched: int | None = None,
    error_message: str | None = None,
) -> None:
    """
    Update extraction progress record.

    Args:
        conn: Database connection.
        progress_id: Progress record ID.
        status: New status ('running', 'complete', 'failed').
        rows_fetched: Number of rows fetched (optional).
        error_message: Error message if failed (optional).
    """
    if status == "running":
        conn.execute(
            """
            UPDATE extraction_progress
            SET status = ?, started_at = current_timestamp
            WHERE id = ?
            """,
            [status, progress_id],
        )
    elif status == "complete":
        conn.execute(
            """
            UPDATE extraction_progress
            SET status = ?, rows_fetched = ?, completed_at = current_timestamp
            WHERE id = ?
            """,
            [status, rows_fetched, progress_id],
        )
    elif status == "failed":
        conn.execute(
            """
            UPDATE extraction_progress
            SET status = ?, error_message = ?, completed_at = current_timestamp
            WHERE id = ?
            """,
            [status, error_message, progress_id],
        )


def get_extraction_progress(
    conn: duckdb.DuckDBPyConnection,
    asset_class: str | None = None,
    instrument: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """
    Get extraction progress records.

    Args:
        conn: Database connection.
        asset_class: Filter by asset class.
        instrument: Filter by instrument.
        status: Filter by status.

    Returns:
        List of progress record dicts.
    """
    query = "SELECT * FROM extraction_progress WHERE 1=1"
    params = []

    if asset_class:
        query += " AND asset_class = ?"
        params.append(asset_class)
    if instrument:
        query += " AND instrument = ?"
        params.append(instrument)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id"

    result = conn.execute(query, params)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
