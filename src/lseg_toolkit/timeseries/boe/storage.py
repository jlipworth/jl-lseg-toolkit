"""BoE data storage operations for PostgreSQL/TimescaleDB."""

from __future__ import annotations

import logging
from datetime import date

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.boe.models import BoEMeeting

logger = logging.getLogger(__name__)


def upsert_boe_meeting(conn: psycopg.Connection, meeting: BoEMeeting) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO boe_meetings (
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


def upsert_boe_meetings(
    conn: psycopg.Connection, meetings: list[BoEMeeting]
) -> int:
    count = 0
    for m in meetings:
        upsert_boe_meeting(conn, m)
        count += 1
    conn.commit()
    return count


def sync_boe_meetings(
    conn: psycopg.Connection,
    api_key: str | None = None,
    allow_missing_rate_history: bool = True,
) -> int:
    from lseg_toolkit.timeseries.boe.fetcher import fetch_boe_meetings

    meetings = fetch_boe_meetings(
        api_key=api_key, allow_missing_rate_history=allow_missing_rate_history
    )
    count = upsert_boe_meetings(conn, meetings)
    logger.info("Upserted %d BoE meetings", count)
    return count


def get_boe_meetings(
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
            f"SELECT * FROM boe_meetings WHERE {where} ORDER BY meeting_date DESC",
            params,
        )
        return list(cur.fetchall())


def get_meeting_count(conn: psycopg.Connection) -> int:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT COUNT(*) AS meeting_count FROM boe_meetings")
        result = cur.fetchone()
        return int(result["meeting_count"]) if result else 0
