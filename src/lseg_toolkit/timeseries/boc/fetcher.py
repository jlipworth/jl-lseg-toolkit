"""BoC meeting/rate fetcher - calendar dates + Valet API Target Overnight Rate."""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx

from lseg_toolkit.timeseries.boc.calendar_scraper import fetch_future_boc_meetings
from lseg_toolkit.timeseries.boc.models import BoCMeeting, RateDecision

VALET_BASE_URL = "https://www.bankofcanada.ca/valet"
# V39079 = "Target for the overnight rate" — verified against the Valet API.
BOC_TARGET_RATE_SERIES = "V39079"

logger = logging.getLogger(__name__)


def fetch_target_rate_history(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[date, float]:
    """Fetch Target Overnight Rate history from BoC Valet API.

    Valet endpoint:
        /valet/observations/{series}/json?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    Returns object with `observations` array; each entry has a `d` (date) and
    a series-keyed value object like `{"v": "4.50"}`.
    """
    params: dict = {}
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()

    resp = httpx.get(
        f"{VALET_BASE_URL}/observations/{BOC_TARGET_RATE_SERIES}/json",
        params=params,
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    history: dict[date, float] = {}
    for obs in data.get("observations", []):
        d_str = obs.get("d")
        if not d_str:
            continue
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
        value_obj = obs.get(BOC_TARGET_RATE_SERIES)
        if not isinstance(value_obj, dict):
            continue
        v_str = value_obj.get("v")
        if v_str in (None, "", "."):
            continue
        history[d] = float(v_str)
    return history


def _rate_on_or_after(rate_history: dict[date, float], target: date) -> float | None:
    candidates = sorted(d for d in rate_history if d >= target)
    return rate_history[candidates[0]] if candidates else None


def build_boc_meetings_from_dates(
    dates: list[date],
    rate_history: dict[date, float] | None = None,
) -> list[BoCMeeting]:
    meetings: list[BoCMeeting] = []
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
            BoCMeeting(
                meeting_date=meeting_date,
                rate_upper=rate,
                rate_lower=rate,
                rate_change_bps=change_bps,
                decision=decision,
                source="valet+boc_calendar",
            )
        )
        if rate is not None:
            prev_rate = rate
    return meetings


def fetch_boc_meetings(
    allow_missing_rate_history: bool = True,
) -> list[BoCMeeting]:
    rate_history: dict[date, float] | None = None
    try:
        rate_history = fetch_target_rate_history()
    except Exception:  # noqa: BLE001
        if not allow_missing_rate_history:
            raise
        logger.warning(
            "BoC Valet unavailable; syncing BoC meetings without rate history",
            exc_info=True,
        )

    change_dates: list[date] = []
    if rate_history:
        prev: float | None = None
        for d in sorted(rate_history):
            if prev is None or rate_history[d] != prev:
                change_dates.append(d)
                prev = rate_history[d]

    historical = build_boc_meetings_from_dates(change_dates, rate_history)

    try:
        future = fetch_future_boc_meetings()
    except Exception:
        logger.warning("Failed to fetch future scheduled BoC meetings", exc_info=True)
        future = []

    combined: dict[date, BoCMeeting] = {m.meeting_date: m for m in historical}
    for m in future:
        combined.setdefault(m.meeting_date, m)
    return [combined[d] for d in sorted(combined)]
