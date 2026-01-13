"""
PostgreSQL/TimescaleDB storage layer for time series data.

This package provides a modular storage layer for financial time series data,
supporting multiple asset classes and data shapes:

- OHLCV: Futures, equities, ETFs, indices, commodity futures
- Quote: FX spot, FX forwards, commodity spot
- Rate: OIS, IRS, FRA, repo, deposits, CDS
- Bond: Government yields, corporate bonds
- Fixing: SOFR, ESTR, SONIA, EURIBOR

Usage:
    from lseg_toolkit.timeseries.storage import (
        get_connection,
        save_instrument,
        save_timeseries,
        load_timeseries,
    )

    with get_connection() as conn:
        instrument_id = save_instrument(
            conn, "TYc1", "10Y Treasury Future",
            AssetClass.BOND_FUTURES, "TYc1",
            underlying="ZN", continuous_type="discrete"
        )
        save_timeseries(conn, instrument_id, df)
"""

from .connection import DEFAULT_DUCKDB_PATH, get_connection
from .field_mapping import FieldMapper, FieldMapping
from .instruments import (
    ASSET_CLASS_TO_DATA_SHAPE,
    DETAIL_TABLES,
    get_data_shape,
    get_instrument,
    get_instrument_by_ric,
    get_instrument_id,
    get_instruments,
    save_instrument,
)
from .migration import migrate_from_sqlite
from .parquet_export import export_symbol_to_parquet, export_to_parquet
from .progress import (
    create_extraction_progress,
    get_extraction_progress,
    log_extraction,
    update_extraction_progress,
)
from .queries import Queries
from .reader import get_data_coverage, get_data_range, load_timeseries
from .resolver import SymbolResolver
from .roll_events import get_roll_events, save_roll_event
from .schema import SCHEMA_SQL, init_db
from .types import (
    BondDetails,
    EquityDetails,
    ETFDetails,
    FixingDetails,
    FuturesDetails,
    FXDetails,
    IndexDetails,
    InstrumentDetails,
    RateDetails,
)
from .writer import SaveContext, save_timeseries

__all__ = [
    # Connection
    "DEFAULT_DUCKDB_PATH",
    "get_connection",
    # Schema
    "SCHEMA_SQL",
    "init_db",
    # Instruments
    "ASSET_CLASS_TO_DATA_SHAPE",
    "DETAIL_TABLES",
    "get_data_shape",
    "save_instrument",
    "get_instrument",
    "get_instrument_id",
    "get_instrument_by_ric",
    "get_instruments",
    # Writer
    "SaveContext",
    "save_timeseries",
    # Reader
    "load_timeseries",
    "get_data_range",
    "get_data_coverage",
    # Field Mapping
    "FieldMapper",
    "FieldMapping",
    # Queries
    "Queries",
    # Resolver
    "SymbolResolver",
    # Roll Events
    "save_roll_event",
    "get_roll_events",
    # Progress
    "log_extraction",
    "create_extraction_progress",
    "update_extraction_progress",
    "get_extraction_progress",
    # Parquet
    "export_to_parquet",
    "export_symbol_to_parquet",
    # Migration
    "migrate_from_sqlite",
    # Types
    "BondDetails",
    "EquityDetails",
    "ETFDetails",
    "FixingDetails",
    "FuturesDetails",
    "FXDetails",
    "IndexDetails",
    "InstrumentDetails",
    "RateDetails",
]
