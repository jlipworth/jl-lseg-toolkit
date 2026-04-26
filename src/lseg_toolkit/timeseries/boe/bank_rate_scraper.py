"""Scrape the Bank of England Interactive Database for the Official Bank Rate.

FRED's BOERUKM series is discontinued at 2017-01-01, so we go to BoE's own
public Interactive Database (IUDBEDR = Official Bank Rate, daily). The endpoint
returns an HTML page with a two-column table (date, rate) regardless of the
``CSVF`` query parameter, so the parser walks the table cells directly.
"""

from __future__ import annotations

import re
from datetime import date

import httpx

BOE_IADB_URL = (
    "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
)
BOE_BANK_RATE_SERIES = "IUDBEDR"

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Rows look like:
#   <td ...>23 Apr 26</td><td align="right">\n\t\t\t\t\t3.75\n\t\t\t\t</td>
_ROW_RE = re.compile(
    r"<td[^>]*>\s*(?P<day>\d{1,2})\s+"
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(?P<year>\d{2,4})\s*</td>\s*"
    r"<td[^>]*>\s*(?P<rate>-?\d+(?:\.\d+)?)\s*</td>",
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _build_iadb_params(start: date, end: date) -> dict[str, str]:
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    return {
        "Travel": "NIxAZxSUx",
        "FromSeries": "1",
        "ToSeries": "50",
        "DAT": "RNG",
        "FD": str(start.day),
        "FM": months[start.month - 1],
        "FY": str(start.year),
        "TD": str(end.day),
        "TM": months[end.month - 1],
        "TY": str(end.year),
        "FNY": "Y",
        "CSVF": "TN",
        "html.x": "66",
        "html.y": "26",
        "SeriesCodes": BOE_BANK_RATE_SERIES,
        "UsingCodes": "Y",
        "Filter": "N",
        "title": BOE_BANK_RATE_SERIES,
        "VPD": "Y",
    }


def fetch_boe_bank_rate_html(
    start_date: date | None = None,
    end_date: date | None = None,
    *,
    url: str = BOE_IADB_URL,
) -> str:
    if start_date is None:
        start_date = date(1995, 1, 1)
    if end_date is None:
        end_date = date(date.today().year + 5, 12, 31)
    response = httpx.get(
        url,
        params=_build_iadb_params(start_date, end_date),
        timeout=60.0,
        follow_redirects=True,
        headers={"User-Agent": _BROWSER_UA},
    )
    response.raise_for_status()
    return response.text


def parse_boe_bank_rate_html(html: str) -> dict[date, float]:
    """Parse BoE IADB HTML response into ``{date: rate_pct}``."""
    history: dict[date, float] = {}
    for match in _ROW_RE.finditer(html):
        year = int(match.group("year"))
        if year < 100:  # 2-digit year — BoE uses YY format
            year += 2000 if year < 70 else 1900
        d = date(year, _MONTHS[match.group("month").lower()], int(match.group("day")))
        history[d] = float(match.group("rate"))
    return history


def fetch_boe_bank_rate_history(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[date, float]:
    """Return the full Bank Rate history from BoE's Interactive Database."""
    return parse_boe_bank_rate_html(fetch_boe_bank_rate_html(start_date, end_date))


def derive_decision_dates(rate_history: dict[date, float]) -> list[date]:
    """Return the dates on which the Bank Rate changed (decision days)."""
    dates: list[date] = []
    prev: float | None = None
    for d in sorted(rate_history):
        if prev is None or rate_history[d] != prev:
            dates.append(d)
            prev = rate_history[d]
    return dates
