"""Pydantic models for Bank of England MPC meetings."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class RateDecision(StrEnum):
    CUT = "cut"
    HIKE = "hike"
    HOLD = "hold"


class BoEMeeting(BaseModel):
    """Bank of England MPC monetary-policy meeting record.

    rate_upper == rate_lower == Bank Rate (single policy rate).
    """

    meeting_date: date = Field(..., description="MPC announcement date")
    meeting_start_date: date | None = None
    rate_upper: float | None = Field(None, description="Bank Rate")
    rate_lower: float | None = Field(None, description="Bank Rate")
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
    source: str = "boe_calendar"
