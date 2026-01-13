"""
Scheduler daemon.

Long-running daemon for scheduled data extraction using APScheduler.
"""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from typing import TYPE_CHECKING

import lseg.data as rd
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from lseg_toolkit.timeseries.client import LSEGDataClient
from lseg_toolkit.timeseries.config import DatabaseConfig
from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.jobs import ExtractionJob
from lseg_toolkit.timeseries.scheduler.state import get_enabled_jobs
from lseg_toolkit.timeseries.storage import get_connection, init_db

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages LSEG session lifecycle."""

    def __init__(self):
        self._session_open = False
        self._lock = threading.Lock()

    def open(self) -> None:
        """Open LSEG session."""
        with self._lock:
            if not self._session_open:
                logger.info("Opening LSEG session...")
                rd.open_session()
                self._session_open = True
                logger.info("LSEG session opened")

    def close(self) -> None:
        """Close LSEG session."""
        with self._lock:
            if self._session_open:
                logger.info("Closing LSEG session...")
                try:
                    rd.close_session()
                except Exception as e:
                    logger.warning(f"Error closing session: {e}")
                self._session_open = False
                logger.info("LSEG session closed")

    def ensure_open(self) -> bool:
        """
        Ensure session is open, reconnecting if needed.

        Uses two-phase check to avoid holding lock during network I/O.

        Returns:
            True if session is open/reconnected, False if failed.
        """
        # Phase 1: Quick check - if marked open, verify outside lock
        if self._session_open:
            try:
                rd.get_data("EUR=", fields=["DSPLY_NAME"])
                return True
            except Exception as e:
                logger.warning(f"Session check failed: {e}")
                # Mark as closed
                with self._lock:
                    self._session_open = False

        # Phase 2: Reconnect with lock
        with self._lock:
            # Double-check - another thread may have reconnected
            if self._session_open:
                return True

            try:
                logger.info("Reconnecting LSEG session...")
                rd.open_session()
                self._session_open = True
                logger.info("LSEG session reconnected")
                return True
            except Exception as e:
                logger.error(f"Failed to reconnect session: {e}")
                return False

    @property
    def is_open(self) -> bool:
        """Check if session is open (without verification)."""
        return self._session_open


class ExtractionDaemon:
    """
    Long-running daemon for scheduled data extraction.

    Features:
    - APScheduler with in-memory job store (jobs loaded from database)
    - Graceful shutdown on SIGTERM/SIGINT
    - Automatic job recovery on restart
    - Priority-based job execution
    - Session health monitoring
    """

    def __init__(
        self,
        config: SchedulerConfig | None = None,
        db_config: DatabaseConfig | None = None,
    ):
        self.config = config or SchedulerConfig.from_env()
        self.db_config = db_config or DatabaseConfig.from_env()
        self.scheduler: BackgroundScheduler | None = None
        self.client: LSEGDataClient | None = None
        self.session_manager = SessionManager()
        self._shutdown_requested = False
        self._health_check_thread: threading.Thread | None = None

    def setup(self) -> None:
        """Initialize daemon components."""
        logger.info("Setting up extraction daemon...")

        # Initialize database schema
        init_db(self.db_config)

        # Clean up any zombie runs from previous daemon instance
        self._cleanup_zombie_runs()

        # Open LSEG session
        self.session_manager.open()

        # Setup LSEG client
        self.client = LSEGDataClient()

        # Setup APScheduler with in-memory job store
        # Jobs are loaded from scheduler_jobs table on startup
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=self.config.max_workers)}
        job_defaults = {
            "coalesce": self.config.coalesce,
            "misfire_grace_time": self.config.misfire_grace_time,
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="America/New_York",
        )

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("Daemon setup complete")

    def _cleanup_zombie_runs(self) -> None:
        """Mark interrupted runs from previous daemon instance as failed."""
        with get_connection(config=self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE scheduler_runs
                    SET status = 'interrupted',
                        completed_at = NOW(),
                        error_summary = 'Daemon was restarted while job was running'
                    WHERE status = 'running'
                """)
                count = cur.rowcount
                if count > 0:
                    logger.warning(
                        f"Cleaned up {count} interrupted run(s) from previous daemon instance"
                    )
            conn.commit()

    def load_jobs(self) -> int:
        """
        Load job definitions from database and schedule them.

        Returns:
            Number of jobs loaded.
        """
        logger.info("Loading scheduled jobs...")

        with get_connection(config=self.db_config) as conn:
            jobs = get_enabled_jobs(conn)

        count = 0
        for job in jobs:
            try:
                self._schedule_job(job)
                logger.info(f"Scheduled job: {job['name']} ({job['schedule_cron']})")
                count += 1
            except Exception as e:
                logger.error(f"Failed to schedule job {job['name']}: {e}")

        logger.info(f"Loaded {count} jobs")
        return count

    def _schedule_job(self, job: dict) -> None:
        """Schedule a single job with APScheduler."""
        if self.scheduler is None:
            raise RuntimeError("Scheduler not initialized. Call setup() first.")

        trigger = CronTrigger.from_crontab(job["schedule_cron"])

        self.scheduler.add_job(
            func=self._run_job,
            trigger=trigger,
            id=f"job_{job['id']}",
            name=job["name"],
            args=[job["id"]],
            replace_existing=True,
        )

    def _run_job(self, job_id: int) -> None:
        """Execute a scheduled job."""
        logger.info(f"Starting scheduled job {job_id}")

        # Ensure session is open
        if not self.session_manager.ensure_open():
            logger.error(f"Cannot run job {job_id}: LSEG session unavailable")
            return

        try:
            if self.client is None:
                raise RuntimeError("Client not initialized. Call setup() first.")

            with get_connection(config=self.db_config) as conn:
                job_executor = ExtractionJob(
                    job_id=job_id,
                    client=self.client,
                    config=self.config,
                )
                result = job_executor.execute(conn)

            logger.info(
                f"Job {job_id} completed: {result.instruments_success}/{result.instruments_total} "
                f"instruments, {result.rows_extracted} rows, status={result.status}"
            )

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)

    def start(self) -> None:
        """Start the daemon (blocking)."""
        if self.scheduler is None:
            raise RuntimeError("Daemon not set up. Call setup() first.")

        logger.info("Starting extraction daemon...")
        self.scheduler.start()

        # Start session health check thread
        self._start_health_check()

        logger.info("Daemon started. Press Ctrl+C to stop.")

        # Block until shutdown
        while not self._shutdown_requested:
            try:
                time.sleep(1)
            except InterruptedError:
                break

    def _start_health_check(self) -> None:
        """Start background thread for session health monitoring."""

        def health_check_loop():
            while not self._shutdown_requested:
                time.sleep(self.config.session_check_interval)
                if self._shutdown_requested:
                    break
                if not self.session_manager.ensure_open():
                    logger.warning(
                        "Session health check failed, will retry on next check"
                    )

        self._health_check_thread = threading.Thread(
            target=health_check_loop,
            daemon=True,
            name="session-health-check",
        )
        self._health_check_thread.start()

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_requested = True

        if self.scheduler:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=True)

        self.session_manager.close()
        logger.info("Daemon stopped")

    def stop(self) -> None:
        """Stop the daemon programmatically."""
        self._handle_shutdown(signal.SIGTERM, None)


def run_daemon(foreground: bool = True) -> ExtractionDaemon | None:
    """
    Main entry point for running the daemon.

    Args:
        foreground: If True, run in foreground (blocking).

    Returns:
        ExtractionDaemon instance if foreground=False, None otherwise.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )

    logger.info("Initializing LSEG extraction daemon...")

    try:
        config = SchedulerConfig.from_env()
        db_config = DatabaseConfig.from_env()

        daemon = ExtractionDaemon(config, db_config)
        daemon.setup()
        daemon.load_jobs()

        if foreground:
            daemon.start()
            return None
        else:
            # For non-foreground mode, return the daemon
            # (caller is responsible for managing lifecycle)
            return daemon

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Daemon failed: {e}", exc_info=True)
        sys.exit(1)
