"""
Time series extraction module for LSEG financial data.

This module provides functionality to extract time series data from LSEG
(bond futures, FX, OIS, etc.) with SQLite storage and Parquet export
for C++/Rust interoperability.

Example:
    >>> from lseg_toolkit.timeseries import TimeSeriesConfig, Granularity
    >>> config = TimeSeriesConfig(
    ...     symbols=['ZN', 'ZB'],
    ...     start_date=date(2024, 1, 1),
    ...     end_date=date(2024, 12, 31),
    ...     granularity=Granularity.DAILY,
    ...     continuous=True,
    ... )
"""

from lseg_toolkit.timeseries.config import TimeSeriesConfig
from lseg_toolkit.timeseries.enums import (
    AssetClass,
    ContinuousType,
    FuturesMonth,
    Granularity,
    RollMethod,
)
from lseg_toolkit.timeseries.models import (
    FRA,
    OHLCV,
    FuturesContract,
    FXSpot,
    GovernmentYield,
    Instrument,
    OISRate,
    RollEvent,
    TimeSeries,
)

__all__ = [
    # Config
    "TimeSeriesConfig",
    # Enums
    "AssetClass",
    "ContinuousType",
    "FuturesMonth",
    "Granularity",
    "RollMethod",
    # Models
    "FRA",
    "FuturesContract",
    "FXSpot",
    "GovernmentYield",
    "Instrument",
    "OHLCV",
    "OISRate",
    "RollEvent",
    "TimeSeries",
]
