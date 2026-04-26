"""Scraper for the Bank of England MPC meeting calendar."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.boe.models import BoEMeeting

BOE_CALENDAR_URL = "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"

_ROW_RE = re.compile(
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<year>\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch_boe_calendar_html(url: str = BOE_CALENDAR_URL) -> str:
    response = httpx.get(
        url, timeout=30.0, follow_redirects=True, headers={"User-Agent": _BROWSER_UA}
    )
    response.raise_for_status()
    return response.text


def parse_future_boe_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[BoEMeeting]:
    if today is None:
        today = date.today()
    seen: set[date] = set()
    meetings: list[BoEMeeting] = []
    for match in _ROW_RE.finditer(html):
        d = date(
            int(match.group("year")),
            _MONTHS[match.group("month").lower()],
            int(match.group("day")),
        )
        if d < today or d in seen:
            continue
        seen.add(d)
        meetings.append(BoEMeeting(meeting_date=d, source="boe_calendar"))
    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def fetch_future_boe_meetings(
    *, today: date | None = None, url: str = BOE_CALENDAR_URL
) -> list[BoEMeeting]:
    return parse_future_boe_meetings(fetch_boe_calendar_html(url), today=today)
