"""
Scheduler package for persistent LSEG data extraction.

This package provides a long-running daemon that schedules and executes
data extraction jobs based on instrument groups and cron schedules.
"""

from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.daemon import ExtractionDaemon, run_daemon
from lseg_toolkit.timeseries.scheduler.jobs import ExtractionJob, run_job_now
from lseg_toolkit.timeseries.scheduler.models import (
    ExtractionResult,
    InstrumentSpec,
    JobRunResult,
)
from lseg_toolkit.timeseries.scheduler.universes import (
    build_universe,
    get_available_groups,
)

__all__ = [
    # Config
    "SchedulerConfig",
    # Daemon
    "ExtractionDaemon",
    "run_daemon",
    # Jobs
    "ExtractionJob",
    "run_job_now",
    # Models
    "ExtractionResult",
    "InstrumentSpec",
    "JobRunResult",
    # Universes
    "build_universe",
    "get_available_groups",
]
