"""BoE meeting/rate fetcher.

Combines BoE-published Bank Rate history (Interactive Database series IUDBEDR,
daily) with the BoE MPC upcoming-meeting calendar.

FRED's BOERUKM series was discontinued at 2017-01-01, so we go directly to
``bankofengland.co.uk/boeapps/database`` for the rate history.
"""

from __future__ import annotations

import logging
from datetime import date

from lseg_toolkit.timeseries.boe.bank_rate_scraper import (
    derive_decision_dates,
    fetch_boe_bank_rate_history,
)
from lseg_toolkit.timeseries.boe.calendar_scraper import fetch_future_boe_meetings
from lseg_toolkit.timeseries.boe.models import BoEMeeting, RateDecision

logger = logging.getLogger(__name__)


def _rate_on_or_after(rate_history: dict[date, float], target: date) -> float | None:
    candidates = sorted(d for d in rate_history if d >= target)
    return rate_history[candidates[0]] if candidates else None


def build_boe_meetings_from_dates(
    dates: list[date],
    rate_history: dict[date, float] | None = None,
) -> list[BoEMeeting]:
    meetings: list[BoEMeeting] = []
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
            BoEMeeting(
                meeting_date=meeting_date,
                rate_upper=rate,
                rate_lower=rate,
                rate_change_bps=change_bps,
                decision=decision,
                source="boe_iadb+boe_calendar",
            )
        )
        if rate is not None:
            prev_rate = rate
    return meetings


def fetch_boe_meetings(
    api_key: str | None = None,  # noqa: ARG001 — kept for sync_boe_meetings signature compat
    allow_missing_rate_history: bool = True,
) -> list[BoEMeeting]:
    rate_history: dict[date, float] | None = None
    try:
        rate_history = fetch_boe_bank_rate_history()
    except Exception:
        if not allow_missing_rate_history:
            raise
        logger.warning(
            "BoE Interactive Database unreachable; syncing without rate history",
            exc_info=True,
        )

    change_dates: list[date] = []
    if rate_history:
        change_dates = derive_decision_dates(rate_history)

    historical = build_boe_meetings_from_dates(change_dates, rate_history)

    try:
        future = fetch_future_boe_meetings()
    except Exception:
        logger.warning("Failed to fetch future scheduled BoE meetings", exc_info=True)
        future = []

    combined: dict[date, BoEMeeting] = {m.meeting_date: m for m in historical}
    for m in future:
        combined.setdefault(m.meeting_date, m)
    return [combined[d] for d in sorted(combined)]
