"""BoE (Bank of England) MPC meeting data module."""

from lseg_toolkit.timeseries.boe.calendar_scraper import (
    BOE_CALENDAR_URL,
    fetch_future_boe_meetings,
    parse_future_boe_meetings,
)
from lseg_toolkit.timeseries.boe.fetcher import (
    fetch_bank_rate_history,
    fetch_boe_meetings,
)
from lseg_toolkit.timeseries.boe.models import BoEMeeting, RateDecision
from lseg_toolkit.timeseries.boe.storage import (
    get_boe_meetings,
    get_meeting_count,
    sync_boe_meetings,
    upsert_boe_meeting,
    upsert_boe_meetings,
)

__all__ = [
    "BOE_CALENDAR_URL",
    "BoEMeeting",
    "RateDecision",
    "fetch_bank_rate_history",
    "fetch_boe_meetings",
    "fetch_future_boe_meetings",
    "get_boe_meetings",
    "get_meeting_count",
    "parse_future_boe_meetings",
    "sync_boe_meetings",
    "upsert_boe_meeting",
    "upsert_boe_meetings",
]
