# RUNBOOK: Storage Refactor - Phase 2 (Priority 2-3)

**Status**: EPHEMERAL (delete after completion)
**Depends on**: Complete RUNBOOK_STORAGE_REFACTOR.md first
**Goal**: Polish work - type safety, naming, patterns alignment

---

## Scope

This runbook covers the "nice to have" improvements AFTER the main refactor:

| Priority | Item | Impact |
|----------|------|--------|
| 2.1 | SaveContext Dataclass | Cleaner function signatures |
| 2.3 | Deprecate Legacy Tables | Consistency |
| 3.1 | TypedDict for kwargs | Type safety |
| 3.2 | Query Patterns | DRY |
| 3.3 | Cache/Storage Alignment | Consistency with client module |

---

## Priority 2.1: SaveContext Dataclass

**Problem**: Save functions have 4-6 positional parameters

**Current**:
```python
def save_timeseries(
    conn: duckdb.DuckDBPyConnection,
    instrument_id: int,
    data: pd.DataFrame,
    granularity: Granularity = Granularity.DAILY,
    source_contract: str | None = None,
    adjustment_factor: float = 1.0,
    data_shape: DataShape | None = None,
) -> int:
```

**After**:
```python
@dataclass
class SaveContext:
    """Context for saving time series data."""
    instrument_id: int
    granularity: Granularity
    data_shape: DataShape
    source_contract: str | None = None
    adjustment_factor: float = 1.0

    @classmethod
    def for_instrument(cls, conn, instrument_id: int, granularity: Granularity = Granularity.DAILY, **kwargs) -> "SaveContext":
        """Factory that looks up data_shape from database."""
        result = conn.execute("SELECT data_shape FROM instruments WHERE id = ?", [instrument_id]).fetchone()
        data_shape = DataShape(result[0]) if result else DataShape.OHLCV
        return cls(instrument_id=instrument_id, granularity=granularity, data_shape=data_shape, **kwargs)


def save_timeseries(conn, data: pd.DataFrame, context: SaveContext) -> int:
    """Save time series data."""
    ...
```

**Benefits**: Cleaner signatures, easier testing, self-documenting

---

## Priority 2.3: Deprecate Legacy Tables

**Problem**: Dual table structures cause confusion

**Legacy Tables** (to deprecate):
```
ohlcv_daily           → timeseries_ohlcv (granularity='daily')
ohlcv_intraday        → timeseries_ohlcv (granularity='1min'/'5min'/etc)
futures_contracts     → instrument_futures
fx_spots              → instrument_fx
ois_rates             → instrument_rate
govt_yields           → instrument_bond
```

### Step 1: Add deprecation warnings

```python
def save_daily_data(conn, symbol, data, ...):
    """
    DEPRECATED: Use save_timeseries() with granularity=Granularity.DAILY.
    Will be removed in v2.0.0.
    """
    warnings.warn(
        "save_daily_data() is deprecated. Use save_timeseries() instead.",
        DeprecationWarning, stacklevel=2
    )
    # ... existing implementation
```

### Step 2: Create migration utility

```python
def migrate_legacy_tables(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """
    Migrate data from legacy tables to new schema.

    Returns:
        dict with table names and rows migrated
    """
    results = {}

    # ohlcv_daily → timeseries_ohlcv
    conn.execute("""
        INSERT INTO timeseries_ohlcv (instrument_id, ts, granularity, open, high, low, close, volume, settle, open_interest, source_contract, adjustment_factor)
        SELECT instrument_id, date::TIMESTAMP, 'daily', open, high, low, close, volume, settle, open_interest, source_contract, adjustment_factor
        FROM ohlcv_daily
        ON CONFLICT (instrument_id, ts, granularity) DO NOTHING
    """)
    results["ohlcv_daily"] = conn.fetchone()[0]

    # Similar for other tables...
    return results
```

### Step 3: Update all internal usage

Search and replace:
- `save_daily_data(` → `save_timeseries(` with `granularity=Granularity.DAILY`
- `load_daily_data(` → `load_timeseries(`

### Step 4: Remove legacy tables (v2.0.0)

```sql
DROP TABLE IF EXISTS ohlcv_daily;
DROP TABLE IF EXISTS ohlcv_intraday;
DROP TABLE IF EXISTS futures_contracts;
DROP TABLE IF EXISTS fx_spots;
DROP TABLE IF EXISTS ois_rates;
DROP TABLE IF EXISTS govt_yields;
```

---

## Priority 3.1: TypedDict for kwargs

**Problem**: `**kwargs` loses type safety in `save_instrument()`

**Solution**: Create TypedDicts for each asset class detail

```python
# storage/types.py

from typing import TypedDict

class FuturesDetails(TypedDict, total=False):
    underlying: str
    exchange: str | None
    expiry_date: date | None
    contract_month: str | None
    continuous_type: str
    tick_size: float | None
    point_value: float | None

class FXDetails(TypedDict, total=False):
    base_currency: str
    quote_currency: str
    pip_size: float
    tenor: str | None

class RateDetails(TypedDict, total=False):
    rate_type: str
    currency: str
    tenor: str
    reference_rate: str | None
    day_count: str | None
    payment_frequency: str | None
    business_day_conv: str | None
    calendar: str | None
    settlement_days: int

class BondDetails(TypedDict, total=False):
    issuer_type: str
    country: str | None
    tenor: str
    coupon_rate: float | None
    coupon_frequency: str | None
    day_count: str | None
    maturity_date: date | None
    settlement_days: int
    credit_rating: str | None
    sector: str | None

class FixingDetails(TypedDict, total=False):
    rate_name: str
    tenor: str | None
    fixing_time: str | None
    administrator: str | None

class EquityDetails(TypedDict, total=False):
    exchange: str | None
    country: str
    currency: str
    sector: str | None
    industry: str | None
    isin: str | None
    cusip: str | None
    sedol: str | None
    market_cap_category: str | None

class ETFDetails(TypedDict, total=False):
    exchange: str | None
    country: str
    currency: str
    asset_class_focus: str | None
    geography_focus: str | None
    benchmark_index: str | None
    expense_ratio: float | None
    isin: str | None
    cusip: str | None
    legal_structure: str | None
    is_leveraged: bool
    is_inverse: bool

class IndexDetails(TypedDict, total=False):
    index_family: str | None
    country: str | None
    calculation_method: str | None
    currency: str
    num_constituents: int | None
    base_date: date | None
    base_value: float | None

# Union type for any instrument details
InstrumentDetails = FuturesDetails | FXDetails | RateDetails | BondDetails | FixingDetails | EquityDetails | ETFDetails | IndexDetails
```

**Usage with overloads**:
```python
from typing import Literal, overload, Unpack

@overload
def save_instrument(
    conn: duckdb.DuckDBPyConnection,
    symbol: str, name: str,
    asset_class: Literal[AssetClass.BOND_FUTURES, AssetClass.STIR_FUTURES, AssetClass.INDEX_FUTURES],
    lseg_ric: str,
    **details: Unpack[FuturesDetails]
) -> int: ...

@overload
def save_instrument(
    conn: duckdb.DuckDBPyConnection,
    symbol: str, name: str,
    asset_class: Literal[AssetClass.FX_SPOT, AssetClass.FX_FORWARD],
    lseg_ric: str,
    **details: Unpack[FXDetails]
) -> int: ...

# ... more overloads

def save_instrument(conn, symbol, name, asset_class, lseg_ric, **kwargs) -> int:
    # Implementation
    ...
```

---

## Priority 3.2: Extract Query Patterns

**Problem**: Similar SQL queries repeated across functions

**Solution**: Create query builder helpers

```python
# storage/queries.py

class Queries:
    """Common SQL query patterns."""

    @staticmethod
    def instrument_exists(symbol: str) -> tuple[str, list]:
        return "SELECT id FROM instruments WHERE symbol = ?", [symbol]

    @staticmethod
    def get_instrument_id(symbol_or_ric: str) -> tuple[str, list]:
        return """
            SELECT id FROM instruments
            WHERE symbol = ? OR lseg_ric = ?
        """, [symbol_or_ric, symbol_or_ric]

    @staticmethod
    def get_data_shape(instrument_id: int) -> tuple[str, list]:
        return "SELECT data_shape FROM instruments WHERE id = ?", [instrument_id]

    @staticmethod
    def get_date_range(table: str, instrument_id: int, granularity: str) -> tuple[str, list]:
        date_col = "date" if table == "timeseries_fixing" else "ts::DATE"
        return f"""
            SELECT MIN({date_col}), MAX({date_col})
            FROM {table}
            WHERE instrument_id = ? AND granularity = ?
        """, [instrument_id, granularity]

    @staticmethod
    def count_rows(table: str, instrument_id: int, granularity: str) -> tuple[str, list]:
        return f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE instrument_id = ? AND granularity = ?
        """, [instrument_id, granularity]


# Usage:
sql, params = Queries.instrument_exists(symbol)
result = conn.execute(sql, params).fetchone()
```

---

## Priority 3.3: Cache/Storage/Client Alignment

**Current Inconsistencies**:

| Module | Session Management | Config Pattern | Symbol Resolution |
|--------|-------------------|----------------|-------------------|
| `client/` | `SessionManager` context manager | `load_app_key()` | N/A (uses RICs directly) |
| `timeseries/client.py` | `_check_session()` only | `ClientConfig` dataclass | RICs |
| `timeseries/cache.py` | `rd.open_session()` direct | `CacheConfig` dataclass | RICs → instrument_id |
| `timeseries/storage/` | None (assumes open) | None | instrument_id |

### Solution: Introduce SymbolResolver + Use SessionManager

```python
# timeseries/storage/resolver.py

class SymbolResolver:
    """Resolves symbols/RICs to instrument IDs with caching."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self._cache: dict[str, int] = {}

    def resolve(self, symbol_or_ric: str) -> int:
        """
        Resolve symbol or RIC to instrument ID.

        Args:
            symbol_or_ric: Internal symbol or LSEG RIC

        Returns:
            Instrument ID

        Raises:
            ValueError: If symbol not found
        """
        if symbol_or_ric not in self._cache:
            sql, params = Queries.get_instrument_id(symbol_or_ric)
            result = self.conn.execute(sql, params).fetchone()

            if not result:
                raise ValueError(f"Unknown symbol/RIC: {symbol_or_ric}")

            self._cache[symbol_or_ric] = result[0]

        return self._cache[symbol_or_ric]

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()
```

### Update cache.py to use SessionManager

```python
# Before:
class DataCache:
    def __init__(self, config: CacheConfig = None):
        ...
        rd.open_session()  # Direct call

# After:
from lseg_toolkit.client import SessionManager

class DataCache:
    def __init__(self, config: CacheConfig = None, session: SessionManager = None):
        self.config = config or CacheConfig()
        self._session = session or SessionManager(auto_open=True)
        self._resolver = SymbolResolver(self._get_connection())
```

### Align Config Patterns

Consider a unified config approach:
```python
# lseg_toolkit/config.py (shared)

@dataclass
class LSEGConfig:
    """Base configuration for LSEG toolkit."""
    app_key: str | None = None

    @classmethod
    def from_file(cls) -> "LSEGConfig":
        """Load from .lseg-config.json or ~/.lseg/config.json."""
        from .client.config import load_app_key
        return cls(app_key=load_app_key())


@dataclass
class ClientConfig(LSEGConfig):
    """Client-specific config."""
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 0.1
    max_rics_per_request: int = 50


@dataclass
class CacheConfig(LSEGConfig):
    """Cache-specific config."""
    db_path: str = DEFAULT_DUCKDB_PATH
    max_concurrent_fetches: int = 5
    executor_workers: int = 4
```

---

## Execution Checklist

### Priority 2.1: SaveContext
- [ ] Create `SaveContext` dataclass
- [ ] Add `for_instrument()` factory method
- [ ] Update `save_timeseries()` signature
- [ ] Update all callers

### Priority 2.3: Legacy Tables
- [ ] Add deprecation warnings to legacy functions
- [ ] Create `migrate_legacy_tables()` utility
- [ ] Update internal usage to new functions
- [ ] Document migration in CHANGELOG

### Priority 3.1: TypedDict
- [ ] Create `storage/types.py` with TypedDicts
- [ ] Add overloaded signatures to `save_instrument()`
- [ ] Verify mypy passes

### Priority 3.2: Query Patterns
- [ ] Create `storage/queries.py`
- [ ] Replace inline SQL with Queries.* calls
- [ ] Add tests for query helpers

### Priority 3.3: Alignment
- [ ] Create `SymbolResolver` class
- [ ] Update `DataCache` to use `SessionManager`
- [ ] Consider unified `LSEGConfig` base class
- [ ] Update tests

---

## Dependencies on Main Refactor

This runbook depends on completing RUNBOOK_STORAGE_REFACTOR.md first because:

1. **SaveContext** goes into `storage/writer.py` (created in Phase 4)
2. **TypedDict** goes into `storage/types.py` (new file in storage/)
3. **Queries** goes into `storage/queries.py` (new file in storage/)
4. **SymbolResolver** goes into `storage/resolver.py` (new file in storage/)

Complete the main refactor first, then use this runbook for polish.
