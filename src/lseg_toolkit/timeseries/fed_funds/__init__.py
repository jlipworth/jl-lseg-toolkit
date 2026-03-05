"""
Fed Funds futures extraction and labeling.

This module provides functions for extracting Fed Funds futures data
from LSEG and labeling continuous contract data with discrete contract codes.
"""

from lseg_toolkit.timeseries.fed_funds.extraction import (
    FF_DAILY_FIELDS,
    FF_HOURLY_FIELDS,
    fetch_fed_funds_daily,
    fetch_fed_funds_hourly,
    prepare_for_storage,
)
from lseg_toolkit.timeseries.fed_funds.roll_detection import (
    RollDiscontinuity,
    compare_roll_dates,
    detect_roll_discontinuities,
    get_expected_roll_dates,
    validate_roll_assumptions,
)

__all__ = [
    # Extraction
    "fetch_fed_funds_daily",
    "fetch_fed_funds_hourly",
    "prepare_for_storage",
    "FF_DAILY_FIELDS",
    "FF_HOURLY_FIELDS",
    # Roll detection
    "detect_roll_discontinuities",
    "get_expected_roll_dates",
    "compare_roll_dates",
    "validate_roll_assumptions",
    "RollDiscontinuity",
]
