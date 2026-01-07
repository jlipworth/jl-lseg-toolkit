"""
Time series extraction module for LSEG financial data.

This module provides functionality to extract time series data from LSEG
(bond futures, FX, OIS, etc.) with storage backends (SQLite/DuckDB) and
Parquet export for C++/Rust interoperability.

Storage Backends:
    - `storage`: SQLite-based storage (original)
    - `duckdb_storage`: DuckDB-based storage (better for analytics, native Parquet)

Example:
    >>> from lseg_toolkit.timeseries import TimeSeriesConfig, Granularity
    >>> config = TimeSeriesConfig(
    ...     symbols=['ZN', 'ZB'],
    ...     start_date=date(2024, 1, 1),
    ...     end_date=date(2024, 12, 31),
    ...     granularity=Granularity.DAILY,
    ...     continuous=True,
    ... )

    >>> # DuckDB storage for analytics
    >>> from lseg_toolkit.timeseries import duckdb_storage
    >>> with duckdb_storage.get_connection() as conn:
    ...     df = duckdb_storage.load_timeseries(conn, "ZN")
"""

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
