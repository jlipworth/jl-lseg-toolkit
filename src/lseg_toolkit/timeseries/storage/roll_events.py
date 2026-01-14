"""
Roll event tracking for continuous futures contracts.

This module provides functions for recording and retrieving roll events
when continuous futures contracts switch from one underlying contract to another.
"""

from __future__ import annotations

from datetime import date

import psycopg

from lseg_toolkit.exceptions import StorageError

from .instruments import get_instrument_id


def save_roll_event(
    conn: psycopg.Connection,
    continuous_symbol: str,
    roll_date: date,
    from_contract: str,
    to_contract: str,
    from_price: float,
    to_price: float,
    roll_method: str,
) -> int:
    """
    Save a roll event for a continuous contract.

    Args:
        conn: Database connection.
        continuous_symbol: Symbol of continuous contract.
        roll_date: Date of the roll.
        from_contract: Contract being rolled out of.
        to_contract: Contract being rolled into.
        from_price: Price of from_contract at roll.
        to_price: Price of to_contract at roll.
        roll_method: Method used to determine roll.

    Returns:
        Roll event ID.

    Raises:
        StorageError: If save fails.
    """
    instrument_id = get_instrument_id(conn, continuous_symbol)
    if instrument_id is None:
        raise StorageError(f"Instrument not found: {continuous_symbol}")

    price_gap = to_price - from_price
    adjustment_factor = to_price / from_price if from_price != 0 else 1.0

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO roll_events (
                    continuous_id, roll_date, from_contract, to_contract,
                    from_price, to_price, price_gap, adjustment_factor, roll_method
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [
                    instrument_id,
                    roll_date,
                    from_contract,
                    to_contract,
                    from_price,
                    to_price,
                    price_gap,
                    adjustment_factor,
                    roll_method,
                ],
            )
            roll_id = cur.fetchone()["id"]
        return roll_id
    except psycopg.Error as e:
        raise StorageError(f"Failed to save roll event: {e}") from e


def get_roll_events(conn: psycopg.Connection, continuous_symbol: str) -> list[dict]:
    """
    Get roll events for a continuous contract.

    Args:
        conn: Database connection.
        continuous_symbol: Symbol of continuous contract.

    Returns:
        List of roll event dicts.
    """
    instrument_id = get_instrument_id(conn, continuous_symbol)
    if instrument_id is None:
        return []

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT roll_date, from_contract, to_contract,
                   from_price, to_price, price_gap, adjustment_factor, roll_method
            FROM roll_events
            WHERE continuous_id = %s
            ORDER BY roll_date ASC
            """,
            [instrument_id],
        )
        # With dict_row, fetchall() returns list of dicts directly
        return [dict(row) for row in cur.fetchall()]
