"""
Pydantic models for FOMC data.
"""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class RateDecision(str, Enum):
    """FOMC rate decision type."""

    CUT = "cut"
    HIKE = "hike"
    HOLD = "hold"


class FOMCMeeting(BaseModel):
    """FOMC meeting record."""

    meeting_date: date = Field(..., description="Announcement date (day 2 of meeting)")
    meeting_start_date: date | None = Field(
        None, description="First day of 2-day meeting"
    )
    rate_upper: float | None = Field(
        None, description="FFR target upper bound after decision"
    )
    rate_lower: float | None = Field(
        None, description="FFR target lower bound after decision"
    )
    rate_change_bps: int | None = Field(
        None, description="Change in bps: +25, -50, 0, etc."
    )
    decision: RateDecision | None = Field(None, description="cut, hike, or hold")
    dissent_count: int = Field(0, description="Number of dissenting votes")
    vote_for: int | None = Field(None, description="Votes for decision")
    vote_against: int | None = Field(None, description="Votes against decision")
    statement_url: str | None = Field(None, description="Link to official statement")
    minutes_url: str | None = Field(None, description="Link to meeting minutes")
    is_scheduled: bool = Field(True, description="FALSE for emergency meetings")
    has_sep: bool = Field(False, description="TRUE if SEP/dot plot released")
    has_presser: bool = Field(False, description="TRUE if press conference")
    source: str = Field(
        "fedtools",
        description="Data source: fedtools, fed_calendar, fred, manual",
    )
