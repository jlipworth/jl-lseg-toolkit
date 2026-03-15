"""
FOMC data storage operations for PostgreSQL/TimescaleDB.
"""

from __future__ import annotations

import logging
from datetime import date

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.fomc.models import FOMCMeeting

logger = logging.getLogger(__name__)


def upsert_fomc_meeting(conn: psycopg.Connection, meeting: FOMCMeeting) -> int:
    """Insert or update a single FOMC meeting record."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fomc_meetings (
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


def upsert_fomc_meetings(
    conn: psycopg.Connection,
    meetings: list[FOMCMeeting],
) -> int:
    """Insert or update multiple FOMC meeting records."""
    count = 0
    for meeting in meetings:
        upsert_fomc_meeting(conn, meeting)
        count += 1
    conn.commit()
    return count


def sync_fomc_meetings(
    conn: psycopg.Connection,
    api_key: str | None = None,
    allow_missing_rate_history: bool = True,
) -> int:
    """Fetch FOMC meetings and upsert them into PostgreSQL."""
    from lseg_toolkit.timeseries.fomc.fetcher import fetch_fomc_meetings

    meetings = fetch_fomc_meetings(
        api_key=api_key,
        allow_missing_rate_history=allow_missing_rate_history,
    )
    count = upsert_fomc_meetings(conn, meetings)
    logger.info("Upserted %d FOMC meetings", count)
    return count


def get_fomc_meetings(
    conn: psycopg.Connection,
    start_date: date | None = None,
    end_date: date | None = None,
    decision: str | None = None,
) -> list[dict]:
    """Query FOMC meetings from the database."""
    conditions = []
    params: dict = {}

    if start_date:
        conditions.append("meeting_date >= %(start_date)s")
        params["start_date"] = start_date
    if end_date:
        conditions.append("meeting_date <= %(end_date)s")
        params["end_date"] = end_date
    if decision:
        conditions.append("decision = %(decision)s")
        params["decision"] = decision

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT * FROM fomc_meetings
            WHERE {where_clause}
            ORDER BY meeting_date DESC
            """,
            params,
        )
        return list(cur.fetchall())


def get_fomc_meeting_by_date(
    conn: psycopg.Connection,
    meeting_date: date,
) -> dict | None:
    """Get a single FOMC meeting by date."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM fomc_meetings WHERE meeting_date = %s",
            (meeting_date,),
        )
        return cur.fetchone()


def get_next_fomc_meeting(conn: psycopg.Connection) -> dict | None:
    """Get the next upcoming FOMC meeting."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT * FROM fomc_meetings
            WHERE meeting_date > CURRENT_DATE
            ORDER BY meeting_date ASC
            LIMIT 1
            """
        )
        return cur.fetchone()


def get_meeting_count(conn: psycopg.Connection) -> int:
    """Get total count of FOMC meetings in database."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT COUNT(*) AS meeting_count FROM fomc_meetings")
        result = cur.fetchone()
        return int(result["meeting_count"]) if result else 0


def get_meeting_date_range(conn: psycopg.Connection) -> tuple[date | None, date | None]:
    """Get earliest and latest meeting dates in database."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                MIN(meeting_date) AS earliest_meeting_date,
                MAX(meeting_date) AS latest_meeting_date
            FROM fomc_meetings
            """
        )
        result = cur.fetchone()
        if not result:
            return (None, None)
        return (result["earliest_meeting_date"], result["latest_meeting_date"])
