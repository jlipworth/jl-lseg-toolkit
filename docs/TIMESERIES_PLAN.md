# Data Extraction Module Implementation Plan

## Overview

Create a new `timeseries` module for extracting financial time series data (bond futures, FX, OIS) from LSEG with SQLite storage and Parquet export for C++/Rust interoperability.

**Priority Instruments:** Bond futures, FX, OIS (all three in parallel)
**Output:** SQLite (primary) + Parquet (interop)
**Granularity:** Daily minimum, explore finer intervals where available
**Database Location:** `data/timeseries.db` (will refactor later for multi-backend interface)
**Living Documentation:** This file tracks findings and LSEG quirks as we implement
**Instruments Reference:** See [INSTRUMENTS.md](INSTRUMENTS.md) for full support list and roadmap

---

## Phase 0: LSEG Data Validation (CRITICAL - DO FIRST)

Before building infrastructure, validate that LSEG provides the data we need.

### 0.1 Create Validation Script

Create `dev_scripts/validate_lseg_timeseries.py` to test:

```python
# Test these RIC patterns before committing to architecture:

# Bond Futures
"ZNc1"       # US 10Y continuous
"ZNH5"       # US 10Y discrete (Mar 2025)
"ZNH1^2"     # US 10Y expired (Mar 2021)
"FGBLc1"     # Bund continuous
"JBc1"       # JGB continuous

# FX
"EUR="       # EUR/USD spot
"EUR1M="     # EUR/USD 1M forward
"USDJPY="    # USD/JPY spot

# OIS
"USD1MOIS"   # USD SOFR 1M
"USD1YOIS"   # USD SOFR 1Y
"USD5YOIS=TREU"  # USD SOFR 5Y (different format?)
```

### 0.2 Validate for Each RIC

- Does `rd.get_history()` return data?
- What date range is available?
- What intervals work (daily, hourly, minute)?
- What fields are returned?

### 0.3 Document Findings

Record results in this file before proceeding.

---

## Phase 1: Foundation (Core Infrastructure)

### 1.1 Module Structure

Create new module at `src/lseg_toolkit/timeseries/`:

```
timeseries/
├── __init__.py              # Public API exports
├── enums.py                 # AssetClass, Granularity, ContinuousType, RollMethod
├── constants.py             # Futures specs, FX pairs, OIS tenors, RIC patterns
├── config.py                # TimeSeriesConfig dataclass
├── models/
│   ├── __init__.py
│   ├── instruments.py       # FuturesContract, FXSpot, OISRate dataclasses
│   └── timeseries.py        # OHLCV, TimeSeries, RollEvent dataclasses
├── fetch.py                 # LSEG fetch functions (module-level, not class-based)
├── storage.py               # SQLite read/write functions
├── export.py                # Parquet export functions
├── rolling.py               # Continuous contract construction
├── pipeline.py              # TimeSeriesExtractionPipeline orchestrator
└── cli.py                   # lseg-extract CLI entry point
```

**Note**: Simplified from class-based providers/storage backends to module-level functions. This library is LSEG-only; the abstraction point is the **output schema** (SQLite/Parquet) for downstream C++/Rust consumption, not the data provider.

### 1.2 Key Files to Create

| File | Purpose |
|------|---------|
| `enums.py` | `AssetClass`, `Granularity`, `ContinuousType`, `RollMethod` enums |
| `constants.py` | RIC patterns, futures specs (ZN, ZB, FGBL), FX pairs, OIS tenors |
| `models/instruments.py` | `FuturesContract`, `FXSpot`, `OISRate` dataclasses |
| `models/timeseries.py` | `OHLCV`, `TimeSeries`, `RollEvent` dataclasses |
| `fetch.py` | LSEG fetch functions: `fetch_futures()`, `fetch_fx()`, `fetch_ois()`, `get_contract_chain()` |
| `storage.py` | SQLite functions: `init_db()`, `save_timeseries()`, `load_timeseries()`, `get_instruments()` |
| `export.py` | Parquet functions: `export_to_parquet()`, `export_metadata()` |
| `rolling.py` | `build_continuous()`, `calculate_adjustment_factors()` with all 3 roll methods |

### 1.3 Existing Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `lseg-extract` CLI entry point, add `pyarrow` dependency |
| `exceptions.py` | Add `InstrumentNotFoundError`, `StorageError`, `RollCalculationError` |

---

## Phase 2: LSEG Integration

### 2.1 RIC Patterns to Implement

**Bond Futures:**
| Root | Name | RIC Pattern | Continuous |
|------|------|-------------|------------|
| ZN | 10Y T-Note | `ZN[M][Y]` (e.g., ZNH6) | `ZNc1` |
| ZB | 30Y T-Bond | `ZB[M][Y]` | `ZBc1` |
| ZF | 5Y T-Note | `ZF[M][Y]` | `ZFc1` |
| ZT | 2Y T-Note | `ZT[M][Y]` | `ZTc1` |
| FGBL | Euro-Bund | `FGBL[M][Y]` | `FGBLc1` |
| JB | JGB 10Y | `JB[M][Y]` | `JBc1` |

**FX:**
| Pair | Spot RIC | Forward RICs |
|------|----------|--------------|
| EUR/USD | `EUR=` | `EUR1M=`, `EUR3M=`, `EUR1Y=` |
| USD/JPY | `JPY=` | `JPY1M=`, etc. |
| GBP/USD | `GBP=` | `GBP1M=`, etc. |

**OIS:**
| Currency | Short Tenors | Long Tenors |
|----------|--------------|-------------|
| USD (SOFR) | `USD1MOIS`, `USD3MOIS` | `USD5YOIS=TREU` |
| EUR (ESTR) | `EUR1MOIS`, `EUR3MOIS` | Similar pattern |
| GBP (SONIA) | `GBP1MOIS=ICAP` | Different contributor |

### 2.2 LSEG API Usage

```python
# Time series extraction via rd.get_history()
df = rd.get_history(
    universe=['ZNc1', 'EUR='],
    fields=['OPEN_PRC', 'HIGH_1', 'LOW_1', 'TRDPRC_1', 'ACVOL_1'],
    start='2024-01-01',
    end='2024-12-31',
    interval='daily'  # Also: 'hourly', '15min', '5min', '1min'
)

# Contract specifications via rd.get_data()
df = rd.get_data(
    universe=['ZNc1', 'ZNc2'],
    fields=['EXPIR_DATE', 'DSPLY_NAME', 'SETTLE', 'OPINT_1']
)
```

### 2.3 Known LSEG Limitations

- Historical expiry dates not available as time series (must lookup per contract)
- Continuation RICs (`c1`) roll on last trading day (not customizable)
- OIS long tenors (>2Y) use different RIC patterns and field lists
- Max 3,000 interday or 50,000 intraday points per request

---

## Phase 3: Storage Implementation

### 3.1 SQLite Schema (Key Tables)

```sql
-- Instruments master table
CREATE TABLE instruments (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,  -- 'bond_futures', 'fx', 'ois'
    lseg_ric TEXT
);

-- Daily OHLCV
CREATE TABLE ohlcv_daily (
    instrument_id INTEGER REFERENCES instruments(id),
    date DATE NOT NULL,
    open REAL, high REAL, low REAL, close REAL NOT NULL,
    volume REAL, open_interest REAL,
    adjustment_factor REAL DEFAULT 1.0,
    source_contract TEXT,
    UNIQUE(instrument_id, date)
);
CREATE INDEX idx_ohlcv_daily ON ohlcv_daily(instrument_id, date DESC);

-- Roll events for continuous contracts
CREATE TABLE roll_events (
    continuous_id INTEGER REFERENCES instruments(id),
    roll_date DATE NOT NULL,
    from_contract TEXT, to_contract TEXT,
    price_gap REAL, adjustment_factor REAL
);
```

### 3.2 Parquet Structure

```
data/parquet/
├── daily/
│   ├── bond_futures/
│   │   ├── discrete/year=2024/ZNZ4.parquet
│   │   ├── unadjusted/ZN.parquet
│   │   └── backward_adjusted/ZN_ADJ.parquet
│   ├── fx/year=2024/EURUSD.parquet
│   └── ois/year=2024/USD_SOFR_1Y.parquet
└── metadata/
    ├── instruments.parquet
    └── roll_events.parquet
```

---

## Phase 4: Continuous Contract Logic

### 4.1 Roll Strategies

| Method | Description | Use Case |
|--------|-------------|----------|
| `VOLUME_SWITCH` | Roll when back month volume exceeds front | Default, liquid transition |
| `FIRST_NOTICE` | Roll before first notice date | Avoid delivery risk |
| `FIXED_DAYS` | Roll N days before expiry | Predictable schedule |

### 4.2 Price Adjustment Methods

| Method | Formula | Best For |
|--------|---------|----------|
| `UNADJUSTED` | Raw stitch (price jumps at roll) | Level analysis |
| `RATIO` | `hist_price * (new/old)` | Backtesting (preserves returns) |
| `DIFFERENCE` | `hist_price + (new - old)` | Spread analysis |

### 4.3 Storage Approach

- Store both unadjusted AND backward-adjusted series as separate instruments
- Track `adjustment_factor` and `source_contract` per bar
- Maintain `roll_events` table for audit trail

---

## Phase 5: CLI & Pipeline

### 5.1 CLI Interface

```bash
# Extract bond futures
lseg-extract ZN FGBL --start 2020-01-01 --end 2024-12-31 --interval daily

# Build continuous contracts
lseg-extract ZN --continuous --adjust ratio

# Extract FX
lseg-extract EURUSD USDJPY --asset-class fx

# Output options
lseg-extract ZN --db timeseries.db --parquet ./parquet/
```

### 5.2 Pipeline Flow

```
1. Resolve instruments (symbol -> RIC mapping)
2. Fetch time series via LsegDataProvider
3. For futures with --continuous:
   a. Get contract chain
   b. Fetch all discrete contracts
   c. Calculate roll dates
   d. Build unadjusted + adjusted series
4. Store to SQLite
5. Export to Parquet
6. Update metadata tables
```

---

## Implementation Runbooks

Each runbook is a self-contained checklist that can be tracked independently. Update status and add notes as you go.

---

### RUNBOOK 0: Setup & Validation
**Status**: `[ ] Not Started` / `[x] In Progress` / `[ ] Complete`
**Estimated Effort**: 1-2 hours

#### Tasks
- [ ] Create new git branch: `feature/timeseries-extraction`
- [ ] Add `data/` to `.gitignore`
- [ ] Create `dev_scripts/validate_lseg_timeseries.py` validation script

#### Validation Tests (2026-01-05)

**BOND FUTURES** (6/11 working)
| RIC | Type | Works? | Date Range | D | H | M | Notes |
|-----|------|--------|------------|---|---|---|-------|
| `TYc1` | US 10Y continuous (CME: ZN) | **YES** | 2024-01-02 to 2024-12-31 | Y | N | N | Use TY not ZN! |
| `USc1` | US 30Y continuous (CME: ZB) | **YES** | 2024-01-02 to 2024-12-31 | Y | N | N | Use US not ZB! |
| `TUc1` | US 5Y continuous (CME: ZF) | **YES** | 2024-01-02 to 2024-12-31 | Y | N | N | Use TU not ZF! |
| `FGBLc1` | Bund 10Y continuous | **YES** | 2024-01-02 to 2024-12-30 | Y | N | N | |
| `FGBMc1` | Bobl 5Y continuous | **YES** | 2024-01-02 to 2024-12-30 | Y | N | N | |
| `FGBSc1` | Schatz 2Y continuous | **YES** | 2024-01-02 to 2024-12-30 | Y | N | N | |
| `ZNc1` | US 10Y (ZN format) | NO | - | - | - | - | Record not found - use TYc1 |
| `JBc1` | JGB 10Y continuous | NO | - | - | - | - | Record not found - need JGB RIC |
| `TYH5` | US 10Y discrete Mar 2025 | NO | - | - | - | - | Future contract not available yet? |
| `TYH1^2` | US 10Y expired Mar 2021 | NO | - | - | - | - | Expired format not working |
| `FGBLH1^2` | Bund expired Mar 2021 | NO | - | - | - | - | Expired format not working |

**FX SPOT** (8/8 working)
| RIC | Works? | Date Range | Notes |
|-----|--------|------------|-------|
| `EUR=` | **YES** | 2024-01-02 to 2024-12-31 | EUR/USD |
| `GBP=` | **YES** | 2024-01-02 to 2024-12-31 | GBP/USD |
| `JPY=` | **YES** | 2024-01-02 to 2024-12-31 | USD/JPY |
| `CHF=` | **YES** | 2024-01-02 to 2024-12-31 | USD/CHF |
| `AUD=` | **YES** | 2024-01-02 to 2024-12-31 | AUD/USD |
| `CAD=` | **YES** | 2024-01-02 to 2024-12-31 | USD/CAD |
| `EURGBP=` | **YES** | 2024-01-01 to 2024-12-31 | Cross |
| `EURJPY=` | **YES** | 2024-01-01 to 2024-12-31 | Cross |

**FX FORWARDS** (6/6 working)
| RIC | Works? | Date Range | Notes |
|-----|--------|------------|-------|
| `EUR1M=` | **YES** | 2024-01-01 to 2024-12-31 | |
| `EUR3M=` | **YES** | 2024-01-01 to 2024-12-31 | |
| `EUR6M=` | **YES** | 2024-01-01 to 2024-12-31 | |
| `EUR1Y=` | **YES** | 2024-01-01 to 2024-12-31 | |
| `GBP1M=` | **YES** | 2024-01-01 to 2024-12-31 | |
| `JPY1M=` | **YES** | 2024-01-01 to 2024-12-31 | |

**OIS - USD SOFR** (23/23 working - FULL CURVE!)
| RIC | Works? | Rows | Notes |
|-----|--------|------|-------|
| `USD1MOIS=` | **YES** | 22 | |
| `USD2MOIS=` | **YES** | 22 | |
| `USD3MOIS=` | **YES** | 22 | |
| `USD4MOIS=` | **YES** | 22 | |
| `USD5MOIS=` | **YES** | 22 | |
| `USD6MOIS=` | **YES** | 22 | |
| `USD9MOIS=` | **YES** | 22 | |
| `USD1YOIS=` | **YES** | 22 | |
| `USD18MOIS=` | **YES** | 22 | |
| `USD2YOIS=` | **YES** | 22 | |
| `USD3YOIS=` | **YES** | 22 | |
| `USD4YOIS=` | **YES** | 22 | |
| `USD5YOIS=` | **YES** | 22 | |
| `USD6YOIS=` | **YES** | 22 | |
| `USD7YOIS=` | **YES** | 22 | |
| `USD8YOIS=` | **YES** | 22 | |
| `USD9YOIS=` | **YES** | 22 | |
| `USD10YOIS=` | **YES** | 22 | |
| `USD12YOIS=` | **YES** | 22 | |
| `USD15YOIS=` | **YES** | 22 | |
| `USD20YOIS=` | **YES** | 22 | |
| `USD25YOIS=` | **YES** | 22 | |
| `USD30YOIS=` | **YES** | 22 | |

**OIS - Other Currencies** (needs validation)
| RIC | Works? | Notes |
|-----|--------|-------|
| `GBP1MOIS=ICAP` | NO | **ACCESS DENIED** - permission issue |
| `EUR1MOIS=` | ❓ | Needs validation |

**GOVT BONDS** (4/9 working - US yields not accessible!)
| RIC | Works? | Notes |
|-----|--------|-------|
| `DE10YT=RR` | **YES** | German 10Y yield |
| `DE5YT=RR` | **YES** | German 5Y yield |
| `DE2YT=RR` | **YES** | German 2Y yield |
| `GB10YT=RR` | **YES** | UK 10Y Gilt |
| `US10YT=RR` | NO | **PERMISSION DENIED** |
| `US5YT=RR` | NO | **PERMISSION DENIED** |
| `US2YT=RR` | NO | **PERMISSION DENIED** |
| `US30YT=RR` | NO | **PERMISSION DENIED** |
| `JP10YT=RR` | NO | **PERMISSION DENIED** |

**INTERVAL TESTING** (Daily only works)
| Instrument | daily | hourly | 30min | 15min | 10min | 5min | 1min | Notes |
|------------|-------|--------|-------|-------|-------|------|------|-------|
| `TYc1` | 6 rows | empty | empty | "not supported" | empty | empty | empty | Futures daily only |
| `EUR=` | 7 rows | empty | empty | empty | empty | empty | empty | FX daily only |

#### Findings
```
KEY FINDINGS:
1. CME-to-LSEG SYMBOL MAPPING: ZN→TY, ZB→US, ZF→TU (same instruments, different symbology)
2. DAILY ONLY: All intraday intervals (hourly, 30min, 15min, 10min, 5min, 1min) return EMPTY
3. OIS FULL CURVE: USD SOFR 1M-30Y all working with pattern USD[tenor]OIS=
4. EXPIRED CONTRACTS: ^2 format not returning data - needs investigation
5. US TREASURY YIELDS: PERMISSION DENIED - not accessible with current app key
6. JGB FUTURES: JBc1 not found - need correct RIC for Japan

FIELDS DISCOVERED:
- Futures: TRDPRC_1, OPEN_PRC, HIGH_1, LOW_1, SETTLE, OPINT_1, ACVOL_UNS
- FX: BID, ASK, BID_HIGH_1, BID_LOW_1
- Bonds: BID, ASK, B_YLD_1
- OIS: BID, ASK (and associated fields)

WORKING COVERAGE:
- US Treasury Futures: TYc1 (10Y), USc1 (30Y), TUc1 (5Y) ✓
- European Futures: FGBLc1, FGBMc1, FGBSc1 ✓
- FX Spot: All major pairs ✓
- FX Forwards: All tenors ✓
- OIS: FULL USD SOFR curve (1M through 30Y) ✓
- Govt Bond Yields: Germany + UK only ✓
```

#### Decision Gate
- [x] Critical RICs validated (2026-01-05)
- [x] CME→LSEG mapping documented
- [x] Permission issues documented (US Treasury yields, GBP OIS)
- [x] Approval to proceed with working instruments: ________ (pending user approval)

---

### RUNBOOK 1: Core Models & Enums
**Status**: `[ ] Not Started` / `[ ] In Progress` / `[ ] Complete`
**Depends On**: Runbook 0

#### Files to Create
- [ ] `src/lseg_toolkit/timeseries/__init__.py`
- [ ] `src/lseg_toolkit/timeseries/enums.py`
  - [ ] `AssetClass` enum
  - [ ] `Granularity` enum (MINUTE, HOURLY, DAILY)
  - [ ] `ContinuousType` enum (DISCRETE, UNADJUSTED, BACKWARD_ADJUSTED)
  - [ ] `RollMethod` enum (VOLUME_SWITCH, FIRST_NOTICE, FIXED_DAYS)
- [ ] `src/lseg_toolkit/timeseries/constants.py`
  - [ ] `FUTURES_MONTH_CODES` dict
  - [ ] `TREASURY_FUTURES` specs (ZN, ZB, ZF, ZT)
  - [ ] `EUROPEAN_FUTURES` specs (FGBL, FGBS, FGBM)
  - [ ] `ASIAN_FUTURES` specs (JB)
  - [ ] `FX_PAIRS` specs
  - [ ] `OIS_TENORS` list
  - [ ] `LSEG_RIC_PATTERNS` (based on Runbook 0 findings)
- [ ] `src/lseg_toolkit/timeseries/models/__init__.py`
- [ ] `src/lseg_toolkit/timeseries/models/instruments.py`
  - [ ] `InstrumentBase` dataclass
  - [ ] `FuturesContract` dataclass
  - [ ] `FXSpot` dataclass
  - [ ] `OISRate` dataclass
- [ ] `src/lseg_toolkit/timeseries/models/timeseries.py`
  - [ ] `OHLCV` dataclass
  - [ ] `TimeSeries` dataclass
  - [ ] `RollEvent` dataclass
- [ ] `src/lseg_toolkit/timeseries/config.py`
  - [ ] `TimeSeriesConfig` dataclass

#### Validation
- [ ] All dataclasses have proper type hints
- [ ] `__post_init__` validation where needed
- [ ] Can import from `lseg_toolkit.timeseries`

---

### RUNBOOK 2: Storage Layer
**Status**: `[ ] Not Started` / `[ ] In Progress` / `[ ] Complete`
**Depends On**: Runbook 1

#### Files to Create
- [ ] `src/lseg_toolkit/timeseries/storage.py`
  - [ ] `SCHEMA_SQL` constant (embedded DDL)
  - [ ] `init_db(path: str) -> Connection`
  - [ ] `save_instrument(conn, instrument) -> int`
  - [ ] `save_timeseries(conn, instrument_id, data: DataFrame)`
  - [ ] `load_timeseries(conn, symbol, start, end) -> DataFrame`
  - [ ] `get_instruments(conn, asset_class=None) -> list`
  - [ ] `get_data_range(conn, symbol) -> tuple[date, date]`
- [ ] `src/lseg_toolkit/timeseries/export.py`
  - [ ] `OHLCV_SCHEMA` PyArrow schema
  - [ ] `INSTRUMENT_SCHEMA` PyArrow schema
  - [ ] `export_to_parquet(conn, output_dir, symbol=None)`
  - [ ] `export_metadata(conn, output_dir)`

#### Files to Modify
- [ ] `src/lseg_toolkit/exceptions.py`
  - [ ] Add `StorageError`
  - [ ] Add `InstrumentNotFoundError`
- [ ] `pyproject.toml`
  - [ ] Add `pyarrow>=14.0.0` dependency

#### SQLite Schema Tables
- [ ] `instruments` (id, symbol, name, asset_class, lseg_ric)
- [ ] `futures_contracts` (instrument_id, underlying, expiry_date, ...)
- [ ] `fx_spots` (instrument_id, pip_size, ...)
- [ ] `ois_rates` (instrument_id, tenor, reference_rate, ...)
- [ ] `ohlcv_daily` (instrument_id, date, open, high, low, close, volume, ...)
- [ ] `roll_events` (continuous_id, roll_date, from_contract, to_contract, ...)

#### Validation
- [ ] `init_db()` creates all tables
- [ ] Round-trip test: save -> load returns same data
- [ ] Parquet export readable from Python/C++/Rust

---

### RUNBOOK 3: Fetch Layer
**Status**: `[ ] Not Started` / `[ ] In Progress` / `[ ] Complete`
**Depends On**: Runbook 2

#### Files to Create
- [ ] `src/lseg_toolkit/timeseries/fetch.py`
  - [ ] `fetch_futures(symbols, start, end, interval='daily') -> DataFrame`
  - [ ] `fetch_fx(pairs, start, end, interval='daily') -> DataFrame`
  - [ ] `fetch_ois(currency, tenors, start, end) -> DataFrame`
  - [ ] `get_contract_chain(root_symbol) -> list[str]`
  - [ ] `resolve_ric(symbol, asset_class) -> str`
  - [ ] `_normalize_columns(df) -> DataFrame` (LSEG -> standard)

#### LSEG API Patterns
```python
# Time series (use rd.get_history)
df = rd.get_history(
    universe=['ZNc1'],
    fields=['OPEN_PRC', 'HIGH_1', 'LOW_1', 'TRDPRC_1', 'ACVOL_1'],
    start='2024-01-01',
    end='2024-12-31',
    interval='daily'
)

# Contract specs (use rd.get_data)
df = rd.get_data(
    universe=['ZNc1', 'ZNc2'],
    fields=['EXPIR_DATE', 'DSPLY_NAME', 'SETTLE']
)
```

#### Validation
- [ ] `fetch_futures()` returns expected columns
- [ ] `fetch_fx()` returns expected columns
- [ ] `fetch_ois()` returns expected columns
- [ ] Error handling for invalid RICs

---

### RUNBOOK 4: Rolling Logic
**Status**: `[ ] Not Started` / `[ ] In Progress` / `[ ] Complete`
**Depends On**: Runbook 3

#### Files to Create
- [ ] `src/lseg_toolkit/timeseries/rolling.py`
  - [ ] `build_continuous(root_symbol, start, end, roll_method, adjust=True) -> DataFrame`
  - [ ] `_detect_roll_dates_volume(data: dict[str, DataFrame]) -> list[date]`
  - [ ] `_detect_roll_dates_first_notice(data: dict[str, DataFrame]) -> list[date]`
  - [ ] `_detect_roll_dates_fixed(data: dict[str, DataFrame], days_before=5) -> list[date]`
  - [ ] `_apply_ratio_adjustment(data, roll_dates) -> DataFrame`
  - [ ] `_stitch_unadjusted(data, roll_dates) -> DataFrame`
  - [ ] `get_roll_calendar(root_symbol, start, end) -> DataFrame`

#### Roll Methods
| Method | Logic | When to Use |
|--------|-------|-------------|
| `VOLUME_SWITCH` | Roll when back month volume > front month | Liquid markets |
| `FIRST_NOTICE` | Roll N days before first notice date | Physical delivery contracts |
| `FIXED_DAYS` | Roll N days before expiry | Simple/predictable |

#### Test Cases
- [ ] ZN with VOLUME_SWITCH produces reasonable roll dates
- [ ] ZN with FIXED_DAYS(5) rolls 5 days before each expiry
- [ ] Adjusted series has no price jumps at rolls
- [ ] Unadjusted series matches discrete contract prices

---

### RUNBOOK 5: Pipeline & CLI
**Status**: `[ ] Not Started` / `[ ] In Progress` / `[ ] Complete`
**Depends On**: Runbook 4

#### Files to Create
- [ ] `src/lseg_toolkit/timeseries/pipeline.py`
  - [ ] `TimeSeriesExtractionPipeline` class
  - [ ] `run(config) -> dict` (orchestrates fetch -> store -> export)
  - [ ] Progress reporting

- [ ] `src/lseg_toolkit/timeseries/cli.py`
  - [ ] `lseg-extract` command
  - [ ] Arguments: symbols, --start, --end, --interval, --continuous, --adjust, --db, --parquet

#### Files to Modify
- [ ] `pyproject.toml`
  - [ ] Add `lseg-extract = "lseg_toolkit.timeseries.cli:main"`

#### CLI Usage Examples
```bash
# Extract discrete bond futures
lseg-extract ZN FGBL --start 2020-01-01 --end 2024-12-31

# Build continuous with adjustment
lseg-extract ZN --continuous --adjust ratio --roll-method volume

# Extract FX
lseg-extract EURUSD USDJPY --asset-class fx

# Custom output
lseg-extract ZN --db data/custom.db --parquet ./output/
```

#### Validation
- [ ] CLI help is clear
- [ ] All flags work as expected
- [ ] Progress output is useful
- [ ] Error messages are helpful

---

### RUNBOOK 6: Testing & Documentation
**Status**: `[ ] Not Started` / `[ ] In Progress` / `[ ] Complete`
**Depends On**: Runbook 5

#### Test Files to Create
- [ ] `tests/test_timeseries_models.py` - dataclass validation
- [ ] `tests/test_timeseries_storage.py` - SQLite round-trip
- [ ] `tests/test_timeseries_rolling.py` - roll calculation
- [ ] `tests/test_timeseries_integration.py` - end-to-end (marked `@pytest.mark.integration`)

#### Documentation to Create/Update
- [ ] `docs/LSEG_API_REFERENCE.md` - Add futures/FX/OIS RIC patterns
- [ ] `docs/TIMESERIES.md` - Usage documentation
- [ ] Finalize this file (`docs/TIMESERIES_PLAN.md`) with all findings

#### Final Checklist
- [ ] All tests pass: `uv run pytest tests/`
- [ ] Pre-commit passes: `uv run pre-commit run --all-files`
- [ ] Type checking passes: `uv run mypy`
- [ ] Documentation is complete
- [ ] Ready for PR review

---

## Testing Strategy

### Unit Tests
- Model validation (instrument dataclasses)
- SQLite schema creation and CRUD
- Parquet read/write
- Roll calculation logic

### Integration Tests (require LSEG Workspace)
- Fetch daily data for ZNc1
- Fetch FX spot rates
- Build continuous contract from discrete contracts

### Manual Testing Checklist
- [ ] Extract ZN daily for 1 year
- [ ] Extract EURUSD daily for 1 year
- [ ] Extract USD OIS curve (1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y)
- [ ] Build ZN continuous (unadjusted + adjusted)
- [ ] Verify SQLite queries return expected data
- [ ] Verify Parquet files readable from C++/Rust

---

## Open Questions for Testing Phase

1. ~~**OIS Data Availability**~~: ✅ RESOLVED - Full USD SOFR curve 1M-30Y works
2. ~~**Intraday Granularity**~~: ✅ RESOLVED - All intervals work with recent dates (hourly, 30min, 10min, 5min, 1min, tick)
3. **Expired Contract RICs**: Verify `^[decade]` format works for historical contracts (e.g., `TYH1^2`) - currently returns empty
4. **Roll Date Detection**: May need to maintain external roll calendar if LSEG doesn't provide historical first notice dates

---

## Future Enhancements (Post-MVP)

1. **Bond Analytics Fields**: Research rd.get_data() fields for:
   - Modified Duration (MD)
   - Z-Spread
   - DV01 / BPV
   - Convexity
   - Yield to Maturity (YTM)
   - Option-Adjusted Spread (OAS)

2. **Corporate Credit Fields**: Research rd.get_data() fields for:
   - S&P / Moody's / Fitch ratings
   - Rating history
   - Credit spreads vs benchmarks
   - CDS spreads

3. **Additional Instruments**: See `docs/INSTRUMENTS.md` for full roadmap

---

## Dependencies to Add

```toml
# pyproject.toml
[project.dependencies]
pyarrow = ">=14.0.0"  # Parquet support

[project.scripts]
lseg-extract = "lseg_toolkit.timeseries.cli:main"
```

---

## Critical Files Reference

| Existing File | Purpose |
|---------------|---------|
| `src/lseg_toolkit/client/session.py` | Session management pattern to reuse |
| `src/lseg_toolkit/earnings/pipeline.py` | Pipeline pattern to follow |
| `src/lseg_toolkit/earnings/config.py` | Config dataclass pattern |
| `src/lseg_toolkit/exceptions.py` | Exception hierarchy to extend |
| `src/lseg_toolkit/constants.py` | Constants pattern |

---

## Architectural Decisions (Post-Review)

Decisions made after architecture review:

| Decision | Rationale |
|----------|-----------|
| **Validate LSEG first** | Test RIC patterns before building infrastructure to avoid rework |
| **Module-level functions** | Library is LSEG-only; matches existing codebase patterns |
| **No DataProvider protocol** | Abstraction point is output schema (SQLite/Parquet), not data source |
| **SQLite = storage, Parquet = export** | Different purposes, not same abstraction |
| **All 3 roll methods upfront** | User needs flexibility for different instruments |
| **data/timeseries.db default** | Simple start; refactor later for multi-backend interface |

### Key Insight
This library extracts data from LSEG only. The **interface** for downstream C++/Rust consumers is the SQLite schema and Parquet format, not a Python provider protocol.
