"""
Default scheduler job definitions.

Provides convenience helpers for creating standard job sets in the scheduler DB.
"""

from __future__ import annotations

from dataclasses import dataclass

from lseg_toolkit.timeseries.scheduler.state import create_job, get_job_by_name


@dataclass(frozen=True)
class DefaultJobSpec:
    """Definition for a default scheduler job."""

    name: str
    instrument_group: str
    granularity: str
    schedule_cron: str
    description: str
    priority: int
    lookback_days: int
    max_chunk_days: int


FF_STRIP_JOB_SPECS = [
    DefaultJobSpec(
        name="STIR_FF_STRIP_DAILY",
        instrument_group="stir_ff",
        granularity="daily",
        schedule_cron="30 18 * * 1-5",
        description="Daily Fed Funds continuous strip (FFc1-FFc12)",
        priority=40,
        lookback_days=10,
        max_chunk_days=30,
    ),
    DefaultJobSpec(
        name="STIR_FF_STRIP_HOURLY",
        instrument_group="stir_ff",
        granularity="hourly",
        schedule_cron="5 * * * 0-5",
        description="Hourly Fed Funds continuous strip (FFc1-FFc12)",
        priority=35,
        lookback_days=3,
        max_chunk_days=7,
    ),
]


def ensure_ff_strip_jobs(conn) -> dict[str, str]:
    """
    Ensure the default FF strip jobs exist.

    Returns:
        Mapping of job name to action: ``created`` or ``exists``.
    """
    results: dict[str, str] = {}

    for spec in FF_STRIP_JOB_SPECS:
        existing = get_job_by_name(conn, spec.name)
        if existing:
            results[spec.name] = "exists"
            continue

        create_job(
            conn,
            name=spec.name,
            instrument_group=spec.instrument_group,
            granularity=spec.granularity,
            schedule_cron=spec.schedule_cron,
            description=spec.description,
            priority=spec.priority,
            lookback_days=spec.lookback_days,
            max_chunk_days=spec.max_chunk_days,
        )
        results[spec.name] = "created"

    return results
