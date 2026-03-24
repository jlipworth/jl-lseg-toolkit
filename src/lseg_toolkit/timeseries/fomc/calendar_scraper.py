"""
Future FOMC meeting scraping from the Federal Reserve calendar page.
"""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.fomc.models import FOMCMeeting

FED_FOMC_CALENDAR_URL = (
    "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
)

_YEAR_BLOCK_RE = re.compile(
    r'<h4><a id="[^"]+">(\d{4}) FOMC Meetings</a></h4></div>(.*?)(?=<div class="panel panel-default"><div class="panel-heading"><h4><a id="|</body>)',
    re.S,
)
_ROW_RE = re.compile(
    r'<div class="(?:fomc-meeting--shaded )?row fomc-meeting"[^>]*>.*?<div class="[^"]*fomc-meeting__month[^"]*"><strong>([^<]+)</strong></div>.*?<div class="fomc-meeting__date[^"]*">([^<]+)</div>',
    re.S,
)

_MONTH_NUMBERS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def fetch_fomc_calendar_html(url: str = FED_FOMC_CALENDAR_URL) -> str:
    """Fetch the official Federal Reserve FOMC calendar page."""
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def _parse_month_range(month_text: str) -> tuple[int, int]:
    parts = [
        part.strip().lower() for part in month_text.replace("&nbsp;", " ").split("/")
    ]
    if not parts:
        raise ValueError(f"Could not parse month text: {month_text!r}")

    start_month = _MONTH_NUMBERS[parts[0]]
    end_month = _MONTH_NUMBERS[parts[-1]]
    return start_month, end_month


def _parse_day_range(date_text: str) -> tuple[int, int]:
    cleaned = date_text.strip().replace("*", "").replace("\u2013", "-")
    match = re.search(r"(\d{1,2})(?:\s*-\s*(\d{1,2}))?", cleaned)
    if not match:
        raise ValueError(f"Could not parse day range: {date_text!r}")

    start_day = int(match.group(1))
    end_day = int(match.group(2) or match.group(1))
    return start_day, end_day


def parse_future_fomc_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[FOMCMeeting]:
    """
    Parse future scheduled FOMC meetings from the official Fed calendar page.

    The page contains recent historical years plus at least one forward-looking
    schedule section. We parse all scheduled meetings and keep only those on or
    after ``today``.
    """
    if today is None:
        today = date.today()

    meetings: list[FOMCMeeting] = []
    for year_text, block in _YEAR_BLOCK_RE.findall(html):
        year = int(year_text)
        for month_text, day_text in _ROW_RE.findall(block):
            start_month, end_month = _parse_month_range(month_text)
            start_day, end_day = _parse_day_range(day_text)

            meeting = FOMCMeeting(
                meeting_date=date(year, end_month, end_day),
                meeting_start_date=date(year, start_month, start_day),
                has_sep=end_month in (3, 6, 9, 12),
                has_presser=True,
                is_scheduled=True,
                source="fed_calendar",
            )
            if meeting.meeting_date >= today:
                meetings.append(meeting)

    meetings.sort(key=lambda meeting: meeting.meeting_date)
    return meetings


def fetch_future_fomc_meetings(
    *,
    today: date | None = None,
    url: str = FED_FOMC_CALENDAR_URL,
) -> list[FOMCMeeting]:
    """Fetch and parse future scheduled FOMC meetings from the Fed website."""
    html = fetch_fomc_calendar_html(url)
    return parse_future_fomc_meetings(html, today=today)
