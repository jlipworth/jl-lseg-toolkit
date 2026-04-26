"""BoC (Bank of Canada) FAD meeting data module."""

from lseg_toolkit.timeseries.boc.calendar_scraper import (
    BOC_CALENDAR_URL,
    fetch_future_boc_meetings,
    parse_future_boc_meetings,
)
from lseg_toolkit.timeseries.boc.fetcher import (
    fetch_boc_meetings,
    fetch_target_rate_history,
)
from lseg_toolkit.timeseries.boc.models import BoCMeeting, RateDecision
from lseg_toolkit.timeseries.boc.storage import (
    get_boc_meetings,
    get_meeting_count,
    sync_boc_meetings,
    upsert_boc_meeting,
    upsert_boc_meetings,
)

__all__ = [
    "BOC_CALENDAR_URL",
    "BoCMeeting",
    "RateDecision",
    "fetch_boc_meetings",
    "fetch_future_boc_meetings",
    "fetch_target_rate_history",
    "get_boc_meetings",
    "get_meeting_count",
    "parse_future_boc_meetings",
    "sync_boc_meetings",
    "upsert_boc_meeting",
    "upsert_boc_meetings",
]
