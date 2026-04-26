"""Scraper for Bank of Canada Fixed Announcement Date schedule."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.boc.models import BoCMeeting

BOC_CALENDAR_URL = (
    "https://www.bankofcanada.ca/core-functions/monetary-policy/"
    "key-interest-rate/"
)

_ROW_RE = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<day>\d{1,2}),?\s+"
    r"(?P<year>\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def fetch_boc_calendar_html(url: str = BOC_CALENDAR_URL) -> str:
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def parse_future_boc_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[BoCMeeting]:
    if today is None:
        today = date.today()
    seen: set[date] = set()
    meetings: list[BoCMeeting] = []
    for match in _ROW_RE.finditer(html):
        d = date(
            int(match.group("year")),
            _MONTHS[match.group("month").lower()],
            int(match.group("day")),
        )
        if d < today or d in seen:
            continue
        seen.add(d)
        meetings.append(BoCMeeting(meeting_date=d, source="boc_calendar"))
    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def fetch_future_boc_meetings(
    *, today: date | None = None, url: str = BOC_CALENDAR_URL
) -> list[BoCMeeting]:
    return parse_future_boc_meetings(fetch_boc_calendar_html(url), today=today)
