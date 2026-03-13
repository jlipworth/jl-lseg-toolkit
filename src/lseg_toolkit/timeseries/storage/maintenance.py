"""
Maintenance helpers for TimescaleDB/PostgreSQL time series storage.

Includes targeted backfills for schema additions that need to be
applied to existing historical data.
"""

from __future__ import annotations

import psycopg


def backfill_ff_continuous_session_dates(conn: psycopg.Connection) -> int:
    """
    Backfill ``session_date`` for existing FF_CONTINUOUS OHLCV rows.

    Rules:
    - daily rows use the UTC calendar date of ``ts``
    - hourly rows use the observed LSEG/CME session boundary:
      ``session_date = ((ts AT TIME ZONE 'UTC') + INTERVAL '2 hours')::date``

    Only rows with NULL ``session_date`` are updated.

    Args:
        conn: PostgreSQL connection.

    Returns:
        Number of rows updated.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE timeseries_ohlcv AS t
            SET session_date = CASE
                WHEN t.granularity = 'daily'
                    THEN (t.ts AT TIME ZONE 'UTC')::date
                WHEN t.granularity = 'hourly'
                    THEN ((t.ts AT TIME ZONE 'UTC') + INTERVAL '2 hours')::date
                ELSE t.session_date
            END
            FROM instruments AS i
            WHERE t.instrument_id = i.id
              AND i.symbol = 'FF_CONTINUOUS'
              AND t.session_date IS NULL
              AND t.granularity IN ('daily', 'hourly')
            """
        )
        return max(cur.rowcount or 0, 0)
