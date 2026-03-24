"""
CLI commands for scheduler management.

Provides command-line interface for managing extraction jobs.
"""

from __future__ import annotations

import argparse
import logging
import sys

from lseg_toolkit.timeseries.config import DatabaseConfig
from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.default_jobs import ensure_ff_strip_jobs
from lseg_toolkit.timeseries.scheduler.state import (
    create_job,
    delete_job,
    get_enabled_jobs,
    get_failed_instruments,
    get_job_by_name,
    get_recent_runs,
    reset_instrument_failures,
    update_job_enabled,
)
from lseg_toolkit.timeseries.scheduler.universes import get_available_groups
from lseg_toolkit.timeseries.storage import get_connection

logger = logging.getLogger(__name__)


def main() -> int:
    """Main CLI entry point for scheduler commands."""
    parser = argparse.ArgumentParser(
        description="LSEG Data Extraction Scheduler",
        prog="lseg-scheduler",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Start daemon
    start_parser = subparsers.add_parser("start", help="Start the scheduler daemon")
    start_parser.add_argument(
        "--foreground",
        "-f",
        action="store_true",
        help="Run in foreground (default)",
    )

    # Status
    subparsers.add_parser("status", help="Show daemon status and scheduled jobs")

    # List jobs
    jobs_parser = subparsers.add_parser("jobs", help="List extraction jobs")
    jobs_parser.add_argument(
        "--all", "-a", action="store_true", help="Include disabled jobs"
    )

    # List groups
    subparsers.add_parser("groups", help="List available instrument groups")

    # Add job
    add_parser = subparsers.add_parser("add-job", help="Add a new extraction job")
    add_parser.add_argument("--name", "-n", required=True, help="Job name (unique)")
    add_parser.add_argument("--group", "-g", required=True, help="Instrument group")
    add_parser.add_argument(
        "--granularity",
        required=True,
        choices=[
            "daily",
            "weekly",
            "monthly",
            "hourly",
            "30min",
            "10min",
            "5min",
            "1min",
        ],
        help="Data granularity (tick excluded - use lseg-extract for tick data)",
    )
    add_parser.add_argument(
        "--cron", "-c", required=True, help="Cron schedule (e.g., '0 18 * * 1-5')"
    )
    add_parser.add_argument(
        "--priority",
        "-p",
        type=int,
        default=50,
        help="Priority (1=highest, 100=lowest)",
    )
    add_parser.add_argument("--description", "-d", help="Job description")
    add_parser.add_argument(
        "--lookback", type=int, default=5, help="Lookback days for gap filling"
    )
    add_parser.add_argument(
        "--chunk-days", type=int, default=30, help="Max days per extraction chunk"
    )

    # Seed default FF strip jobs
    subparsers.add_parser(
        "seed-ff-strip",
        help="Create the default FF strip daily/hourly jobs if missing",
    )

    # Enable/disable job
    enable_parser = subparsers.add_parser("enable", help="Enable a job")
    enable_parser.add_argument("name", help="Job name")

    disable_parser = subparsers.add_parser("disable", help="Disable a job")
    disable_parser.add_argument("name", help="Job name")

    # Delete job
    delete_parser = subparsers.add_parser("delete-job", help="Delete a job")
    delete_parser.add_argument("name", help="Job name")
    delete_parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation"
    )

    # Run job manually
    run_parser = subparsers.add_parser("run", help="Run a job manually")
    run_parser.add_argument("name", help="Job name")

    # Show state
    state_parser = subparsers.add_parser("state", help="Show extraction state")
    state_parser.add_argument("--job", "-j", help="Filter by job name")
    state_parser.add_argument(
        "--failed", "-f", action="store_true", help="Show only failed instruments"
    )

    # Reset failures
    reset_parser = subparsers.add_parser(
        "reset", help="Reset failure count for an instrument"
    )
    reset_parser.add_argument("--job", "-j", required=True, help="Job name")
    reset_parser.add_argument("--symbol", "-s", required=True, help="Instrument symbol")

    # History
    history_parser = subparsers.add_parser("history", help="Show job run history")
    history_parser.add_argument("--job", "-j", help="Filter by job name")
    history_parser.add_argument(
        "--limit", "-l", type=int, default=20, help="Number of runs to show"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Dispatch to command handlers
    try:
        if args.command == "start":
            return cmd_start(args)
        elif args.command == "status":
            return cmd_status(args)
        elif args.command == "jobs":
            return cmd_jobs(args)
        elif args.command == "groups":
            return cmd_groups(args)
        elif args.command == "add-job":
            return cmd_add_job(args)
        elif args.command == "seed-ff-strip":
            return cmd_seed_ff_strip(args)
        elif args.command == "enable":
            return cmd_enable(args)
        elif args.command == "disable":
            return cmd_disable(args)
        elif args.command == "delete-job":
            return cmd_delete_job(args)
        elif args.command == "run":
            return cmd_run(args)
        elif args.command == "state":
            return cmd_state(args)
        elif args.command == "reset":
            return cmd_reset(args)
        elif args.command == "history":
            return cmd_history(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        logger.error(f"Command failed: {e}")
        if args.verbose:
            raise
        return 1


def cmd_start(args) -> int:
    """Start the scheduler daemon."""
    from lseg_toolkit.timeseries.scheduler.daemon import run_daemon

    print("Starting scheduler daemon...")
    run_daemon(foreground=True)
    return 0


def cmd_status(args) -> int:
    """Show daemon status and scheduled jobs."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        jobs = get_enabled_jobs(conn)
        runs = get_recent_runs(conn, limit=5)

    print(f"\nEnabled jobs: {len(jobs)}")
    print("-" * 60)

    if jobs:
        print(f"{'Name':<25} {'Group':<20} {'Schedule':<15}")
        print("-" * 60)
        for job in jobs:
            print(
                f"{job['name']:<25} {job['instrument_group']:<20} {job['schedule_cron']:<15}"
            )
    else:
        print("No jobs configured.")

    print("\nRecent runs:")
    print("-" * 60)

    if runs:
        print(f"{'Job':<20} {'Started':<20} {'Status':<10} {'Success':<8}")
        print("-" * 60)
        for run in runs:
            started = (
                run["started_at"].strftime("%Y-%m-%d %H:%M")
                if run["started_at"]
                else "N/A"
            )
            print(
                f"{run['job_name']:<20} {started:<20} {run['status']:<10} {run['instruments_success'] or 0:<8}"
            )
    else:
        print("No recent runs.")

    return 0


def cmd_jobs(args) -> int:
    """List extraction jobs."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT name, instrument_group, granularity, schedule_cron,
                       priority, enabled
                FROM scheduler_jobs
            """
            if not args.all:
                query += " WHERE enabled = TRUE"
            query += " ORDER BY priority, name"
            cur.execute(query)
            rows = list(cur.fetchall())

    if not rows:
        print("No jobs found.")
        return 0

    print(
        f"\n{'Name':<25} {'Group':<20} {'Gran':<8} {'Schedule':<15} {'Pri':<4} {'On':<3}"
    )
    print("-" * 80)

    for row in rows:
        enabled = "Y" if row["enabled"] else "N"
        print(
            f"{row['name']:<25} {row['instrument_group']:<20} "
            f"{row['granularity']:<8} {row['schedule_cron']:<15} "
            f"{row['priority']:<4} {enabled:<3}"
        )

    return 0


def cmd_groups(args) -> int:
    """List available instrument groups."""
    groups = get_available_groups()

    print(f"\nAvailable instrument groups ({len(groups)}):")
    print("-" * 40)

    for group in groups:
        print(f"  {group}")

    return 0


def cmd_add_job(args) -> int:
    """Add a new extraction job."""
    # Validate group exists
    available_groups = get_available_groups()
    if args.group not in available_groups:
        print(f"Error: Unknown group '{args.group}'")
        print(f"Available groups: {', '.join(available_groups)}")
        return 1

    db_config = DatabaseConfig.from_env()

    # Validate cron expression before creating job
    try:
        from apscheduler.triggers.cron import CronTrigger

        CronTrigger.from_crontab(args.cron)
    except (ValueError, KeyError) as e:
        print(f"Error: Invalid cron expression '{args.cron}': {e}")
        return 1

    with get_connection(config=db_config) as conn:
        # Check if job already exists
        existing = get_job_by_name(conn, args.name)
        if existing:
            print(f"Error: Job '{args.name}' already exists")
            return 1

        job_id = create_job(
            conn,
            name=args.name,
            instrument_group=args.group,
            granularity=args.granularity,
            schedule_cron=args.cron,
            description=args.description,
            priority=args.priority,
            lookback_days=args.lookback,
            max_chunk_days=args.chunk_days,
        )
        conn.commit()

    print(f"Created job '{args.name}' (id={job_id})")
    print(f"  Group: {args.group}")
    print(f"  Granularity: {args.granularity}")
    print(f"  Schedule: {args.cron}")
    print(f"  Priority: {args.priority}")

    return 0


def cmd_seed_ff_strip(args) -> int:
    """Create the default FF strip jobs if they do not exist."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        results = ensure_ff_strip_jobs(conn)
        conn.commit()

    for name, action in results.items():
        print(f"{name}: {action}")

    created = sum(1 for action in results.values() if action == "created")
    print(
        f"\nFF strip jobs ready ({created} created, {len(results) - created} existing)"
    )
    return 0


def cmd_enable(args) -> int:
    """Enable a job."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        job = get_job_by_name(conn, args.name)
        if not job:
            print(f"Error: Job '{args.name}' not found")
            return 1

        update_job_enabled(conn, job["id"], True)
        conn.commit()

    print(f"Enabled job '{args.name}'")
    return 0


def cmd_disable(args) -> int:
    """Disable a job."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        job = get_job_by_name(conn, args.name)
        if not job:
            print(f"Error: Job '{args.name}' not found")
            return 1

        update_job_enabled(conn, job["id"], False)
        conn.commit()

    print(f"Disabled job '{args.name}'")
    return 0


def cmd_delete_job(args) -> int:
    """Delete a job."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        job = get_job_by_name(conn, args.name)
        if not job:
            print(f"Error: Job '{args.name}' not found")
            return 1

        if not args.force:
            confirm = input(f"Type '{args.name}' to confirm deletion: ")
            if confirm != args.name:
                print("Cancelled - job name did not match")
                return 0

        delete_job(conn, job["id"])
        conn.commit()

    print(f"Deleted job '{args.name}'")
    return 0


def cmd_run(args) -> int:
    """Run a job manually."""
    import lseg.data as rd

    from lseg_toolkit.timeseries.client import LSEGDataClient
    from lseg_toolkit.timeseries.scheduler.jobs import run_job_now

    db_config = DatabaseConfig.from_env()
    config = SchedulerConfig.from_env()

    with get_connection(config=db_config) as conn:
        job = get_job_by_name(conn, args.name)
        if not job:
            print(f"Error: Job '{args.name}' not found")
            return 1

        print(f"Running job '{args.name}'...")
        print("Opening LSEG session...")

        rd.open_session()
        try:
            client = LSEGDataClient()
            result = run_job_now(conn, job["id"], client, config)
        finally:
            rd.close_session()

    print("\nJob completed:")
    print(f"  Status: {result.status}")
    print(
        f"  Instruments: {result.instruments_success}/{result.instruments_total} success"
    )
    print(f"  Rows extracted: {result.rows_extracted}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors[:10]:
            print(f"  - {err}")

    return 0 if result.status in ("completed", "partial") else 1


def cmd_state(args) -> int:
    """Show extraction state."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        job = None
        if args.job:
            job = get_job_by_name(conn, args.job)
            if not job:
                print(f"Error: Job '{args.job}' not found")
                return 1

        if args.failed:
            # Show failed instruments
            if job:
                rows = get_failed_instruments(conn, job["id"])
            else:
                # Get failed from all jobs
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT s.*, i.symbol, j.name as job_name
                        FROM scheduler_state s
                        JOIN instruments i ON s.instrument_id = i.id
                        JOIN scheduler_jobs j ON s.job_id = j.id
                        WHERE s.consecutive_failures > 0
                        ORDER BY s.consecutive_failures DESC
                    """)
                    rows = list(cur.fetchall())

            if not rows:
                print("No failed instruments.")
                return 0

            print(f"\n{'Job':<20} {'Symbol':<15} {'Failures':<8} {'Error':<40}")
            print("-" * 85)

            for row in rows:
                job_name = row.get("job_name", args.job or "N/A")
                error = (
                    (row["error_message"] or "")[:37] + "..."
                    if row.get("error_message") and len(row["error_message"]) > 40
                    else row.get("error_message", "")
                )
                print(
                    f"{job_name:<20} {row['symbol']:<15} {row['consecutive_failures']:<8} {error:<40}"
                )

        else:
            # Show general state
            with conn.cursor() as cur:
                if job:
                    cur.execute(
                        """
                        SELECT j.name as job_name, COUNT(*) as instruments,
                               SUM(CASE WHEN s.consecutive_failures = 0 THEN 1 ELSE 0 END) as healthy,
                               MAX(s.last_success_date) as last_success
                        FROM scheduler_state s
                        JOIN scheduler_jobs j ON s.job_id = j.id
                        WHERE j.id = %s
                        GROUP BY j.name ORDER BY j.name
                        """,
                        [job["id"]],
                    )
                else:
                    cur.execute("""
                        SELECT j.name as job_name, COUNT(*) as instruments,
                               SUM(CASE WHEN s.consecutive_failures = 0 THEN 1 ELSE 0 END) as healthy,
                               MAX(s.last_success_date) as last_success
                        FROM scheduler_state s
                        JOIN scheduler_jobs j ON s.job_id = j.id
                        GROUP BY j.name ORDER BY j.name
                    """)
                rows = list(cur.fetchall())

            if not rows:
                print("No state data yet.")
                return 0

            print(
                f"\n{'Job':<25} {'Instruments':<12} {'Healthy':<8} {'Last Success':<15}"
            )
            print("-" * 65)

            for row in rows:
                last = row["last_success"].isoformat() if row["last_success"] else "N/A"
                print(
                    f"{row['job_name']:<25} {row['instruments']:<12} {row['healthy']:<8} {last:<15}"
                )

    return 0


def cmd_reset(args) -> int:
    """Reset failure count for an instrument."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        job = get_job_by_name(conn, args.job)
        if not job:
            print(f"Error: Job '{args.job}' not found")
            return 1

        # Find instrument
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM instruments WHERE symbol = %s", [args.symbol])
            result = cur.fetchone()
            if not result:
                print(f"Error: Instrument '{args.symbol}' not found")
                return 1
            instrument_id = result["id"]

        reset_instrument_failures(conn, job["id"], instrument_id)
        conn.commit()

    print(f"Reset failures for '{args.symbol}' in job '{args.job}'")
    return 0


def cmd_history(args) -> int:
    """Show job run history."""
    db_config = DatabaseConfig.from_env()

    with get_connection(config=db_config) as conn:
        job_id = None
        if args.job:
            job = get_job_by_name(conn, args.job)
            if not job:
                print(f"Error: Job '{args.job}' not found")
                return 1
            job_id = job["id"]

        runs = get_recent_runs(conn, job_id=job_id, limit=args.limit)

    if not runs:
        print("No run history.")
        return 0

    print(f"\n{'Job':<20} {'Started':<20} {'Status':<10} {'Success':<8} {'Rows':<10}")
    print("-" * 75)

    for run in runs:
        started = (
            run["started_at"].strftime("%Y-%m-%d %H:%M") if run["started_at"] else "N/A"
        )
        print(
            f"{run['job_name']:<20} {started:<20} {run['status']:<10} "
            f"{run['instruments_success'] or 0:<8} {run['rows_extracted'] or 0:<10}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
