"""
Continuous contract rolling logic.

Provides functions to build continuous futures contracts from
discrete contracts using various roll methods and adjustments.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from lseg_toolkit.exceptions import RollCalculationError
from lseg_toolkit.timeseries.enums import ContinuousType, RollMethod
from lseg_toolkit.timeseries.models import RollEvent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Main Entry Point
# =============================================================================


def _to_contract_label_date(value) -> date:
    """Normalize a session/timestamp value to a Python date."""
    if isinstance(value, pd.Timestamp):
        return value.date()
    if hasattr(value, "date"):
        return value.date()
    return pd.Timestamp(value).date()


def label_continuous_data(
    df: pd.DataFrame,
    get_contract: Callable[[date], str],
    date_col: str = "session_date",
) -> pd.DataFrame:
    """
    Label continuous-contract rows with the corresponding discrete contract.

    Args:
        df: Continuous-contract DataFrame.
        get_contract: Callable that maps a date to a contract code.
        date_col: Preferred column containing the labeling date. If absent,
            the DataFrame index is used.

    Returns:
        Copy of ``df`` with a ``source_contract`` column added.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    if date_col in result.columns:
        label_dates = result[date_col].map(_to_contract_label_date)
    else:
        label_dates = pd.Series(
            (_to_contract_label_date(idx) for idx in result.index),
            index=result.index,
        )

    result["source_contract"] = label_dates.map(get_contract)
    return result


def build_continuous(
    contracts_data: dict[str, pd.DataFrame],
    roll_method: RollMethod = RollMethod.VOLUME_SWITCH,
    continuous_type: ContinuousType = ContinuousType.RATIO_ADJUSTED,
    roll_days_before: int = 5,
) -> tuple[pd.DataFrame, list[RollEvent]]:
    """
    Build continuous contract from discrete contract data.

    Args:
        contracts_data: Dict mapping contract RIC to OHLCV DataFrame.
            DataFrames must have DatetimeIndex and columns:
            open, high, low, close, volume, open_interest.
        roll_method: Method for determining roll dates.
        continuous_type: Type of adjustment to apply.
        roll_days_before: Days before expiry for FIXED_DAYS method.

    Returns:
        Tuple of (continuous DataFrame, list of RollEvent objects).

    Raises:
        RollCalculationError: If roll calculation fails.
    """
    if not contracts_data:
        raise RollCalculationError("No contract data provided")

    if len(contracts_data) < 2:
        # Single contract - return as-is with no rolls
        ric = list(contracts_data.keys())[0]
        df = contracts_data[ric].copy()
        df["source_contract"] = ric
        df["adjustment_factor"] = 1.0
        return df, []

    # Detect roll dates based on method
    if roll_method == RollMethod.VOLUME_SWITCH:
        roll_dates = _detect_roll_dates_volume(contracts_data)
    elif roll_method == RollMethod.FIRST_NOTICE:
        roll_dates = _detect_roll_dates_first_notice(contracts_data)
    elif roll_method == RollMethod.FIXED_DAYS:
        roll_dates = _detect_roll_dates_fixed(contracts_data, roll_days_before)
    elif roll_method == RollMethod.EXPIRY:
        roll_dates = _detect_roll_dates_expiry(contracts_data)
    else:
        raise RollCalculationError(f"Unknown roll method: {roll_method}")

    if not roll_dates:
        logger.warning("No roll dates detected, using first contract only")
        ric = list(contracts_data.keys())[0]
        df = contracts_data[ric].copy()
        df["source_contract"] = ric
        df["adjustment_factor"] = 1.0
        return df, []

    # Build roll events
    roll_events = _build_roll_events(contracts_data, roll_dates, roll_method.value)

    # Stitch contracts together
    if continuous_type == ContinuousType.UNADJUSTED:
        continuous = _stitch_unadjusted(contracts_data, roll_events)
    elif continuous_type == ContinuousType.RATIO_ADJUSTED:
        continuous = _apply_ratio_adjustment(contracts_data, roll_events)
    elif continuous_type == ContinuousType.DIFFERENCE_ADJUSTED:
        continuous = _apply_difference_adjustment(contracts_data, roll_events)
    else:
        continuous = _stitch_unadjusted(contracts_data, roll_events)

    return continuous, roll_events


# =============================================================================
# Roll Detection Methods
# =============================================================================


def _detect_roll_dates_volume(
    contracts_data: dict[str, pd.DataFrame],
) -> list[tuple[date, str, str]]:
    """
    Detect roll dates using volume switch method.

    Roll when back month volume exceeds front month.

    Returns:
        List of (roll_date, from_contract, to_contract) tuples.
    """
    contracts = sorted(contracts_data.keys())
    if len(contracts) < 2:
        return []

    roll_dates: list[tuple[date, str, str]] = []

    # Compare consecutive contracts
    for i in range(len(contracts) - 1):
        front = contracts[i]
        back = contracts[i + 1]

        front_df = contracts_data[front]
        back_df = contracts_data[back]

        if front_df.empty or back_df.empty:
            continue

        # Get overlapping dates
        overlap_start = max(front_df.index.min(), back_df.index.min())
        overlap_end = min(front_df.index.max(), back_df.index.max())

        if overlap_start > overlap_end:
            continue

        # Find date where back volume > front volume
        front_vol = front_df.loc[overlap_start:overlap_end, "volume"]
        back_vol = back_df.loc[overlap_start:overlap_end, "volume"]

        # Align indices
        aligned = pd.DataFrame({"front": front_vol, "back": back_vol}).dropna()

        # Find first date where back > front
        cross_mask = aligned["back"] > aligned["front"]
        cross_dates = aligned[cross_mask].index

        if len(cross_dates) > 0:
            roll_date = cross_dates[0]
            if hasattr(roll_date, "date"):
                roll_date = roll_date.date()
            roll_dates.append((roll_date, front, back))
            logger.info(f"Volume switch: {front} -> {back} on {roll_date}")

    return roll_dates


def _detect_roll_dates_first_notice(
    contracts_data: dict[str, pd.DataFrame],
) -> list[tuple[date, str, str]]:
    """
    Detect roll dates using first notice date method.

    Note: This requires expiry dates which may not be in the data.
    Falls back to volume switch if expiry dates unavailable.

    Returns:
        List of (roll_date, from_contract, to_contract) tuples.
    """
    # First notice is typically 2 business days before last trading day
    # For simplicity, we'll use volume switch as fallback
    logger.warning(
        "First notice date detection requires expiry dates. "
        "Falling back to volume switch."
    )
    return _detect_roll_dates_volume(contracts_data)


def _detect_roll_dates_fixed(
    contracts_data: dict[str, pd.DataFrame],
    days_before: int = 5,
) -> list[tuple[date, str, str]]:
    """
    Detect roll dates using fixed days before expiry.

    Args:
        contracts_data: Contract data dict.
        days_before: Days before contract end to roll.

    Returns:
        List of (roll_date, from_contract, to_contract) tuples.
    """
    contracts = sorted(contracts_data.keys())
    if len(contracts) < 2:
        return []

    roll_dates: list[tuple[date, str, str]] = []

    for i in range(len(contracts) - 1):
        front = contracts[i]
        back = contracts[i + 1]

        front_df = contracts_data[front]
        if front_df.empty:
            continue

        # Roll N days before the last data point for front contract
        last_date = front_df.index.max()
        if hasattr(last_date, "date"):
            last_date = last_date.date()

        roll_date = last_date - timedelta(days=days_before)

        # Ensure roll date is in the data
        front_dates = [d.date() if hasattr(d, "date") else d for d in front_df.index]
        available_dates = [d for d in front_dates if d <= roll_date]

        if available_dates:
            roll_date = max(available_dates)
            roll_dates.append((roll_date, front, back))
            logger.info(
                f"Fixed roll ({days_before}d): {front} -> {back} on {roll_date}"
            )

    return roll_dates


def _detect_roll_dates_expiry(
    contracts_data: dict[str, pd.DataFrame],
) -> list[tuple[date, str, str]]:
    """
    Detect roll dates at contract expiry.

    Returns:
        List of (roll_date, from_contract, to_contract) tuples.
    """
    contracts = sorted(contracts_data.keys())
    if len(contracts) < 2:
        return []

    roll_dates: list[tuple[date, str, str]] = []

    for i in range(len(contracts) - 1):
        front = contracts[i]
        back = contracts[i + 1]

        front_df = contracts_data[front]
        if front_df.empty:
            continue

        # Roll on last date of front contract
        last_date = front_df.index.max()
        if hasattr(last_date, "date"):
            last_date = last_date.date()

        roll_dates.append((last_date, front, back))
        logger.info(f"Expiry roll: {front} -> {back} on {last_date}")

    return roll_dates


# =============================================================================
# Roll Event Construction
# =============================================================================


def _build_roll_events(
    contracts_data: dict[str, pd.DataFrame],
    roll_dates: list[tuple[date, str, str]],
    roll_method: str,
) -> list[RollEvent]:
    """
    Build RollEvent objects from roll dates.

    Args:
        contracts_data: Contract data dict.
        roll_dates: List of (roll_date, from_contract, to_contract).
        roll_method: Method name for logging.

    Returns:
        List of RollEvent objects.
    """
    events: list[RollEvent] = []

    for roll_date, from_contract, to_contract in roll_dates:
        from_df = contracts_data.get(from_contract)
        to_df = contracts_data.get(to_contract)

        if from_df is None or to_df is None:
            logger.warning(f"Missing data for roll {from_contract} -> {to_contract}")
            continue

        # Get prices at roll date
        from_price = _get_price_at_date(from_df, roll_date)
        to_price = _get_price_at_date(to_df, roll_date)

        if from_price is None or to_price is None:
            logger.warning(f"Missing prices at roll date {roll_date}")
            continue

        event = RollEvent(
            roll_date=roll_date,
            from_contract=from_contract,
            to_contract=to_contract,
            from_price=from_price,
            to_price=to_price,
            roll_method=roll_method,
        )
        events.append(event)

    return events


def _get_price_at_date(df: pd.DataFrame, target_date: date) -> float | None:
    """Get close price at or near a target date."""
    if df.empty:
        return None

    # Convert index to dates for comparison
    df_dates = df.copy()
    dates_array = pd.to_datetime(df_dates.index).date
    df_dates["_date"] = dates_array

    # Use mask-based lookup that mypy can type-check
    mask = df_dates["_date"] == target_date
    if mask.any():
        close_val = df_dates.loc[mask, "close"].iloc[0]
        return float(close_val) if pd.notna(close_val) else None

    # Try to find nearest date within 5 days
    for delta in range(1, 6):
        for offset in [delta, -delta]:
            try_date = target_date + timedelta(days=offset)
            mask = df_dates["_date"] == try_date
            if mask.any():
                close_val = df_dates.loc[mask, "close"].iloc[0]
                return float(close_val) if pd.notna(close_val) else None

    return None


# =============================================================================
# Stitching Methods
# =============================================================================


def _stitch_unadjusted(
    contracts_data: dict[str, pd.DataFrame],
    roll_events: list[RollEvent],
) -> pd.DataFrame:
    """
    Stitch contracts without price adjustment.

    Returns DataFrame with raw prices (will have jumps at rolls).
    """
    if not roll_events:
        ric = list(contracts_data.keys())[0]
        df = contracts_data[ric].copy()
        df["source_contract"] = ric
        df["adjustment_factor"] = 1.0
        return df

    # Build segments between roll dates
    segments: list[pd.DataFrame] = []

    # First segment: from start to first roll
    first_contract = roll_events[0].from_contract
    first_roll = roll_events[0].roll_date

    if first_contract in contracts_data:
        df = contracts_data[first_contract]
        mask = pd.to_datetime(df.index).date <= first_roll
        segment = df[mask].copy()
        segment["source_contract"] = first_contract
        segment["adjustment_factor"] = 1.0
        segments.append(segment)

    # Middle segments
    for i, event in enumerate(roll_events):
        contract = event.to_contract

        # End date is next roll or end of data
        if i + 1 < len(roll_events):
            end_date = roll_events[i + 1].roll_date
        else:
            end_date = None

        if contract in contracts_data:
            df = contracts_data[contract]
            mask = pd.to_datetime(df.index).date > event.roll_date
            if end_date:
                mask = mask & (pd.to_datetime(df.index).date <= end_date)

            segment = df[mask].copy()
            segment["source_contract"] = contract
            segment["adjustment_factor"] = 1.0
            segments.append(segment)

    if not segments:
        return pd.DataFrame()

    continuous = pd.concat(segments).sort_index()
    return continuous


def _apply_ratio_adjustment(
    contracts_data: dict[str, pd.DataFrame],
    roll_events: list[RollEvent],
) -> pd.DataFrame:
    """
    Apply backward ratio adjustment to prices.

    Historical prices are multiplied by cumulative adjustment factors
    to eliminate roll gaps while preserving returns.
    """
    if not roll_events:
        ric = list(contracts_data.keys())[0]
        df = contracts_data[ric].copy()
        df["source_contract"] = ric
        df["adjustment_factor"] = 1.0
        return df

    # Calculate cumulative adjustment factors (backward from present)
    cumulative_factors: dict[date, float] = {}
    factor = 1.0

    # Work backward through roll events
    for event in reversed(roll_events):
        cumulative_factors[event.roll_date] = factor
        factor *= event.adjustment_factor

    # Build segments with adjustment
    segments: list[pd.DataFrame] = []

    # First segment with full cumulative adjustment
    first_contract = roll_events[0].from_contract
    first_roll = roll_events[0].roll_date

    if first_contract in contracts_data:
        df = contracts_data[first_contract]
        mask = pd.to_datetime(df.index).date <= first_roll
        segment = df[mask].copy()
        segment["source_contract"] = first_contract

        # Apply cumulative adjustment
        adj_factor = factor  # Full cumulative factor for earliest segment
        segment["adjustment_factor"] = adj_factor
        for col in ["open", "high", "low", "close", "settle"]:
            if col in segment.columns:
                segment[col] = segment[col] * adj_factor
        segments.append(segment)

    # Remaining segments
    current_factor = factor
    for i, event in enumerate(roll_events):
        # Reduce factor as we move forward
        current_factor /= event.adjustment_factor

        contract = event.to_contract

        if i + 1 < len(roll_events):
            end_date = roll_events[i + 1].roll_date
        else:
            end_date = None

        if contract in contracts_data:
            df = contracts_data[contract]
            mask = pd.to_datetime(df.index).date > event.roll_date
            if end_date:
                mask = mask & (pd.to_datetime(df.index).date <= end_date)

            segment = df[mask].copy()
            segment["source_contract"] = contract
            segment["adjustment_factor"] = current_factor

            for col in ["open", "high", "low", "close", "settle"]:
                if col in segment.columns:
                    segment[col] = segment[col] * current_factor
            segments.append(segment)

    if not segments:
        return pd.DataFrame()

    continuous = pd.concat(segments).sort_index()
    return continuous


def _apply_difference_adjustment(
    contracts_data: dict[str, pd.DataFrame],
    roll_events: list[RollEvent],
) -> pd.DataFrame:
    """
    Apply backward difference adjustment to prices.

    Historical prices have roll gaps added/subtracted.
    """
    if not roll_events:
        ric = list(contracts_data.keys())[0]
        df = contracts_data[ric].copy()
        df["source_contract"] = ric
        df["adjustment_factor"] = 1.0
        return df

    # Calculate cumulative difference adjustment (backward from present)
    cumulative_diff = 0.0
    adjustments: list[float] = []

    for event in reversed(roll_events):
        adjustments.insert(0, cumulative_diff)
        cumulative_diff += event.price_gap

    # Build segments with adjustment
    segments: list[pd.DataFrame] = []

    # First segment
    first_contract = roll_events[0].from_contract
    first_roll = roll_events[0].roll_date

    if first_contract in contracts_data:
        df = contracts_data[first_contract]
        mask = pd.to_datetime(df.index).date <= first_roll
        segment = df[mask].copy()
        segment["source_contract"] = first_contract
        segment["adjustment_factor"] = cumulative_diff

        for col in ["open", "high", "low", "close", "settle"]:
            if col in segment.columns:
                segment[col] = segment[col] + cumulative_diff
        segments.append(segment)

    # Remaining segments
    for i, event in enumerate(roll_events):
        contract = event.to_contract
        adj = adjustments[i] if i < len(adjustments) else 0.0

        if i + 1 < len(roll_events):
            end_date = roll_events[i + 1].roll_date
        else:
            end_date = None

        if contract in contracts_data:
            df = contracts_data[contract]
            mask = pd.to_datetime(df.index).date > event.roll_date
            if end_date:
                mask = mask & (pd.to_datetime(df.index).date <= end_date)

            segment = df[mask].copy()
            segment["source_contract"] = contract
            segment["adjustment_factor"] = adj

            for col in ["open", "high", "low", "close", "settle"]:
                if col in segment.columns:
                    segment[col] = segment[col] + adj
            segments.append(segment)

    if not segments:
        return pd.DataFrame()

    continuous = pd.concat(segments).sort_index()
    return continuous


# =============================================================================
# Roll Calendar
# =============================================================================


def get_roll_calendar(
    roll_events: list[RollEvent],
) -> pd.DataFrame:
    """
    Convert roll events to a DataFrame for analysis.

    Args:
        roll_events: List of RollEvent objects.

    Returns:
        DataFrame with roll calendar data.
    """
    if not roll_events:
        return pd.DataFrame()

    records = [event.to_dict() for event in roll_events]
    df = pd.DataFrame(records)
    df["roll_date"] = pd.to_datetime(df["roll_date"])
    df.set_index("roll_date", inplace=True)
    return df
