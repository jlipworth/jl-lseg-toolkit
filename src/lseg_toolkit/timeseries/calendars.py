"""
Exchange calendar utilities for trading day calculations.

Provides helpers for determining trading days, LSEG continuous
contract roll dates, and LSEG/CME session dates for intraday data.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Literal

import exchange_calendars as xcals
import pandas as pd

# Supported exchange codes
ExchangeCode = Literal["CME", "NYSE", "EUREX", "ICE"]


@lru_cache(maxsize=4)
def _get_calendar(exchange: ExchangeCode) -> xcals.ExchangeCalendar:
    """Get an exchange calendar (cached)."""
    calendar_map = {
        "CME": "CME",
        "NYSE": "XNYS",
        "EUREX": "XEUR",
        "ICE": "IEPA",
    }
    cal_code = calendar_map.get(exchange, exchange)
    return xcals.get_calendar(cal_code)


def _next_trading_day(dt: date, exchange: ExchangeCode = "CME") -> date:
    """Get the next trading day on or after the given date."""
    cal = _get_calendar(exchange)
    ts = pd.Timestamp(dt)
    result = cal.date_to_session(ts, direction="next")
    return result.date()


def first_trading_day_of_month(
    year: int,
    month: int,
    exchange: ExchangeCode = "CME",
) -> date:
    """
    Get the first trading day of a given month.

    This is the key function for STIR futures roll date calculation.
    Fed Funds and other monthly LSEG continuous contracts roll on
    the 1st trading day of each month.

    Args:
        year: Year
        month: Month (1-12)
        exchange: Exchange code (default: CME)

    Returns:
        First trading day of the month

    Example:
        >>> first_trading_day_of_month(2025, 1, "CME")
        datetime.date(2025, 1, 2)  # Jan 1 is New Year's
        >>> first_trading_day_of_month(2025, 9, "CME")
        datetime.date(2025, 9, 1)  # CME has a Sep 1 session
    """
    first_of_month = date(year, month, 1)
    return _next_trading_day(first_of_month, exchange)


def get_lseg_cme_session_date(ts: pd.Timestamp | str) -> date:
    """
    Map an LSEG hourly CME timestamp to its session date.

    LSEG intraday CME bars are returned as timezone-naive UTC timestamps.
    For the observed Fed Funds (`FFc1`) hourly history, the contract/session
    cutover behaves like a 22:00 UTC day boundary. A robust way to express this
    is: session_date = (timestamp_utc + 2 hours).date().

    This helper is intentionally LSEG-specific and should be used for
    intraday contract labeling/storage, not for exact exchange matching logic.

    Args:
        ts: Timestamp-like value from LSEG intraday history.

    Returns:
        CME/LSEG session date.
    """
    timestamp = pd.Timestamp(ts)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return (timestamp + pd.Timedelta(hours=2)).date()


def get_lseg_cme_session_dates(index: pd.Index) -> pd.Series:
    """
    Vectorized CME session-date mapping for an LSEG intraday index.

    Args:
        index: Datetime-like index from LSEG intraday history.

    Returns:
        Series of Python ``date`` objects aligned to the input index.
    """
    timestamps = pd.to_datetime(index)
    if getattr(timestamps, "tz", None) is None:
        timestamps = timestamps.tz_localize("UTC")
    else:
        timestamps = timestamps.tz_convert("UTC")
    return pd.Series((timestamps + pd.Timedelta(hours=2)).date, index=index)


def get_lseg_continuous_roll_dates(
    start_year: int,
    end_year: int,
    frequency: Literal["monthly", "quarterly"] = "monthly",
    exchange: ExchangeCode = "CME",
) -> list[date]:
    """
    Get LSEG continuous contract roll dates for a range of years.

    LSEG continuous contracts (e.g., FFc1, SRAc1) switch to the new
    front contract on the first trading day of each roll period.
    This is NOT the same as actual exchange roll conventions.

    Monthly products (Fed Funds) roll every month.
    Quarterly products (SOFR, Euribor) roll in Mar, Jun, Sep, Dec.

    Args:
        start_year: First year
        end_year: Last year (inclusive)
        frequency: 'monthly' or 'quarterly'
        exchange: Exchange code (default: CME)

    Returns:
        List of roll dates in chronological order

    Example:
        >>> get_lseg_continuous_roll_dates(2024, 2024, "monthly", "CME")
        [date(2024, 1, 2), date(2024, 2, 1), ...]  # 12 dates
    """
    if frequency == "quarterly":
        months = [3, 6, 9, 12]
    else:
        months = list(range(1, 13))

    roll_dates = []
    for year in range(start_year, end_year + 1):
        for month in months:
            roll_date = first_trading_day_of_month(year, month, exchange)
            roll_dates.append(roll_date)

    return roll_dates
