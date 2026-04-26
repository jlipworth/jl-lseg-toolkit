"""BoC data storage operations for PostgreSQL/TimescaleDB."""

from __future__ import annotations

import logging
from datetime import date

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.boc.models import BoCMeeting

logger = logging.getLogger(__name__)


def upsert_boc_meeting(conn: psycopg.Connection, meeting: BoCMeeting) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO boc_meetings (
                meeting_date, meeting_start_date, rate_upper, rate_lower,
                rate_change_bps, decision, dissent_count, vote_for, vote_against,
                statement_url, minutes_url, is_scheduled, has_sep, has_presser, source,
                updated_at
            ) VALUES (
                %(meeting_date)s, %(meeting_start_date)s, %(rate_upper)s, %(rate_lower)s,
                %(rate_change_bps)s, %(decision)s, %(dissent_count)s, %(vote_for)s, %(vote_against)s,
                %(statement_url)s, %(minutes_url)s, %(is_scheduled)s, %(has_sep)s, %(has_presser)s,
                %(source)s, NOW()
            )
            ON CONFLICT (meeting_date) DO UPDATE SET
                meeting_start_date = EXCLUDED.meeting_start_date,
                rate_upper = EXCLUDED.rate_upper,
                rate_lower = EXCLUDED.rate_lower,
                rate_change_bps = EXCLUDED.rate_change_bps,
                decision = EXCLUDED.decision,
                dissent_count = EXCLUDED.dissent_count,
                vote_for = EXCLUDED.vote_for,
                vote_against = EXCLUDED.vote_against,
                statement_url = EXCLUDED.statement_url,
                minutes_url = EXCLUDED.minutes_url,
                is_scheduled = EXCLUDED.is_scheduled,
                has_sep = EXCLUDED.has_sep,
                has_presser = EXCLUDED.has_presser,
                source = EXCLUDED.source,
                updated_at = NOW()
            RETURNING id
            """,
            {
                "meeting_date": meeting.meeting_date,
                "meeting_start_date": meeting.meeting_start_date,
                "rate_upper": meeting.rate_upper,
                "rate_lower": meeting.rate_lower,
                "rate_change_bps": meeting.rate_change_bps,
                "decision": meeting.decision.value if meeting.decision else None,
                "dissent_count": meeting.dissent_count,
                "vote_for": meeting.vote_for,
                "vote_against": meeting.vote_against,
                "statement_url": meeting.statement_url,
                "minutes_url": meeting.minutes_url,
                "is_scheduled": meeting.is_scheduled,
                "has_sep": meeting.has_sep,
                "has_presser": meeting.has_presser,
                "source": meeting.source,
            },
        )
        result = cur.fetchone()
        return result["id"] if result else 0


def upsert_boc_meetings(
    conn: psycopg.Connection, meetings: list[BoCMeeting]
) -> int:
    count = 0
    for m in meetings:
        upsert_boc_meeting(conn, m)
        count += 1
    conn.commit()
    return count


def sync_boc_meetings(
    conn: psycopg.Connection,
    allow_missing_rate_history: bool = True,
) -> int:
    from lseg_toolkit.timeseries.boc.fetcher import fetch_boc_meetings

    meetings = fetch_boc_meetings(allow_missing_rate_history=allow_missing_rate_history)
    count = upsert_boc_meetings(conn, meetings)
    logger.info("Upserted %d BoC meetings", count)
    return count


def get_boc_meetings(
    conn: psycopg.Connection,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    conditions = []
    params: dict = {}
    if start_date:
        conditions.append("meeting_date >= %(start_date)s")
        params["start_date"] = start_date
    if end_date:
        conditions.append("meeting_date <= %(end_date)s")
        params["end_date"] = end_date
    where = " AND ".join(conditions) if conditions else "TRUE"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT * FROM boc_meetings WHERE {where} ORDER BY meeting_date DESC",
            params,
        )
        return list(cur.fetchall())


def get_meeting_count(conn: psycopg.Connection) -> int:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT COUNT(*) AS meeting_count FROM boc_meetings")
        result = cur.fetchone()
        return int(result["meeting_count"]) if result else 0
