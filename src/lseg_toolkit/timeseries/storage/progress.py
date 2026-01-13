"""
Extraction progress tracking for batch data operations.

This module provides functions for tracking the progress of data extractions,
including extraction logs and batch progress records.
"""

from __future__ import annotations

from datetime import date

import psycopg

from lseg_toolkit.timeseries.enums import Granularity

from .instruments import get_instrument_id


def log_extraction(
    conn: psycopg.Connection,
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

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extraction_log (
                instrument_id, start_date, end_date, granularity, rows_fetched
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            [instrument_id, start_date, end_date, granularity.value, rows_fetched],
        )


def create_extraction_progress(
    conn: psycopg.Connection,
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
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extraction_progress (
                asset_class, instrument, start_date, end_date, status
            )
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id
            """,
            [asset_class, instrument, start_date, end_date],
        )
        progress_id = cur.fetchone()[0]
    return progress_id


def update_extraction_progress(
    conn: psycopg.Connection,
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
    with conn.cursor() as cur:
        if status == "running":
            cur.execute(
                """
                UPDATE extraction_progress
                SET status = %s, started_at = current_timestamp
                WHERE id = %s
                """,
                [status, progress_id],
            )
        elif status == "complete":
            cur.execute(
                """
                UPDATE extraction_progress
                SET status = %s, rows_fetched = %s, completed_at = current_timestamp
                WHERE id = %s
                """,
                [status, rows_fetched, progress_id],
            )
        elif status == "failed":
            cur.execute(
                """
                UPDATE extraction_progress
                SET status = %s, error_message = %s, completed_at = current_timestamp
                WHERE id = %s
                """,
                [status, error_message, progress_id],
            )


def get_extraction_progress(
    conn: psycopg.Connection,
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
        query += " AND asset_class = %s"
        params.append(asset_class)
    if instrument:
        query += " AND instrument = %s"
        params.append(instrument)
    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY id"

    with conn.cursor() as cur:
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
