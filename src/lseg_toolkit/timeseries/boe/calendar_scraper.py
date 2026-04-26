"""Scraper for the Bank of England MPC meeting calendar.

The /monetary-policy/upcoming-mpc-dates page lists dates under section
headers like "2026 confirmed dates" / "2027 provisional dates". Each date
inside a section appears as "Thursday 5 February" — the year is *not*
repeated on the row, so the parser tracks the active section header.
"""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.boe.models import BoEMeeting

BOE_CALENDAR_URL = "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"

# Year section header, e.g. "2026 confirmed dates" or "2027 provisional dates".
_YEAR_HEADER_RE = re.compile(
    r"(?P<year>20\d{2})\s+(?:confirmed|provisional)\s+dates",
    re.IGNORECASE,
)

# Day-of-month + month inside a section. Year comes from the surrounding header.
_DATE_NO_YEAR_RE = re.compile(
    r"(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s*"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\b",
    re.IGNORECASE,
)

# Stand-alone "DD Month YYYY" — fallback for fixture HTML used in tests
# and for the news listings below the schedule.
_DATE_FULL_RE = re.compile(
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<year>20\d{2})",
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
    """Parse BoE MPC calendar into future-dated BoEMeeting rows.

    Walks the document linearly, switching the active year on every
    "YYYY confirmed/provisional dates" header and pairing each subsequent
    weekday-prefixed date with that year. Falls back to standalone
    "DD Month YYYY" matches at the end so fixture HTML used in tests
    (which doesn't have section headers) still parses.
    """
    if today is None:
        today = date.today()

    text = re.sub(r"<[^>]+>", " ", html)
    # BoE markup uses &nbsp; (and U+00A0) between weekday and day for some
    # rows — collapse those to plain spaces before whitespace normalization.
    text = text.replace("&nbsp;", " ").replace(" ", " ")
    text = re.sub(r"\s+", " ", text)

    seen: set[date] = set()
    meetings: list[BoEMeeting] = []

    # The live BoE page uses "YYYY confirmed/provisional dates" section
    # headers; date rows inside don't repeat the year. Fixture HTML used by
    # tests has standalone "DD Month YYYY" rows. Use whichever style fires
    # first — never both, since running the fallback against a section-style
    # page mis-attributes the trailing month of one section to the year of
    # the next header.
    headers = list(_YEAR_HEADER_RE.finditer(text))
    if headers:
        for i, header in enumerate(headers):
            year = int(header.group("year"))
            section_start = header.end()
            section_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            section = text[section_start:section_end]
            for m in _DATE_NO_YEAR_RE.finditer(section):
                try:
                    d = date(
                        year, _MONTHS[m.group("month").lower()], int(m.group("day"))
                    )
                except ValueError:
                    continue
                if d < today or d in seen:
                    continue
                seen.add(d)
                meetings.append(BoEMeeting(meeting_date=d, source="boe_calendar"))
    else:
        for m in _DATE_FULL_RE.finditer(text):
            d = date(
                int(m.group("year")),
                _MONTHS[m.group("month").lower()],
                int(m.group("day")),
            )
            if d < today or d in seen:
                continue
            seen.add(d)
            meetings.append(BoEMeeting(meeting_date=d, source="boe_calendar"))

    meetings.sort(key=lambda x: x.meeting_date)
    return meetings


def fetch_future_boe_meetings(
    *, today: date | None = None, url: str = BOE_CALENDAR_URL
) -> list[BoEMeeting]:
    return parse_future_boe_meetings(fetch_boe_calendar_html(url), today=today)
