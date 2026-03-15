"""
FOMC data fetching from FRED API, FedTools, and the Fed calendar page.

FRED API:
- DFEDTARU: Fed funds target rate upper bound
- DFEDTARL: Fed funds target rate lower bound

FedTools:
- MonetaryPolicyCommittee: Scrapes Fed website for historical meeting dates
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import httpx

from lseg_toolkit.timeseries.fomc.calendar_scraper import fetch_future_fomc_meetings
from lseg_toolkit.timeseries.fomc.models import FOMCMeeting, RateDecision

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
logger = logging.getLogger(__name__)


def get_fred_api_key() -> str:
    """Get FRED API key from environment."""
    import os

    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise ValueError(
            "FRED_API_KEY environment variable not set. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return key


def fetch_fed_funds_rate_history(
    api_key: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    """
    Fetch Fed Funds target rate history from FRED.

    Returns both upper (DFEDTARU) and lower (DFEDTARL) bounds.
    """
    if api_key is None:
        api_key = get_fred_api_key()

    def fetch_series(series_id: str) -> dict[str, float]:
        params: dict = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "asc",
        }
        if start_date:
            params["observation_start"] = start_date.isoformat()
        if end_date:
            params["observation_end"] = end_date.isoformat()

        resp = httpx.get(
            f"{FRED_BASE_URL}/series/observations",
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            obs["date"]: float(obs["value"])
            for obs in data.get("observations", [])
            if obs.get("value") and obs["value"] != "."
        }

    upper = fetch_series("DFEDTARU")
    lower = fetch_series("DFEDTARL")

    all_dates = sorted(set(upper.keys()) | set(lower.keys()))
    return [
        {
            "date": datetime.strptime(d, "%Y-%m-%d").date(),
            "upper": upper.get(d),
            "lower": lower.get(d),
        }
        for d in all_dates
    ]


def fetch_fomc_dates_from_fedtools() -> list[date]:
    """
    Fetch historical FOMC announcement dates using FedTools library.
    """
    try:
        from FedTools import MonetaryPolicyCommittee
    except ImportError as e:
        raise ImportError(
            "FedTools not installed. Install with: pip install FedTools"
        ) from e

    mpc = MonetaryPolicyCommittee(verbose=False)
    statements = mpc.find_statements()
    dates = [d.date() for d in statements.index.tolist()]
    return sorted(dates)


def build_fomc_meetings(
    dates: list[date],
    rate_history: list[dict] | None = None,
) -> list[FOMCMeeting]:
    """
    Build historical FOMCMeeting records from meeting dates and FRED rate history.
    """
    meetings: list[FOMCMeeting] = []
    prev_rate: float | None = None

    for meeting_date in sorted(dates):
        rate_upper: float | None = None
        rate_lower: float | None = None

        if rate_history:
            for rate_row in rate_history:
                if rate_row["date"] >= meeting_date:
                    rate_upper = rate_row.get("upper")
                    rate_lower = rate_row.get("lower")
                    break

        rate_change_bps: int | None = None
        decision: RateDecision | None = None
        if rate_upper is not None and prev_rate is not None:
            change = rate_upper - prev_rate
            rate_change_bps = int(round(change * 100))
            if rate_change_bps > 0:
                decision = RateDecision.HIKE
            elif rate_change_bps < 0:
                decision = RateDecision.CUT
            else:
                decision = RateDecision.HOLD

        meetings.append(
            FOMCMeeting(
                meeting_date=meeting_date,
                meeting_start_date=meeting_date - timedelta(days=1),
                rate_upper=rate_upper,
                rate_lower=rate_lower,
                rate_change_bps=rate_change_bps,
                decision=decision,
                has_sep=meeting_date.month in (3, 6, 9, 12),
                has_presser=True,
                source="fedtools",
            )
        )

        if rate_upper is not None:
            prev_rate = rate_upper

    return meetings


def fetch_fomc_meetings(
    api_key: str | None = None,
    allow_missing_rate_history: bool = False,
) -> list[FOMCMeeting]:
    """
    Fetch historical FOMC meetings and append future scheduled meetings.
    """
    dates = fetch_fomc_dates_from_fedtools()

    rate_history: list[dict] | None = None
    try:
        rate_history = fetch_fed_funds_rate_history(api_key)
    except ValueError:
        if not allow_missing_rate_history:
            raise
        logger.warning(
            "FRED API key unavailable; syncing FOMC meetings without rate history"
        )

    meetings = build_fomc_meetings(dates, rate_history)

    try:
        future_meetings = fetch_future_fomc_meetings()
    except Exception:
        logger.warning(
            "Failed to fetch future scheduled FOMC meetings from Fed calendar",
            exc_info=True,
        )
        future_meetings = []

    combined = {meeting.meeting_date: meeting for meeting in meetings}
    for meeting in future_meetings:
        combined.setdefault(meeting.meeting_date, meeting)

    return [combined[meeting_date] for meeting_date in sorted(combined)]


def fetch_all_fomc_meetings(api_key: str | None = None) -> list[FOMCMeeting]:
    """Fetch complete FOMC meeting history plus future scheduled meetings."""
    return fetch_fomc_meetings(
        api_key=api_key,
        allow_missing_rate_history=False,
    )
