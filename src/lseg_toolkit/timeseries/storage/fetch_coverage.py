"""Persist successful provider requests, independently of returned row density.

Coverage and returned rows are written in the same transaction. Do not infer
coverage from MIN/MAX timestamps: valid no-trading intervals contain no rows.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import psycopg

from lseg_toolkit.timeseries.enums import Granularity


def load_fetch_coverage(
    conn: psycopg.Connection[dict[str, Any]],
    instrument_id: int,
    granularity: Granularity,
    start: date,
    end: date,
) -> list[tuple[date, date]]:
    """Read successful request intervals overlapping this inclusive date range."""
    rows = conn.execute(
        """SELECT start_date, end_date FROM fetch_coverage
           WHERE instrument_id = %s AND granularity = %s
             AND start_date <= %s AND end_date >= %s
           ORDER BY start_date, end_date""",
        (instrument_id, granularity.value, end, start),
    ).fetchall()
    return [(row["start_date"], row["end_date"]) for row in rows]


def save_fetch_coverage(
    conn: psycopg.Connection[dict[str, Any]],
    instrument_id: int,
    granularity: Granularity,
    start: date,
    end: date,
) -> None:
    """Record only completed provider calls; caller owns commit/rollback."""
    # Today's bars can still arrive, and future empty responses are not durable
    # coverage. UTC matches the provider's intraday timestamp convention.
    end = min(end, datetime.now(UTC).date() - timedelta(days=1))
    if start > end:
        return
    conn.execute(
        """INSERT INTO fetch_coverage
               (instrument_id, granularity, start_date, end_date)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (instrument_id, granularity, start_date, end_date)
           DO UPDATE SET fetched_at = NOW()""",
        (instrument_id, granularity.value, start, end),
    )
