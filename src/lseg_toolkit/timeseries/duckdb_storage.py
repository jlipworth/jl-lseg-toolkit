"""
Backward compatibility shim for duckdb_storage.

DEPRECATED: Import from lseg_toolkit.timeseries.storage instead.
This module will be removed in v2.0.0.

Example migration:
    # Old (deprecated):
    from lseg_toolkit.timeseries.duckdb_storage import save_instrument, save_timeseries

    # New (recommended):
    from lseg_toolkit.timeseries.storage import save_instrument, save_timeseries
"""

from __future__ import annotations

import warnings

# Re-export everything from the new storage module
from lseg_toolkit.timeseries.storage import (
    ASSET_CLASS_TO_DATA_SHAPE,
    DEFAULT_DUCKDB_PATH,
    DETAIL_TABLES,
    SCHEMA_SQL,
    FieldMapper,
    FieldMapping,
    create_extraction_progress,
    export_symbol_to_parquet,
    export_to_parquet,
    get_connection,
    get_data_coverage,
    get_data_range,
    get_data_shape,
    get_extraction_progress,
    get_instrument,
    get_instrument_by_ric,
    get_instrument_id,
    get_instruments,
    get_roll_events,
    init_db,
    load_timeseries,
    log_extraction,
    migrate_from_sqlite,
    save_instrument,
    save_roll_event,
    save_timeseries,
    update_extraction_progress,
)

# Emit deprecation warning on import
warnings.warn(
    "Importing from duckdb_storage is deprecated. "
    "Use 'from lseg_toolkit.timeseries.storage import ...' instead. "
    "This module will be removed in v2.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

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
    "save_timeseries",
    # Reader
    "load_timeseries",
    "get_data_range",
    "get_data_coverage",
    # Field Mapping
    "FieldMapper",
    "FieldMapping",
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
]
