"""
Roll detection for Fed Funds continuous contracts.

Detects roll dates by finding price discontinuities in continuous contract data
and validates them against expected roll dates (1st business day of month).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd

from lseg_toolkit.timeseries.calendars import first_trading_day_of_month

logger = logging.getLogger(__name__)


@dataclass
class RollDiscontinuity:
    """A detected roll discontinuity in continuous contract data."""

    roll_date: date
    price_before: float
    price_after: float
    price_change: float
    pct_change: float
    expected_roll_date: date | None
    days_from_expected: int | None
    is_validated: bool

    @property
    def price_gap(self) -> float:
        """Alias for price_change."""
        return self.price_change


def detect_roll_discontinuities(
    df: pd.DataFrame,
    price_col: str = "settle",
    threshold_pct: float = 0.05,
    threshold_abs: float = 0.02,
) -> list[RollDiscontinuity]:
    """
    Detect roll discontinuities in continuous contract data.

    Fed Funds continuous contracts (FFc1) show price jumps when rolling
    from one month's contract to the next. This function identifies these
    jumps by looking for price changes that exceed normal daily volatility.

    Args:
        df: DataFrame with DatetimeIndex and price column.
        price_col: Name of price column to analyze.
        threshold_pct: Minimum percentage change to flag as discontinuity.
        threshold_abs: Minimum absolute change to flag as discontinuity.
            Both thresholds must be exceeded for a discontinuity to be flagged.

    Returns:
        List of RollDiscontinuity objects for detected roll dates.

    Example:
        >>> df = client.get_history("FFc1", "2024-01-01", "2024-12-31")
        >>> discontinuities = detect_roll_discontinuities(df)
        >>> for d in discontinuities:
        ...     print(f"{d.roll_date}: {d.price_change:.4f} ({d.pct_change:.2%})")
    """
    if df.empty or price_col not in df.columns:
        return []

    # Get price series and compute changes
    prices = df[price_col].dropna()
    if len(prices) < 2:
        return []

    # Compute daily returns
    price_diff = prices.diff()
    pct_change = prices.pct_change()

    discontinuities: list[RollDiscontinuity] = []

    for i in range(1, len(prices)):
        abs_change = abs(price_diff.iloc[i])
        pct = abs(pct_change.iloc[i])

        # Check if this is a significant discontinuity
        if abs_change >= threshold_abs and pct >= threshold_pct:
            current_date = prices.index[i]
            if hasattr(current_date, "date"):
                current_date = current_date.date()

            # Find expected roll date (1st business day of this month)
            expected = _get_expected_roll_date(current_date)
            days_diff = (current_date - expected).days if expected else None

            # Validate: discontinuity should be within 3 days of expected roll
            is_validated = days_diff is not None and abs(days_diff) <= 3

            disc = RollDiscontinuity(
                roll_date=current_date,
                price_before=float(prices.iloc[i - 1]),
                price_after=float(prices.iloc[i]),
                price_change=float(price_diff.iloc[i]),
                pct_change=float(pct_change.iloc[i]),
                expected_roll_date=expected,
                days_from_expected=days_diff,
                is_validated=is_validated,
            )
            discontinuities.append(disc)

            logger.debug(
                f"Detected discontinuity on {current_date}: "
                f"{disc.price_change:+.4f} ({disc.pct_change:+.2%}), "
                f"expected roll: {expected}, validated: {is_validated}"
            )

    return discontinuities


def _get_expected_roll_date(ref_date: date) -> date:
    """
    Get the expected roll date for a given month.

    Fed Funds continuous contracts roll on the 1st CME session day of each month,
    switching from the prior month contract to the current month contract.

    Args:
        ref_date: A date in the month to find the roll date for.

    Returns:
        Expected roll date (1st CME session day of the month).
    """
    return first_trading_day_of_month(ref_date.year, ref_date.month, "CME")


def get_expected_roll_dates(
    start: date,
    end: date,
) -> list[date]:
    """
    Generate expected roll dates for Fed Funds in a date range.

    Args:
        start: Start date.
        end: End date.

    Returns:
        List of expected roll dates (1st CME session day of each month).

    Example:
        >>> get_expected_roll_dates(date(2024, 1, 1), date(2024, 3, 31))
        [datetime.date(2024, 1, 2), datetime.date(2024, 2, 1), datetime.date(2024, 3, 1)]
    """
    roll_dates: list[date] = []

    # Start from first of start month
    current = date(start.year, start.month, 1)

    while current <= end:
        roll_date = _get_expected_roll_date(current)
        if start <= roll_date <= end:
            roll_dates.append(roll_date)

        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return roll_dates


def compare_roll_dates(
    detected: list[RollDiscontinuity],
    expected: list[date],
    tolerance_days: int = 3,
) -> dict:
    """
    Compare detected roll discontinuities against expected roll dates.

    Args:
        detected: List of detected discontinuities.
        expected: List of expected roll dates.
        tolerance_days: Maximum days difference to consider a match.

    Returns:
        Dict with comparison results:
        - matched: List of (expected_date, detected_disc) tuples
        - missed: Expected dates with no detected discontinuity
        - unexpected: Detected discontinuities not near expected dates
    """
    detected_dates = {d.roll_date: d for d in detected}

    matched: list[tuple[date, RollDiscontinuity]] = []
    missed: list[date] = []
    unexpected: list[RollDiscontinuity] = []

    # Check each expected date
    matched_detected = set()
    for exp_date in expected:
        # Look for a detected discontinuity within tolerance
        found = False
        for det_date, disc in detected_dates.items():
            if abs((det_date - exp_date).days) <= tolerance_days:
                matched.append((exp_date, disc))
                matched_detected.add(det_date)
                found = True
                break

        if not found:
            missed.append(exp_date)

    # Find unexpected discontinuities
    for disc in detected:
        if disc.roll_date not in matched_detected:
            unexpected.append(disc)

    return {
        "matched": matched,
        "missed": missed,
        "unexpected": unexpected,
        "match_rate": len(matched) / len(expected) if expected else 0.0,
    }


def validate_roll_assumptions(
    df: pd.DataFrame,
    price_col: str = "settle",
) -> dict:
    """
    Validate the assumption that FF rolls on 1st business day of month.

    Args:
        df: Continuous contract data with DatetimeIndex.
        price_col: Price column name.

    Returns:
        Dict with validation results including match rate and details.

    Example:
        >>> df = client.get_history("FFc1", "2020-01-01", "2024-12-31")
        >>> results = validate_roll_assumptions(df)
        >>> print(f"Match rate: {results['match_rate']:.1%}")
    """
    if df.empty:
        return {"error": "Empty DataFrame", "match_rate": 0.0}

    # Get date range
    start = df.index.min()
    end = df.index.max()
    if hasattr(start, "date"):
        start = start.date()
    if hasattr(end, "date"):
        end = end.date()

    # Detect discontinuities
    detected = detect_roll_discontinuities(df, price_col)

    # Get expected roll dates
    expected = get_expected_roll_dates(start, end)

    # Compare
    comparison = compare_roll_dates(detected, expected)

    return {
        "start_date": start,
        "end_date": end,
        "expected_rolls": len(expected),
        "detected_discontinuities": len(detected),
        "matched": len(comparison["matched"]),
        "missed": len(comparison["missed"]),
        "unexpected": len(comparison["unexpected"]),
        "match_rate": comparison["match_rate"],
        "details": comparison,
    }
