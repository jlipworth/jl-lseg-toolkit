"""Scraper for ECB Governing Council monetary-policy meeting calendar."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.ecb.models import ECBMeeting

ECB_CALENDAR_URL = "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Live ECB calendar lists each row as "DD/MM/YYYY <description>". The rate
# decision is announced on Day 2 of the monetary-policy meeting (followed by
# press conference). Day 1 sessions, non-monetary meetings, and General Council
# meetings are filtered out.
#
# Legacy long-form regex (kept as fallback for fixture HTML used in tests):
#   "Wednesday, 11 March 2026" → (day, month-name, year)
_ROW_RE_DDMMYYYY = re.compile(
    r"(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})"
    # Description stops at the next date or end-of-line. Use a lazy match
    # with a lookahead so descriptions never bleed into the next row's text.
    r"\s*(?P<desc>.*?)(?=\s*\d{1,2}/\d{1,2}/\d{4}|$)",
)

_ROW_RE_LEGACY = re.compile(
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month_name>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
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


def fetch_ecb_calendar_html(url: str = ECB_CALENDAR_URL) -> str:
    response = httpx.get(
        url, timeout=30.0, follow_redirects=True, headers={"User-Agent": _BROWSER_UA}
    )
    response.raise_for_status()
    return response.text


def _is_rate_decision_row(desc: str) -> bool:
    """Filter rule: only Day 2 / press conference rows announce the decision."""
    desc_l = desc.lower()
    if "non-monetary" in desc_l:
        return False
    if "general council" in desc_l:
        return False
    if "monetary policy" not in desc_l:
        return False
    # Day 2 is when the rate is announced; press conference follows.
    return "day 2" in desc_l or "press conference" in desc_l


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

    # Strip HTML tags so date+description appear as adjacent text.
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    matched_any = False
    for match in _ROW_RE_DDMMYYYY.finditer(text):
        matched_any = True
        if not _is_rate_decision_row(match.group("desc")):
            continue
        d = date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )
        if d < today or d in seen:
            continue
        seen.add(d)
        meetings.append(ECBMeeting(meeting_date=d, source="ecb_calendar"))

    # Fallback for fixture HTML (tests) using the long-form date format.
    if not matched_any:
        for match in _ROW_RE_LEGACY.finditer(text):
            d = date(
                int(match.group("year")),
                _MONTHS[match.group("month_name").lower()],
                int(match.group("day")),
            )
            if d < today or d in seen:
                continue
            seen.add(d)
            meetings.append(ECBMeeting(meeting_date=d, source="ecb_calendar"))

    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def fetch_future_ecb_meetings(
    *,
    today: date | None = None,
    url: str = ECB_CALENDAR_URL,
) -> list[ECBMeeting]:
    return parse_future_ecb_meetings(fetch_ecb_calendar_html(url), today=today)
