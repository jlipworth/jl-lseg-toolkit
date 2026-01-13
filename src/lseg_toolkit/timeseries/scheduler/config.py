"""
Scheduler configuration.

Provides configuration dataclass for the extraction scheduler daemon.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SchedulerConfig:
    """Configuration for the extraction scheduler daemon."""

    # APScheduler settings
    max_workers: int = 4
    coalesce: bool = True  # Combine missed runs into single execution
    misfire_grace_time: int = 300  # 5 minutes grace for missed jobs

    # Rate limiting (must match LSEG API limits)
    rate_limit_delay: float = 0.05  # seconds between requests
    max_rics_per_batch: int = 100  # max RICs per API call

    # Retry settings
    max_retries: int = 3
    retry_base_delay: int = 60  # seconds
    retry_max_delay: int = 3600  # 1 hour cap
    consecutive_failure_threshold: int = 5  # pause instrument after this many failures

    # Intraday constraints
    intraday_retention_days: int = 90  # LSEG intraday data retention

    # Default job settings
    default_lookback_days: int = 5
    default_max_chunk_days: int = 30

    # Priority levels (lower = higher priority)
    priority_realtime: int = 10
    priority_daily_eod: int = 20
    priority_intraday: int = 30
    priority_catchup: int = 50
    priority_backfill: int = 80

    # Session health check interval (seconds)
    session_check_interval: int = 300  # 5 minutes

    @classmethod
    def from_env(cls) -> SchedulerConfig:
        """Load configuration from environment variables."""
        return cls(
            max_workers=int(os.getenv("SCHEDULER_MAX_WORKERS", "4")),
            coalesce=os.getenv("SCHEDULER_COALESCE", "true").lower() == "true",
            misfire_grace_time=int(os.getenv("SCHEDULER_MISFIRE_GRACE", "300")),
            rate_limit_delay=float(os.getenv("SCHEDULER_RATE_LIMIT", "0.05")),
            max_rics_per_batch=int(os.getenv("SCHEDULER_MAX_RICS", "100")),
            max_retries=int(os.getenv("SCHEDULER_MAX_RETRIES", "3")),
            retry_base_delay=int(os.getenv("SCHEDULER_RETRY_DELAY", "60")),
            retry_max_delay=int(os.getenv("SCHEDULER_RETRY_MAX", "3600")),
            consecutive_failure_threshold=int(
                os.getenv("SCHEDULER_FAILURE_THRESHOLD", "5")
            ),
            intraday_retention_days=int(
                os.getenv("SCHEDULER_INTRADAY_RETENTION", "90")
            ),
            default_lookback_days=int(os.getenv("SCHEDULER_LOOKBACK_DAYS", "5")),
            default_max_chunk_days=int(os.getenv("SCHEDULER_MAX_CHUNK_DAYS", "30")),
            session_check_interval=int(
                os.getenv("SCHEDULER_SESSION_CHECK_INTERVAL", "300")
            ),
        )
