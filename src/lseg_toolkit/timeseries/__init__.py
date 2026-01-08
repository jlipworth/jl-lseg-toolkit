"""
Time series extraction module for LSEG financial data.

This module provides functionality to extract time series data from LSEG
(bond futures, FX, OIS, etc.) with storage backends and Parquet export
for C++/Rust interoperability.

Storage:
    - `storage`: DuckDB-based modular storage (recommended)
    - `duckdb_storage`: Deprecated alias for `storage` (will be removed in v2.0.0)

Example:
    >>> from lseg_toolkit.timeseries import TimeSeriesConfig, Granularity
    >>> config = TimeSeriesConfig(
    ...     symbols=['ZN', 'ZB'],
    ...     start_date=date(2024, 1, 1),
    ...     end_date=date(2024, 12, 31),
    ...     granularity=Granularity.DAILY,
    ...     continuous=True,
    ... )

    >>> # Storage usage
    >>> from lseg_toolkit.timeseries import storage
    >>> with storage.get_connection() as conn:
    ...     df = storage.load_timeseries(conn, "ZN")
"""

# Backward compatibility alias (deprecated)
from lseg_toolkit.timeseries import duckdb_storage, storage
from lseg_toolkit.timeseries.cache import (
    CacheConfig,
    CacheError,
    DataCache,
    DateGap,
    FetchResult,
    FetchStatus,
    InstrumentNotFoundError,
    InstrumentRegistry,
    detect_gaps,
    get_registry,
)
from lseg_toolkit.timeseries.client import ClientConfig, LSEGDataClient, get_client
from lseg_toolkit.timeseries.config import TimeSeriesConfig
from lseg_toolkit.timeseries.enums import (
    AssetClass,
    ContinuousType,
    DataShape,
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
    # Storage backends
    "storage",
    "duckdb_storage",
    # Cache
    "CacheConfig",
    "CacheError",
    "DataCache",
    "DateGap",
    "FetchResult",
    "FetchStatus",
    "InstrumentNotFoundError",
    "InstrumentRegistry",
    "detect_gaps",
    "get_registry",
    # Client
    "ClientConfig",
    "LSEGDataClient",
    "get_client",
    # Config
    "TimeSeriesConfig",
    # Enums
    "AssetClass",
    "ContinuousType",
    "DataShape",
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
