"""ECB (European Central Bank) monetary-policy meeting data module."""

from lseg_toolkit.timeseries.ecb.calendar_scraper import (
    ECB_CALENDAR_URL,
    fetch_future_ecb_meetings,
    parse_future_ecb_meetings,
)
from lseg_toolkit.timeseries.ecb.fetcher import (
    fetch_dfr_history,
    fetch_ecb_meetings,
)
from lseg_toolkit.timeseries.ecb.models import ECBMeeting, RateDecision
from lseg_toolkit.timeseries.ecb.storage import (
    get_ecb_meetings,
    get_meeting_count,
    sync_ecb_meetings,
    upsert_ecb_meeting,
    upsert_ecb_meetings,
)

__all__ = [
    "ECB_CALENDAR_URL",
    "ECBMeeting",
    "RateDecision",
    "fetch_dfr_history",
    "fetch_ecb_meetings",
    "fetch_future_ecb_meetings",
    "get_ecb_meetings",
    "get_meeting_count",
    "parse_future_ecb_meetings",
    "sync_ecb_meetings",
    "upsert_ecb_meeting",
    "upsert_ecb_meetings",
]
