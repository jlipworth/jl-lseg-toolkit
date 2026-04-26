"""Scraper for ECB Governing Council monetary-policy meeting calendar."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.ecb.models import ECBMeeting

ECB_CALENDAR_URL = (
    "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"
)

_ROW_RE = re.compile(
    r"(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s*,?\s*"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<year>\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def fetch_ecb_calendar_html(url: str = ECB_CALENDAR_URL) -> str:
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def parse_future_ecb_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[ECBMeeting]:
    """Parse the ECB monetary-policy calendar page into ECBMeeting objects."""
    if today is None:
        today = date.today()

    meetings: list[ECBMeeting] = []
    seen: set[date] = set()
    for match in _ROW_RE.finditer(html):
        d = date(
            int(match.group("year")),
            _MONTHS[match.group("month").lower()],
            int(match.group("day")),
        )
        if d < today or d in seen:
            continue
        seen.add(d)
        meetings.append(
            ECBMeeting(
                meeting_date=d,
                source="ecb_calendar",
            )
        )
    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def fetch_future_ecb_meetings(
    *,
    today: date | None = None,
    url: str = ECB_CALENDAR_URL,
) -> list[ECBMeeting]:
    return parse_future_ecb_meetings(fetch_ecb_calendar_html(url), today=today)
