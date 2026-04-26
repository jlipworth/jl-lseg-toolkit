"""Pydantic models for ECB Governing Council monetary-policy meetings."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class RateDecision(StrEnum):
    CUT = "cut"
    HIKE = "hike"
    HOLD = "hold"


class ECBMeeting(BaseModel):
    """ECB Governing Council monetary-policy meeting record.

    Both rate_upper and rate_lower store the Deposit Facility Rate (DFR);
    DFR is what ESTR tracks, so it is the relevant policy rate for OIS
    decomposition. MRO and marginal-lending rates are intentionally omitted.
    """

    meeting_date: date = Field(..., description="Decision/announcement date")
    meeting_start_date: date | None = None
    rate_upper: float | None = Field(None, description="Deposit Facility Rate (DFR)")
    rate_lower: float | None = Field(None, description="Deposit Facility Rate (DFR)")
    rate_change_bps: int | None = None
    decision: RateDecision | None = None
    dissent_count: int = 0
    vote_for: int | None = None
    vote_against: int | None = None
    statement_url: str | None = None
    minutes_url: str | None = None
    is_scheduled: bool = True
    has_sep: bool = False
    has_presser: bool = True
    source: str = "ecb_calendar"
