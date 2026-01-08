# RUNBOOK: DuckDB Storage Refactor

**Status**: EPHEMERAL (delete after completion)
**Goal**: Reduce `duckdb_storage.py` from 2,740 lines to ~1,200 lines across focused modules
**Estimated LOC Reduction**: ~1,000 lines (-37%)

---

## Current State

```
src/lseg_toolkit/timeseries/duckdb_storage.py (2,740 lines, 42 functions)
├── Schema SQL (410 lines)
├── Connection management (50 lines)
├── Instrument CRUD (200 lines)
├── 5x _save_*_data functions (500 lines) ← MAJOR DUPLICATION
├── 5x _load_*_data functions (300 lines)
├── 7x _save_*_details functions (350 lines) ← MAJOR DUPLICATION
├── Roll event functions (150 lines)
├── Extraction progress tracking (100 lines)
└── Parquet export (200 lines)
```

---

## Target State

```
src/lseg_toolkit/timeseries/
├── storage/
│   ├── __init__.py          # Re-exports public API
│   ├── schema.py            # Schema SQL + init_db (~450 lines)
│   ├── connection.py        # get_connection, context manager (~50 lines)
│   ├── instruments.py       # Instrument CRUD + details (~150 lines)
│   ├── field_mapping.py     # FieldMapper + mappings (~120 lines) ← NEW
│   ├── writer.py            # All save functions (~200 lines)
│   ├── reader.py            # All load functions (~200 lines)
│   ├── roll_events.py       # Roll tracking (~100 lines)
│   └── parquet_export.py    # Export functions (~150 lines)
├── cache.py                 # Keep as-is (already good)
├── client.py                # Keep as-is
├── constants.py             # Keep as-is
└── enums.py                 # Keep as-is
```

**Total**: ~1,420 lines (down from 2,740)

---

## Phase 1: Extract FieldMapper (Priority 1.1)

**Goal**: Centralize LSEG field name → normalized column mapping

### Step 1.1.1: Create field_mapping.py

```python
# src/lseg_toolkit/timeseries/storage/field_mapping.py
"""
Field mapping from LSEG API field names to normalized storage columns.

This module provides the FieldMapper class which handles the translation
between LSEG's field names (TRDPRC_1, ACVOL_UNS, etc.) and our normalized
column names (close, volume, etc.) with fallback chains.
"""

from dataclasses import dataclass
from typing import Any, Callable
import pandas as pd


@dataclass
class FieldMapping:
    """Single field mapping with fallback chain."""

    target: str                           # Our column name
    sources: list[str]                    # LSEG field names (priority order)
    required: bool = False                # Raise if not found?
    transform: Callable[[Any], Any] | None = None  # Optional transform

    def extract(self, row: pd.Series) -> Any:
        """Extract value from row using fallback chain."""
        for source in self.sources:
            value = row.get(source)
            if value is not None and not pd.isna(value):
                return self.transform(value) if self.transform else value

        if self.required:
            raise ValueError(f"Required field '{self.target}' not found")
        return None


class FieldMapper:
    """Registry of field mappings by data shape."""

    OHLCV = [
        FieldMapping("open", ["open", "OPEN_PRC"]),
        FieldMapping("high", ["high", "HIGH_1"]),
        FieldMapping("low", ["low", "LOW_1"]),
        FieldMapping("close", ["close", "settle", "TRDPRC_1"], required=True),
        FieldMapping("volume", ["volume", "ACVOL_UNS"]),
        FieldMapping("settle", ["settle", "SETTLE"]),
        FieldMapping("open_interest", ["open_interest", "OPINT_1"]),
        FieldMapping("vwap", ["vwap", "VWAP"]),
    ]

    QUOTE = [
        FieldMapping("bid", ["bid", "BID"]),
        FieldMapping("ask", ["ask", "ASK"]),
        FieldMapping("mid", ["mid", "MID_PRICE"]),
        FieldMapping("open_bid", ["open_bid", "OPEN_BID"]),
        FieldMapping("bid_high", ["bid_high", "BID_HIGH_1"]),
        FieldMapping("bid_low", ["bid_low", "BID_LOW_1"]),
        FieldMapping("open_ask", ["open_ask", "OPEN_ASK"]),
        FieldMapping("ask_high", ["ask_high", "ASK_HIGH_1"]),
        FieldMapping("ask_low", ["ask_low", "ASK_LOW_1"]),
        FieldMapping("forward_points", ["forward_points", "FWD_POINTS"]),
    ]

    RATE = [
        FieldMapping("rate", ["rate", "MID_PRICE", "BID"]),
        FieldMapping("bid", ["bid", "BID"]),
        FieldMapping("ask", ["ask", "ASK"]),
        FieldMapping("open_rate", ["open_rate", "OPEN_BID"]),
        FieldMapping("high_rate", ["high_rate", "BID_HIGH_1"]),
        FieldMapping("low_rate", ["low_rate", "BID_LOW_1"]),
        FieldMapping("rate_2", ["rate_2", "GV1_RATE"]),
        FieldMapping("spread", ["spread"]),
    ]

    BOND = [
        FieldMapping("price", ["price", "MID_PRICE"]),
        FieldMapping("bid", ["bid", "BID"]),
        FieldMapping("ask", ["ask", "ASK"]),
        FieldMapping("open_price", ["open_price", "MID_OPEN"]),
        FieldMapping("yield", ["yield", "MID_YLD_1", "B_YLD_1"], required=True),
        FieldMapping("yield_bid", ["yield_bid", "B_YLD_1"]),
        FieldMapping("yield_ask", ["yield_ask", "A_YLD_1"]),
        FieldMapping("open_yield", ["open_yield", "OPEN_YLD"]),
        FieldMapping("yield_high", ["yield_high", "HIGH_YLD"]),
        FieldMapping("yield_low", ["yield_low", "LOW_YLD"]),
        FieldMapping("dirty_price", ["dirty_price"]),
        FieldMapping("accrued_interest", ["accrued_interest", "ACCR_INT"]),
        FieldMapping("mod_duration", ["mod_duration", "MOD_DURTN"]),
        FieldMapping("mac_duration", ["mac_duration", "MAC_DURTN"]),
        FieldMapping("convexity", ["convexity", "CONVEXITY"]),
        FieldMapping("dv01", ["dv01", "BPV"]),
        FieldMapping("z_spread", ["z_spread", "ZSPREAD"]),
        FieldMapping("oas", ["oas", "OAS_BID"]),
    ]

    FIXING = [
        FieldMapping("value", ["value", "FIXING_1", "PRIMACT_1"], required=True),
        FieldMapping("volume", ["volume", "ACVOL_UNS"]),
    ]

    @classmethod
    def get_mappings(cls, data_shape: str) -> list[FieldMapping]:
        """Get field mappings for a data shape."""
        return getattr(cls, data_shape.upper(), cls.OHLCV)

    @classmethod
    def extract_row(cls, row: pd.Series, data_shape: str) -> dict[str, Any]:
        """Extract all mapped fields from a row."""
        mappings = cls.get_mappings(data_shape)
        return {m.target: m.extract(row) for m in mappings}
```

### Step 1.1.2: Add tests

```python
# tests/timeseries/test_field_mapping.py

def test_ohlcv_mapping_with_lseg_names():
    """LSEG field names should map correctly."""
    row = pd.Series({
        "OPEN_PRC": 100.0,
        "HIGH_1": 105.0,
        "LOW_1": 99.0,
        "TRDPRC_1": 103.0,
        "ACVOL_UNS": 50000,
    })
    result = FieldMapper.extract_row(row, "ohlcv")
    assert result["open"] == 100.0
    assert result["close"] == 103.0
    assert result["volume"] == 50000

def test_ohlcv_mapping_with_normalized_names():
    """Already-normalized names should work too."""
    row = pd.Series({"open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0})
    result = FieldMapper.extract_row(row, "ohlcv")
    assert result["close"] == 103.0

def test_fallback_chain():
    """Fallback to settle when close missing."""
    row = pd.Series({"settle": 102.5})
    result = FieldMapper.extract_row(row, "ohlcv")
    assert result["close"] == 102.5

def test_required_field_raises():
    """Required field raises ValueError when missing."""
    row = pd.Series({"open": 100.0})  # No close/settle/TRDPRC_1
    with pytest.raises(ValueError, match="Required field 'close'"):
        FieldMapper.extract_row(row, "ohlcv")
```

---

## Phase 2: Extract Bulk Insert Helper (Priority 1.2)

**Goal**: Single function for all INSERT OR REPLACE operations

### Step 2.1: Add to storage/writer.py

```python
def _bulk_insert(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    records: list[dict],
    conflict: str = "REPLACE"
) -> int:
    """
    Bulk insert records into a table.

    Args:
        conn: Database connection
        table: Target table name
        records: List of dicts with column -> value
        conflict: 'REPLACE' or 'IGNORE'

    Returns:
        Number of rows inserted
    """
    if not records:
        return 0

    columns = list(records[0].keys())
    placeholders = ", ".join(["?" for _ in columns])
    col_list = ", ".join(columns)

    sql = f"INSERT OR {conflict} INTO {table} ({col_list}) VALUES ({placeholders})"

    for record in records:
        conn.execute(sql, [record[col] for col in columns])

    return len(records)
```

### Step 2.2: Refactor save functions

**Before** (in each _save_*_data function):
```python
for record in rows:
    conn.execute(
        """INSERT OR REPLACE INTO timeseries_ohlcv (...) VALUES (?, ?, ?, ...)""",
        [record["instrument_id"], record["ts"], ...]
    )
```

**After**:
```python
return _bulk_insert(conn, "timeseries_ohlcv", rows)
```

---

## Phase 3: Unified Instrument Details (Priority 1.3)

**Goal**: Replace 7 `_save_*_details` functions with 1 generic function

### Step 3.1: Define detail table mappings

```python
# storage/instruments.py

DETAIL_TABLES = {
    "bond_futures": ("instrument_futures", [
        "underlying", "exchange", "expiry_date", "contract_month",
        "continuous_type", "tick_size", "point_value"
    ]),
    "stir_futures": ("instrument_futures", [...]),
    "index_futures": ("instrument_futures", [...]),
    "fx_futures": ("instrument_futures", [...]),
    "commodity_futures": ("instrument_futures", [...]),

    "fx_spot": ("instrument_fx", [
        "base_currency", "quote_currency", "pip_size", "tenor"
    ]),
    "fx_forward": ("instrument_fx", [...]),

    "ois": ("instrument_rate", [
        "rate_type", "currency", "tenor", "reference_rate",
        "day_count", "payment_frequency", "business_day_conv",
        "calendar", "settlement_days", "paired_instrument_id"
    ]),
    "irs": ("instrument_rate", [...]),
    "fra": ("instrument_rate", [...]),
    "deposit": ("instrument_rate", [...]),
    "repo": ("instrument_rate", [...]),

    "govt_yield": ("instrument_bond", [
        "issuer_type", "country", "tenor", "coupon_rate",
        "coupon_frequency", "day_count", "maturity_date",
        "settlement_days", "credit_rating", "sector"
    ]),
    "corp_bond": ("instrument_bond", [...]),

    "fixing": ("instrument_fixing", [
        "rate_name", "tenor", "fixing_time", "administrator"
    ]),

    "equity": ("instrument_equity", [
        "exchange", "country", "currency", "sector", "industry",
        "isin", "cusip", "sedol", "market_cap_category"
    ]),

    "etf": ("instrument_etf", [
        "exchange", "country", "currency", "asset_class_focus",
        "geography_focus", "benchmark_index", "expense_ratio",
        "isin", "cusip", "legal_structure", "is_leveraged", "is_inverse"
    ]),

    "equity_index": ("instrument_index", [
        "index_family", "country", "calculation_method", "currency",
        "num_constituents", "base_date", "base_value"
    ]),
}
```

### Step 3.2: Generic upsert function

```python
def _upsert_instrument_details(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    asset_class: str,
    **kwargs
) -> None:
    """
    Upsert instrument details to the appropriate table.

    Replaces: _save_futures_details, _save_fx_details, _save_ois_details,
              _save_govt_yield_details, _save_rate_details, _save_bond_details,
              _save_fixing_details (7 functions → 1)
    """
    if asset_class not in DETAIL_TABLES:
        return  # No detail table for this asset class

    table, valid_fields = DETAIL_TABLES[asset_class]

    # Filter to only valid fields that have values
    details = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}

    if not details:
        return

    # Check if exists
    exists = conn.execute(
        f"SELECT 1 FROM {table} WHERE instrument_id = ?",
        [instrument_id]
    ).fetchone()

    if exists:
        # UPDATE
        set_clause = ", ".join(f"{k} = ?" for k in details)
        conn.execute(
            f"UPDATE {table} SET {set_clause} WHERE instrument_id = ?",
            list(details.values()) + [instrument_id]
        )
    else:
        # INSERT
        cols = ["instrument_id"] + list(details.keys())
        placeholders = ", ".join("?" for _ in cols)
        conn.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
            [instrument_id] + list(details.values())
        )
```

---

## Phase 4: Split duckdb_storage.py (Priority 2.2)

### Step 4.1: Create storage/ submodule

```bash
mkdir -p src/lseg_toolkit/timeseries/storage
touch src/lseg_toolkit/timeseries/storage/__init__.py
```

### Step 4.2: Extract schema.py

Move from `duckdb_storage.py`:
- `SCHEMA_SQL` constant
- `init_db()` function
- Table creation logic

### Step 4.3: Extract connection.py

Move:
- `get_connection()` function
- `DEFAULT_DUCKDB_PATH` constant

### Step 4.4: Extract instruments.py

Move:
- `save_instrument()`
- `get_instrument()`
- `get_instrument_by_ric()`
- `_upsert_instrument_details()` (new unified function)
- `DETAIL_TABLES` mapping

### Step 4.5: Extract writer.py

Move:
- `save_timeseries()`
- `_save_ohlcv_data()` (refactored)
- `_save_quote_data()` (refactored)
- `_save_rate_data()` (refactored)
- `_save_bond_data()` (refactored)
- `_save_fixing_data()` (refactored)
- `_bulk_insert()` (new)
- `_convert_index_to_timestamp()`

### Step 4.6: Extract reader.py

Move:
- `load_timeseries()`
- `_load_ohlcv_data()`
- `_load_quote_data()`
- `_load_rate_data()`
- `_load_bond_data()`
- `_load_fixing_data()`
- `get_data_range()`

### Step 4.7: Extract roll_events.py

Move:
- `save_roll_event()`
- `get_roll_events()`

### Step 4.8: Extract parquet_export.py

Move:
- `export_to_parquet()`
- `export_instrument_to_parquet()`

### Step 4.9: Update __init__.py

```python
# src/lseg_toolkit/timeseries/storage/__init__.py
"""DuckDB storage layer for time series data."""

from .connection import get_connection, DEFAULT_DUCKDB_PATH
from .schema import init_db, SCHEMA_SQL
from .instruments import (
    save_instrument,
    get_instrument,
    get_instrument_by_ric,
)
from .writer import save_timeseries
from .reader import load_timeseries, get_data_range
from .field_mapping import FieldMapper, FieldMapping
from .roll_events import save_roll_event, get_roll_events
from .parquet_export import export_to_parquet

__all__ = [
    "get_connection",
    "DEFAULT_DUCKDB_PATH",
    "init_db",
    "save_instrument",
    "get_instrument",
    "get_instrument_by_ric",
    "save_timeseries",
    "load_timeseries",
    "get_data_range",
    "FieldMapper",
    "save_roll_event",
    "get_roll_events",
    "export_to_parquet",
]
```

### Step 4.10: Backward compatibility shim

```python
# src/lseg_toolkit/timeseries/duckdb_storage.py (reduced to ~50 lines)
"""
Backward compatibility shim for duckdb_storage.

DEPRECATED: Import from lseg_toolkit.timeseries.storage instead.
This module will be removed in v2.0.0.
"""

import warnings

from .storage import (
    get_connection,
    DEFAULT_DUCKDB_PATH,
    init_db,
    save_instrument,
    get_instrument,
    get_instrument_by_ric,
    save_timeseries,
    load_timeseries,
    get_data_range,
    save_roll_event,
    get_roll_events,
    export_to_parquet,
)

warnings.warn(
    "Importing from duckdb_storage is deprecated. "
    "Use 'from lseg_toolkit.timeseries.storage import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "get_connection",
    "DEFAULT_DUCKDB_PATH",
    "init_db",
    "save_instrument",
    "get_instrument",
    "get_instrument_by_ric",
    "save_timeseries",
    "load_timeseries",
    "get_data_range",
    "save_roll_event",
    "get_roll_events",
    "export_to_parquet",
]
```

---

## Execution Checklist

### Phase 1: FieldMapper
- [ ] Create `storage/field_mapping.py`
- [ ] Add unit tests for field mapping
- [ ] Run tests, verify passing

### Phase 2: Bulk Insert
- [ ] Add `_bulk_insert()` to writer.py
- [ ] Refactor `_save_ohlcv_data()` to use it
- [ ] Refactor `_save_quote_data()` to use it
- [ ] Refactor `_save_rate_data()` to use it
- [ ] Refactor `_save_bond_data()` to use it
- [ ] Refactor `_save_fixing_data()` to use it
- [ ] Run tests, verify data integrity

### Phase 3: Unified Instrument Details
- [ ] Create `DETAIL_TABLES` mapping
- [ ] Implement `_upsert_instrument_details()`
- [ ] Remove 7 old `_save_*_details()` functions
- [ ] Update `save_instrument()` to use new function
- [ ] Run tests, verify instrument details saved correctly

### Phase 4: Split Module
- [ ] Create `storage/` directory structure
- [ ] Extract `schema.py`
- [ ] Extract `connection.py`
- [ ] Extract `instruments.py`
- [ ] Extract `writer.py`
- [ ] Extract `reader.py`
- [ ] Extract `roll_events.py`
- [ ] Extract `parquet_export.py`
- [ ] Create `storage/__init__.py` with re-exports
- [ ] Create backward compatibility shim in `duckdb_storage.py`
- [ ] Update imports in `cache.py`, `client.py`
- [ ] Run full test suite
- [ ] Run pre-commit

### Final Validation
- [ ] `uv run pytest tests/timeseries/ -v`
- [ ] `uv run pre-commit run --all-files`
- [ ] Verify LOC reduction (target: 2,740 → ~1,420)
- [ ] Delete this runbook

---

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| duckdb_storage.py lines | 2,740 | ~50 (shim only) |
| Total storage/ lines | - | ~1,420 |
| Number of functions | 42 | ~25 |
| _save_*_details functions | 7 | 1 |
| Field mapping code | ~400 lines scattered | ~120 lines centralized |

---

## Rollback Plan

If issues arise:
1. All old functions remain available via the shim
2. Git revert to pre-refactor commit
3. No data migration required (schema unchanged)
