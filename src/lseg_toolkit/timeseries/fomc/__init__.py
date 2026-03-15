"""
FOMC (Federal Open Market Committee) data module.

Provides tools for fetching and storing FOMC meeting data.
"""

from lseg_toolkit.timeseries.fomc.calendar_scraper import (
    FED_FOMC_CALENDAR_URL,
    fetch_future_fomc_meetings,
    parse_future_fomc_meetings,
)
from lseg_toolkit.timeseries.fomc.fetcher import (
    fetch_all_fomc_meetings,
    fetch_fed_funds_rate_history,
    fetch_fomc_dates_from_fedtools,
    fetch_fomc_meetings,
)
from lseg_toolkit.timeseries.fomc.models import FOMCMeeting, RateDecision
from lseg_toolkit.timeseries.fomc.storage import (
    get_fomc_meeting_by_date,
    get_fomc_meetings,
    get_meeting_count,
    get_meeting_date_range,
    get_next_fomc_meeting,
    sync_fomc_meetings,
    upsert_fomc_meeting,
    upsert_fomc_meetings,
)

__all__ = [
    "FED_FOMC_CALENDAR_URL",
    "FOMCMeeting",
    "RateDecision",
    "fetch_all_fomc_meetings",
    "fetch_fed_funds_rate_history",
    "fetch_fomc_dates_from_fedtools",
    "fetch_fomc_meetings",
    "fetch_future_fomc_meetings",
    "get_fomc_meeting_by_date",
    "get_fomc_meetings",
    "get_meeting_count",
    "get_meeting_date_range",
    "get_next_fomc_meeting",
    "parse_future_fomc_meetings",
    "sync_fomc_meetings",
    "upsert_fomc_meeting",
    "upsert_fomc_meetings",
]
