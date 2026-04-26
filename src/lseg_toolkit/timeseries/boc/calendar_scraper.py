"""Scraper for Bank of Canada Fixed Announcement Date schedule."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.boc.models import BoCMeeting

# /upcoming-events lists each scheduled "Interest Rate Announcement" alongside
# unrelated items (Summary of Deliberations, Market Operations, ...). Filter
# the rows that carry the announcement label since those are the FAD decision
# dates.
BOC_CALENDAR_URL = (
    "https://www.bankofcanada.ca/press/upcoming-events/"
    "?upcoming_event_category=key-interest-rate-decision"
)

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_ROW_RE = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<day>\d{1,2}),?\s+"
    r"(?P<year>\d{4})\s*"
    # Description bounded by lookahead at next date or end-of-line so rows
    # never bleed into adjacent entries after whitespace normalization.
    r"(?P<desc>.*?)(?=\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|$)",
    re.IGNORECASE | re.DOTALL,
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


def fetch_boc_calendar_html(url: str = BOC_CALENDAR_URL) -> str:
    response = httpx.get(
        url, timeout=30.0, follow_redirects=True, headers={"User-Agent": _BROWSER_UA}
    )
    response.raise_for_status()
    return response.text


def _is_rate_announcement(desc: str) -> bool:
    """Filter rule: only 'Interest Rate Announcement' rows are decisions.

    Excludes 'Summary of Deliberations', 'Market Operations', etc.
    """
    return "interest rate announcement" in desc.lower()


def parse_future_boc_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[BoCMeeting]:
    if today is None:
        today = date.today()

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    seen: set[date] = set()
    meetings: list[BoCMeeting] = []
    for match in _ROW_RE.finditer(text):
        if not _is_rate_announcement(match.group("desc")):
            continue
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
