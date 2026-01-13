"""
Scheduler state management.

Database operations for tracking job definitions, extraction state, and run history.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg


# =============================================================================
# Job Operations
# =============================================================================


def get_enabled_jobs(conn: psycopg.Connection) -> list[dict]:
    """Get all enabled job definitions."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, description, instrument_group, granularity,
                   schedule_cron, priority, lookback_days, max_chunk_days
            FROM scheduler_jobs
            WHERE enabled = TRUE
            ORDER BY priority, name
        """)
        return list(cur.fetchall())


def get_job_by_name(conn: psycopg.Connection, name: str) -> dict | None:
    """Get job definition by name."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, description, instrument_group, granularity,
                   schedule_cron, priority, enabled, lookback_days, max_chunk_days
            FROM scheduler_jobs
            WHERE name = %s
        """,
            [name],
        )
        return cur.fetchone()


def get_job_by_id(conn: psycopg.Connection, job_id: int) -> dict | None:
    """Get job definition by ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, description, instrument_group, granularity,
                   schedule_cron, priority, enabled, lookback_days, max_chunk_days
            FROM scheduler_jobs
            WHERE id = %s
        """,
            [job_id],
        )
        return cur.fetchone()


def create_job(
    conn: psycopg.Connection,
    name: str,
    instrument_group: str,
    granularity: str,
    schedule_cron: str,
    description: str | None = None,
    priority: int = 50,
    lookback_days: int = 5,
    max_chunk_days: int = 30,
) -> int:
    """Create a new job definition."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scheduler_jobs
                (name, description, instrument_group, granularity, schedule_cron,
                 priority, lookback_days, max_chunk_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            [
                name,
                description,
                instrument_group,
                granularity,
                schedule_cron,
                priority,
                lookback_days,
                max_chunk_days,
            ],
        )
        result = cur.fetchone()
        return result["id"]


def update_job_enabled(conn: psycopg.Connection, job_id: int, enabled: bool) -> None:
    """Enable or disable a job."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scheduler_jobs
            SET enabled = %s, updated_at = NOW()
            WHERE id = %s
        """,
            [enabled, job_id],
        )


def delete_job(conn: psycopg.Connection, job_id: int) -> None:
    """Delete a job and its associated state."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM scheduler_jobs WHERE id = %s", [job_id])


# =============================================================================
# State Operations
# =============================================================================


def get_instrument_state(
    conn: psycopg.Connection, job_id: int, instrument_id: int
) -> dict | None:
    """Get extraction state for a specific instrument in a job."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, job_id, instrument_id, last_success_date,
                   last_attempt_at, last_success_at, consecutive_failures,
                   next_retry_at, error_message
            FROM scheduler_state
            WHERE job_id = %s AND instrument_id = %s
        """,
            [job_id, instrument_id],
        )
        return cur.fetchone()


def upsert_instrument_state(
    conn: psycopg.Connection,
    job_id: int,
    instrument_id: int,
    success: bool,
    last_date: date | None = None,
    error_message: str | None = None,
    retry_delay_seconds: int = 3600,
) -> None:
    """Update or insert extraction state for an instrument."""
    now = datetime.now()

    if success:
        # Success: reset failures, update success timestamp
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scheduler_state
                    (job_id, instrument_id, last_success_date, last_attempt_at,
                     last_success_at, consecutive_failures, error_message)
                VALUES (%s, %s, %s, %s, %s, 0, NULL)
                ON CONFLICT (job_id, instrument_id) DO UPDATE SET
                    last_success_date = COALESCE(EXCLUDED.last_success_date, scheduler_state.last_success_date),
                    last_attempt_at = EXCLUDED.last_attempt_at,
                    last_success_at = EXCLUDED.last_success_at,
                    consecutive_failures = 0,
                    next_retry_at = NULL,
                    error_message = NULL
            """,
                [job_id, instrument_id, last_date, now, now],
            )
    else:
        # Failure: increment failures, set retry time
        next_retry = now + timedelta(seconds=retry_delay_seconds)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scheduler_state
                    (job_id, instrument_id, last_attempt_at, consecutive_failures,
                     next_retry_at, error_message)
                VALUES (%s, %s, %s, 1, %s, %s)
                ON CONFLICT (job_id, instrument_id) DO UPDATE SET
                    last_attempt_at = EXCLUDED.last_attempt_at,
                    consecutive_failures = scheduler_state.consecutive_failures + 1,
                    next_retry_at = EXCLUDED.next_retry_at,
                    error_message = EXCLUDED.error_message
            """,
                [job_id, instrument_id, now, next_retry, error_message],
            )


def get_failed_instruments(
    conn: psycopg.Connection, job_id: int, min_failures: int = 1
) -> list[dict]:
    """Get instruments with consecutive failures for a job."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.*, i.symbol
            FROM scheduler_state s
            JOIN instruments i ON s.instrument_id = i.id
            WHERE s.job_id = %s AND s.consecutive_failures >= %s
            ORDER BY s.consecutive_failures DESC
        """,
            [job_id, min_failures],
        )
        return list(cur.fetchall())


def get_instruments_ready_for_retry(
    conn: psycopg.Connection, job_id: int
) -> list[dict]:
    """Get instruments that are past their retry time."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.*, i.symbol
            FROM scheduler_state s
            JOIN instruments i ON s.instrument_id = i.id
            WHERE s.job_id = %s
              AND s.consecutive_failures > 0
              AND s.next_retry_at <= NOW()
            ORDER BY s.next_retry_at
        """,
            [job_id],
        )
        return list(cur.fetchall())


def reset_instrument_failures(
    conn: psycopg.Connection, job_id: int, instrument_id: int
) -> None:
    """Reset failure count for an instrument (manual intervention)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scheduler_state
            SET consecutive_failures = 0, next_retry_at = NULL, error_message = NULL
            WHERE job_id = %s AND instrument_id = %s
        """,
            [job_id, instrument_id],
        )


# =============================================================================
# Run Operations
# =============================================================================


def create_run(conn: psycopg.Connection, job_id: int, instruments_total: int) -> int:
    """Create a new job run record."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scheduler_runs (job_id, instruments_total, status)
            VALUES (%s, %s, 'running')
            RETURNING id
        """,
            [job_id, instruments_total],
        )
        result = cur.fetchone()
        return result["id"]


def complete_run(
    conn: psycopg.Connection,
    run_id: int,
    status: str,
    instruments_success: int,
    instruments_failed: int,
    rows_extracted: int,
    error_summary: str | None = None,
) -> None:
    """Complete a job run record."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scheduler_runs
            SET completed_at = NOW(),
                status = %s,
                instruments_success = %s,
                instruments_failed = %s,
                rows_extracted = %s,
                error_summary = %s
            WHERE id = %s
        """,
            [
                status,
                instruments_success,
                instruments_failed,
                rows_extracted,
                error_summary,
                run_id,
            ],
        )


def get_recent_runs(
    conn: psycopg.Connection, job_id: int | None = None, limit: int = 20
) -> list[dict]:
    """Get recent job runs."""
    with conn.cursor() as cur:
        if job_id:
            cur.execute(
                """
                SELECT r.*, j.name as job_name
                FROM scheduler_runs r
                JOIN scheduler_jobs j ON r.job_id = j.id
                WHERE r.job_id = %s
                ORDER BY r.started_at DESC
                LIMIT %s
            """,
                [job_id, limit],
            )
        else:
            cur.execute(
                """
                SELECT r.*, j.name as job_name
                FROM scheduler_runs r
                JOIN scheduler_jobs j ON r.job_id = j.id
                ORDER BY r.started_at DESC
                LIMIT %s
            """,
                [limit],
            )
        return list(cur.fetchall())


def get_running_jobs(conn: psycopg.Connection) -> list[dict]:
    """Get currently running jobs."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.*, j.name as job_name
            FROM scheduler_runs r
            JOIN scheduler_jobs j ON r.job_id = j.id
            WHERE r.status = 'running'
            ORDER BY r.started_at
        """)
        return list(cur.fetchall())
