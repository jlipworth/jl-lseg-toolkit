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


RATE_DECISION_JOB_SPECS: list[DefaultJobSpec] = [
    DefaultJobSpec(
        name="ois_usd_daily",
        instrument_group="ois_usd",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily USD OIS curve",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="ois_eur_daily",
        instrument_group="ois_eur",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily EUR OIS (ESTR-linked)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="ois_gbp_daily",
        instrument_group="ois_gbp",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily GBP OIS (SONIA-linked)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="ois_g7_daily",
        instrument_group="ois_g7",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily G7 OIS (covers CAD, JPY, CHF, AUD, NZD)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="benchmark_fixings_daily",
        instrument_group="benchmark_fixings",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily overnight benchmarks (SOFR, ESTR, GBPOND, CADCORRA, etc.)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="euribor_fixings_daily",
        instrument_group="euribor_fixings",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily EURIBOR fixings (1M/3M/6M/12M)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
]


def _eur_ois_unwired() -> bool:
    """True iff EUR OIS RICs aren't (or aren't yet) wired to a working pattern."""
    try:
        from lseg_toolkit.timeseries.constants import EUR_OIS_TENORS
    except ImportError:
        return True
    return not EUR_OIS_TENORS


def ensure_rate_decision_jobs(
    conn,
    *,
    skip_eur_ois: bool | None = None,
) -> dict[str, str]:
    """Ensure the rate-decision-modeling jobs exist.

    ``skip_eur_ois``:
        - ``None`` (default): auto-skip if ``EUR_OIS_TENORS`` is missing/empty.
        - ``True``: always skip ``ois_eur_daily``.
        - ``False``: always include ``ois_eur_daily``.

    Returns a mapping of job name to action (``created``, ``exists``, or ``skipped``).
    """
    if skip_eur_ois is None:
        skip_eur_ois = _eur_ois_unwired()

    results: dict[str, str] = {}
    for spec in RATE_DECISION_JOB_SPECS:
        if spec.name == "ois_eur_daily" and skip_eur_ois:
            results[spec.name] = "skipped"
            continue
        if get_job_by_name(conn, spec.name):
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
