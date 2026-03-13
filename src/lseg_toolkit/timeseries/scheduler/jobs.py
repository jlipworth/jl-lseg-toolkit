"""
Job execution logic.

Handles the extraction of data for scheduled jobs.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

from lseg_toolkit.timeseries.cache import detect_gaps
from lseg_toolkit.timeseries.enums import Granularity
from lseg_toolkit.timeseries.fed_funds import (
    fetch_fed_funds_daily,
    fetch_fed_funds_hourly,
)
from lseg_toolkit.timeseries.scheduler.config import SchedulerConfig
from lseg_toolkit.timeseries.scheduler.models import (
    ExtractionResult,
    InstrumentSpec,
    JobRunResult,
)
from lseg_toolkit.timeseries.scheduler.state import (
    complete_run,
    create_run,
    get_instrument_state,
    get_job_by_id,
    upsert_instrument_state,
)
from lseg_toolkit.timeseries.scheduler.universes import build_universe
from lseg_toolkit.timeseries.storage import (
    get_instrument_id,
    save_instrument,
    save_timeseries,
)

if TYPE_CHECKING:
    import psycopg

    from lseg_toolkit.timeseries.client import LSEGDataClient

logger = logging.getLogger(__name__)


class ExtractionJob:
    """
    Executes an extraction job for a group of instruments.

    Handles:
    - Gap detection (incremental fetches)
    - Chunked backfills for large date ranges
    - Rate limiting
    - Error handling with retries
    - State persistence
    """

    def __init__(
        self,
        job_id: int,
        client: LSEGDataClient,
        config: SchedulerConfig,
    ):
        self.job_id = job_id
        self.client = client
        self.config = config

    def execute(self, conn: psycopg.Connection) -> JobRunResult:
        """
        Execute the job for all instruments.

        Args:
            conn: Database connection.

        Returns:
            JobRunResult with summary of extraction.
        """
        # 1. Load job definition
        job = get_job_by_id(conn, self.job_id)
        if job is None:
            raise ValueError(f"Job {self.job_id} not found")

        logger.info(
            f"Starting job {job['name']} (group={job['instrument_group']}, granularity={job['granularity']})"
        )

        # 2. Build instrument universe
        try:
            instruments = build_universe(job["instrument_group"])
        except ValueError as e:
            logger.error(f"Failed to build universe for job {job['name']}: {e}")
            raise

        if not instruments:
            logger.warning(f"No instruments in universe for job {job['name']}")
            return JobRunResult(
                job_id=self.job_id,
                run_id=0,
                status="completed",
                instruments_total=0,
                instruments_success=0,
                instruments_failed=0,
                rows_extracted=0,
                errors=[],
            )

        # 3. Ensure all instruments are registered
        instrument_ids = self._ensure_instruments(conn, instruments)

        # 4. Create run record
        run_id = create_run(conn, self.job_id, len(instruments))
        conn.commit()

        # 5. Process each instrument
        results: list[ExtractionResult] = []
        for spec, instrument_id in zip(instruments, instrument_ids, strict=True):
            result = self._extract_instrument(conn, spec, instrument_id, job)
            results.append(result)
            conn.commit()  # Commit after each instrument

        # 6. Complete run record
        success_count = sum(1 for r in results if r.success)
        failed_count = sum(1 for r in results if not r.success)
        total_rows = sum(r.rows_extracted for r in results)
        errors = [f"{r.symbol}: {r.error}" for r in results if r.error]

        status = (
            "completed"
            if failed_count == 0
            else ("partial" if success_count > 0 else "failed")
        )
        error_summary = "; ".join(errors[:5]) if errors else None  # First 5 errors

        complete_run(
            conn,
            run_id,
            status,
            instruments_success=success_count,
            instruments_failed=failed_count,
            rows_extracted=total_rows,
            error_summary=error_summary,
        )
        conn.commit()

        logger.info(
            f"Job {job['name']} completed: {success_count}/{len(instruments)} instruments, "
            f"{total_rows} rows extracted"
        )

        return JobRunResult(
            job_id=self.job_id,
            run_id=run_id,
            status=status,
            instruments_total=len(instruments),
            instruments_success=success_count,
            instruments_failed=failed_count,
            rows_extracted=total_rows,
            errors=errors,
        )

    def _ensure_instruments(
        self, conn: psycopg.Connection, instruments: list[InstrumentSpec]
    ) -> list[int]:
        """Ensure all instruments are registered and return their IDs."""
        ids = []
        for spec in instruments:
            # Check if exists
            instrument_id = get_instrument_id(conn, spec.symbol)
            if instrument_id is None:
                # Register new instrument
                instrument_id = save_instrument(
                    conn,
                    symbol=spec.symbol,
                    name=spec.name or spec.symbol,
                    asset_class=spec.asset_class,
                    lseg_ric=spec.ric,
                    data_shape=spec.data_shape,
                )
                logger.info(
                    f"Registered new instrument: {spec.symbol} (id={instrument_id})"
                )
            ids.append(instrument_id)
        return ids

    def _extract_instrument(
        self,
        conn: psycopg.Connection,
        spec: InstrumentSpec,
        instrument_id: int,
        job: dict,
    ) -> ExtractionResult:
        """Extract data for a single instrument."""
        granularity = Granularity(job["granularity"])
        lookback_days = job["lookback_days"]
        max_chunk_days = job["max_chunk_days"]
        state: dict | None = None  # Initialize before try block for exception handler

        try:
            # Load state to find last successful date
            state = get_instrument_state(conn, self.job_id, instrument_id)

            # Determine date range to fetch
            end_date = date.today()
            if state and state.get("last_success_date"):
                # Incremental: start from last success
                start_date = state["last_success_date"]
            else:
                # Initial: use lookback
                start_date = end_date - timedelta(days=lookback_days)

            # For intraday, cap at retention limit
            if granularity in (
                Granularity.HOURLY,
                Granularity.MINUTE_5,
                Granularity.MINUTE_1,
            ):
                retention_limit = end_date - timedelta(
                    days=self.config.intraday_retention_days
                )
                start_date = max(start_date, retention_limit)

            # Detect gaps in existing data
            gaps = detect_gaps(conn, spec.symbol, start_date, end_date, granularity)

            if not gaps:
                # No gaps, already up to date
                upsert_instrument_state(
                    conn, self.job_id, instrument_id, success=True, last_date=end_date
                )
                logger.debug(f"{spec.symbol}: No gaps, up to date")
                return ExtractionResult(
                    instrument_id=instrument_id,
                    symbol=spec.symbol,
                    success=True,
                    rows_extracted=0,
                )

            # Fetch data for each gap, chunked if needed
            total_rows = 0
            for gap in gaps:
                rows = self._fetch_gap(
                    conn,
                    spec,
                    instrument_id,
                    gap.start,
                    gap.end,
                    granularity,
                    max_chunk_days,
                )
                total_rows += rows

            # Update state on success
            upsert_instrument_state(
                conn, self.job_id, instrument_id, success=True, last_date=end_date
            )

            logger.info(
                f"{spec.symbol}: Extracted {total_rows} rows ({start_date} to {end_date})"
            )

            return ExtractionResult(
                instrument_id=instrument_id,
                symbol=spec.symbol,
                success=True,
                rows_extracted=total_rows,
                start_date=start_date,
                end_date=end_date,
            )

        except Exception as e:
            logger.error(f"{spec.symbol}: Extraction failed - {e}")
            # Update state on failure
            retry_delay = self.config.retry_base_delay * (
                2 ** min(state.get("consecutive_failures", 0) if state else 0, 5)
            )
            upsert_instrument_state(
                conn,
                self.job_id,
                instrument_id,
                success=False,
                error_message=str(e)[:500],
                retry_delay_seconds=min(retry_delay, self.config.retry_max_delay),
            )
            return ExtractionResult(
                instrument_id=instrument_id,
                symbol=spec.symbol,
                success=False,
                error=str(e),
            )

    def _fetch_gap(
        self,
        conn: psycopg.Connection,
        spec: InstrumentSpec,
        instrument_id: int,
        start_date: date,
        end_date: date,
        granularity: Granularity,
        max_chunk_days: int,
    ) -> int:
        """Fetch data for a gap, chunking if necessary."""
        total_rows = 0
        current = start_date

        while current <= end_date:
            chunk_end = min(current + timedelta(days=max_chunk_days - 1), end_date)

            logger.debug(
                f"{spec.symbol}: Fetching {current} to {chunk_end} ({granularity.value})"
            )

            df = self._fetch_timeseries(spec, current, chunk_end, granularity)

            if df is not None and not df.empty:
                # Save to database
                rows = save_timeseries(
                    conn,
                    instrument_id,
                    df,
                    granularity,
                    data_shape=spec.data_shape,
                )
                total_rows += rows
                logger.debug(
                    f"{spec.symbol}: Saved {rows} rows for {current} to {chunk_end}"
                )

            current = chunk_end + timedelta(days=1)

        return total_rows

    def _fetch_timeseries(
        self,
        spec: InstrumentSpec,
        start_date: date,
        end_date: date,
        granularity: Granularity,
    ):
        """
        Fetch timeseries for one instrument/date chunk.

        FF_CONTINUOUS must use the dedicated Fed Funds extraction path so
        session_date and source_contract are populated correctly.
        """
        if spec.symbol == "FF_CONTINUOUS":
            if granularity == Granularity.DAILY:
                return fetch_fed_funds_daily(self.client, start_date, end_date)
            if granularity == Granularity.HOURLY:
                return fetch_fed_funds_hourly(self.client, start_date, end_date)
            raise ValueError(
                "FF_CONTINUOUS scheduler jobs currently support only daily/hourly granularity"
            )

        return self.client.get_history(
            rics=spec.ric,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=granularity.value,
        )


def run_job_now(
    conn: psycopg.Connection,
    job_id: int,
    client: LSEGDataClient,
    config: SchedulerConfig | None = None,
) -> JobRunResult:
    """
    Run a job immediately (manual trigger).

    Args:
        conn: Database connection.
        job_id: Job ID to run.
        client: LSEG data client.
        config: Optional scheduler config (uses defaults if not provided).

    Returns:
        JobRunResult with extraction summary.
    """
    if config is None:
        config = SchedulerConfig()

    job = ExtractionJob(job_id, client, config)
    return job.execute(conn)
