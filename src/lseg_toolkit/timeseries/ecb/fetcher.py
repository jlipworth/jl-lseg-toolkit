"""ECB meeting/rate fetcher - combines calendar dates and FRED ECBDFR."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime

import httpx

from lseg_toolkit.timeseries.ecb.calendar_scraper import fetch_future_ecb_meetings
from lseg_toolkit.timeseries.ecb.models import ECBMeeting, RateDecision

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_DFR_SERIES = "ECBDFR"

logger = logging.getLogger(__name__)


def get_fred_api_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise ValueError(
            "FRED_API_KEY environment variable not set. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return key


def fetch_dfr_history(
    api_key: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[date, float]:
    """Fetch Deposit Facility Rate history from FRED (series ECBDFR)."""
    if api_key is None:
        api_key = get_fred_api_key()

    params: dict = {
        "series_id": FRED_DFR_SERIES,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "asc",
    }
    if start_date:
        params["observation_start"] = start_date.isoformat()
    if end_date:
        params["observation_end"] = end_date.isoformat()

    resp = httpx.get(
        f"{FRED_BASE_URL}/series/observations", params=params, timeout=30.0
    )
    resp.raise_for_status()
    data = resp.json()

    return {
        datetime.strptime(obs["date"], "%Y-%m-%d").date(): float(obs["value"])
        for obs in data.get("observations", [])
        if obs.get("value") and obs["value"] != "."
    }


def _rate_on_or_after(rate_history: dict[date, float], target: date) -> float | None:
    """Return the first rate on or after target (inclusive)."""
    candidates = sorted(d for d in rate_history if d >= target)
    return rate_history[candidates[0]] if candidates else None


def build_ecb_meetings_from_dates(
    dates: list[date],
    rate_history: dict[date, float] | None = None,
) -> list[ECBMeeting]:
    """Build ECBMeeting records from announcement dates + DFR history."""
    meetings: list[ECBMeeting] = []
    prev_rate: float | None = None

    for meeting_date in sorted(dates):
        rate: float | None = None
        if rate_history:
            rate = _rate_on_or_after(rate_history, meeting_date)

        change_bps: int | None = None
        decision: RateDecision | None = None
        if rate is not None and prev_rate is not None:
            diff = rate - prev_rate
            change_bps = int(round(diff * 100))
            if change_bps > 0:
                decision = RateDecision.HIKE
            elif change_bps < 0:
                decision = RateDecision.CUT
            else:
                decision = RateDecision.HOLD

        meetings.append(
            ECBMeeting(
                meeting_date=meeting_date,
                rate_upper=rate,
                rate_lower=rate,
                rate_change_bps=change_bps,
                decision=decision,
                source="fred+ecb_calendar",
            )
        )
        if rate is not None:
            prev_rate = rate

    return meetings


def fetch_ecb_meetings(
    api_key: str | None = None,
    allow_missing_rate_history: bool = True,
) -> list[ECBMeeting]:
    """Fetch ECB monetary-policy meetings: future from calendar, history from DFR."""
    rate_history: dict[date, float] | None = None
    try:
        rate_history = fetch_dfr_history(api_key)
    except ValueError:
        if not allow_missing_rate_history:
            raise
        logger.warning(
            "FRED API key unavailable; syncing ECB meetings without rate history"
        )

    historical_dates: list[date] = (
        sorted(rate_history.keys()) if rate_history else []
    )
    change_dates: list[date] = []
    if rate_history:
        prev: float | None = None
        for d in historical_dates:
            if prev is None or rate_history[d] != prev:
                change_dates.append(d)
                prev = rate_history[d]

    historical = build_ecb_meetings_from_dates(change_dates, rate_history)

    try:
        future = fetch_future_ecb_meetings()
    except Exception:
        logger.warning(
            "Failed to fetch future scheduled ECB meetings", exc_info=True
        )
        future = []

    combined: dict[date, ECBMeeting] = {m.meeting_date: m for m in historical}
    for m in future:
        combined.setdefault(m.meeting_date, m)

    return [combined[d] for d in sorted(combined)]
