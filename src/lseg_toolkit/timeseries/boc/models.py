"""Pydantic models for Bank of Canada rate-decision meetings (FAD)."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class RateDecision(StrEnum):
    CUT = "cut"
    HIKE = "hike"
    HOLD = "hold"


class BoCMeeting(BaseModel):
    """Bank of Canada Fixed Announcement Date (FAD) record.

    rate_upper == rate_lower == Target Overnight Rate (single policy rate).
    """

    meeting_date: date = Field(..., description="FAD announcement date")
    meeting_start_date: date | None = None
    rate_upper: float | None = Field(None, description="Target Overnight Rate")
    rate_lower: float | None = Field(None, description="Target Overnight Rate")
    rate_change_bps: int | None = None
    decision: RateDecision | None = None
    dissent_count: int = 0
    vote_for: int | None = None
    vote_against: int | None = None
    statement_url: str | None = None
    minutes_url: str | None = None
    is_scheduled: bool = True
    has_sep: bool = False
    has_presser: bool = False
    source: str = "boc_calendar"
