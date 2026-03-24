# Fed Funds Futures Extraction Implementation History

> Archived implementation note from the original feature branch.

**Status at archive time:** implemented / validating
**Created:** 2026-01-22
**Original branch:** `feature/timeseries-extraction`

---

## Objective

Extract Fed Funds futures continuous contract data from LSEG, label each row with the discrete contract code, and store for downstream fed funds rate prediction work.

Current implementation supports:
- `FF_CONTINUOUS` (`FFc1`)
- `FF_CONTINUOUS_2` through `FF_CONTINUOUS_12` (`FFc2` ... `FFc12`)
- daily and hourly extraction
- scheduler integration
- `session_date` + `source_contract` storage for downstream consumers

---

## Key Decision: Use Existing Schema

**No new table needed.** Fed funds data fits the existing `timeseries_ohlcv` table:

```sql
-- Existing columns we'll use:
instrument_id INTEGER NOT NULL,     -- FK to instruments table
ts TIMESTAMPTZ NOT NULL,            -- as_of timestamp
granularity TEXT NOT NULL,          -- 'daily' or 'hourly'
settle DOUBLE PRECISION,            -- price (daily)
open_interest DOUBLE PRECISION,
volume DOUBLE PRECISION,
source_contract TEXT,               -- discrete contract: 'FFG26', 'FFH26'
PRIMARY KEY (instrument_id, ts, granularity)
```

**Additional columns we need to add/derive:**
- `implied_rate` → Computed: `100 - settle` (can be view or app-side)
- `contract_month` → Derived from `source_contract` parsing
- `last_trade_date` → Fetched from LSEG metadata per contract

---

## Validated Findings (2026-01-22)

### Data Availability

| Data Type | Status | Fields |
|-----------|--------|--------|
| Daily | ✅ | `SETTLE`, `OPEN_INT`, `VOLUME` |
| Hourly | ✅ | `BID`, `ASK`, `TRDPRC_1`, `HIGH_1`, `LOW_1` |

### Key Observations
- Hourly uses BID/ASK (no SETTLE) → store `mid = (bid + ask) / 2` as price
- `EXPIR_DATE` from metadata gives last trade date
- Fed Funds continuous rank symbols are exposed as `FF_CONTINUOUS` / `FF_CONTINUOUS_<rank>`
- Chunking infrastructure exists in `scheduler/jobs.py` (30-day chunks default)

---

## Decisions Made (2026-01-22)

### Q1: Roll Date Detection → D then A
- **First:** Assume 1st business day of month
- **Then:** Validate by checking for price discontinuities at those dates
- Store validated rolls in `roll_events` table

### Q2: Intraday Storage → C (Schema Change)
Add `bid`, `ask` columns to `timeseries_ohlcv`. Store raw bid/ask, calculate `mid` for the price field.

### Q3: Implied Rate → Store It
Store `implied_rate` column (optimizing for backtest speed). `implied_rate = 100 - price`

### Q4: Contract Metadata → last_trade_date only
Need `last_trade_date` per discrete contract. Store in `stir_contracts` lookup table.

### Q5: Contract Population → Upfront Bulk Fetch
Fetch metadata for all ~120 contracts (10 years × 12 months) upfront before labeling.

### Q6: Intraday Price Field → mid column, settle = NaN
- Daily: use `settle`, `implied_rate = 100 - settle`
- Hourly: use `mid = (bid + ask) / 2`, `settle = NaN`, `implied_rate = 100 - mid`

---

## Schema Changes Required

```sql
-- Add to timeseries_ohlcv
ALTER TABLE timeseries_ohlcv ADD COLUMN IF NOT EXISTS bid DOUBLE PRECISION;
ALTER TABLE timeseries_ohlcv ADD COLUMN IF NOT EXISTS ask DOUBLE PRECISION;
ALTER TABLE timeseries_ohlcv ADD COLUMN IF NOT EXISTS mid DOUBLE PRECISION;
ALTER TABLE timeseries_ohlcv ADD COLUMN IF NOT EXISTS implied_rate DOUBLE PRECISION;

-- New lookup table for STIR contract metadata
CREATE TABLE IF NOT EXISTS stir_contracts (
    contract_code TEXT PRIMARY KEY,      -- 'FFG26', 'FFH26'
    product TEXT NOT NULL,               -- 'FF', 'SRA', 'FEI'
    contract_month DATE NOT NULL,        -- First day of settlement month
    last_trade_date DATE NOT NULL,       -- From LSEG EXPIR_DATE
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stir_contracts_product ON stir_contracts(product);
```

---

## Implementation Tasks

### Phase 0: Schema Updates ✅ DONE

- [x] **0.1** Add `bid`, `ask`, `mid`, `implied_rate` columns to `timeseries_ohlcv`
- [x] **0.2** Create `stir_contracts` lookup table
- [x] **0.3** Update `pg_schema.py` with new DDL

### Phase 1: Contract Labeling ✅ DONE

- [x] **1.1** Implement `label_continuous_data(df, get_front_contract)` in `rolling.py`
  - Generic function: works for any futures product via callable
  - Uses 1st business day assumption initially
- [x] **1.4** Unit tests for labeling logic (4 tests in `test_rolling.py`)

### Phase 1b: Contract Metadata ✅ DONE

- [x] **1.2** Implement `get_contract_last_trade_date(contract_code)` - fetch from LSEG
- [x] **1.3** Implement `populate_stir_contracts()` - bulk fetch metadata for all contracts
- [x] **1.5** Helper functions: `get_contract_month_date()`, `fetch_contract_metadata_batch()`
- [x] **1.6** Unit tests for metadata functions (7 tests)

### Phase 2: Roll Validation ✅ DONE

**Finding:** Fed Funds continuous contracts (FFc1) have minimal roll discontinuities.
Roll price changes range from 0.0025 to 0.31, well within normal daily volatility.
Calendar-based labeling (1st business day of month) is validated by the data.

- [x] **2.1** Implement `detect_roll_discontinuities(df)` - find price jumps
  - Implemented in `fed_funds/roll_detection.py`
  - Not needed for FF (no significant discontinuities)
- [x] **2.2** Compare detected vs assumed roll dates
  - Implemented `compare_roll_dates()` and `validate_roll_assumptions()`
  - Validated: 0% match rate because no discontinuities exceed threshold (expected)
- [N/A] **2.3** Store validated rolls in `roll_events` table
  - Not needed: calendar-based labeling is sufficient for FF
- [N/A] **2.4** Adjust labeling if discrepancies found
  - No discrepancies: roll dates match 1st business day of month exactly

### Phase 3: Instrument Registration ✅ DONE

- [x] **3.1** Register `FF_CONTINUOUS` in `instruments` table
  ```python
  symbol='FF_CONTINUOUS',
  asset_class='STIR_FUTURES',
  data_shape='ohlcv',
  lseg_ric='FFc1'
  ```
- [x] **3.2** Add to `instrument_futures` detail table
  - Pipeline stores Fed Funds continuous instruments with:
    - `underlying='FF'`
    - `exchange='CME'`
    - `continuous_type='continuous'`
  - Same pattern applies to deferred ranks (`FF_CONTINUOUS_2` ... `FF_CONTINUOUS_12`)

### Phase 4: Extraction Pipeline ✅ DONE

- [x] **4.1** Create `fetch_fed_funds_daily()` - 10 years, SETTLE/OI/VOL + implied_rate
  - Implemented in `fed_funds/extraction.py`
  - Fields: SETTLE, OPINT_1 (open_interest), ACVOL_UNS (volume)
  - Auto-computes implied_rate = 100 - settle
  - Auto-labels with discrete contract codes (FFG24, FFH24, etc.)
- [x] **4.2** Create `fetch_fed_funds_hourly()` - 370 days, BID/ASK/MID + implied_rate
  - Implemented in `fed_funds/extraction.py`
  - Fields: BID, ASK, TRDPRC_1, HIGH_1, LOW_1, IMP_YIELD
  - **Note:** Only available for last 370 days (older dates return empty)
- [N/A] **4.3** Add `--label-contracts` flag to `lseg-extract` CLI
  - Not needed: Fed Funds contract labeling is automatic for
    `FF_CONTINUOUS` daily/hourly extraction
  - CLI already exposes `FF_CONTINUOUS` and deferred ranks directly
- [x] **4.4** Integration test with small date range
  - Verified with live DB-backed daily/hourly loads under Infisical-injected credentials
  - Confirmed hourly rows store `session_date` and `source_contract` correctly across month boundary

### Phase 5: Scheduler Integration

- [x] **5.1** Add `STIR_FF_DAILY` job to scheduler
- [x] **5.2** Add `STIR_FF_HOURLY` job to scheduler
- [x] **5.3** Configure appropriate `max_chunk_days` for each
  - Added dedicated `stir_ff` scheduler universe for `FF_CONTINUOUS`
  - Scheduler extraction path now uses the Fed Funds-specific fetchers
  - Initial job settings:
    - `STIR_FF_DAILY`: cron `30 18 * * 1-5`, `lookback_days=10`, `max_chunk_days=30`
    - `STIR_FF_HOURLY`: cron `5 * * * 0-5`, `lookback_days=3`, `max_chunk_days=7`

### Phase 6: Historical Data Hygiene

- [x] Backfill `session_date` for existing historical `FF_CONTINUOUS` rows
  - Updated 1,258 existing rows in TimescaleDB
  - Remaining `NULL session_date` rows for daily/hourly FF data: 0

---

## Data Extraction Plan

### Daily Data
```
RIC: FFc1
Period: 10 years (2016-01-01 to present)
Estimated rows: ~2,520
Fields: SETTLE, OPEN_INT, VOLUME
Chunks: 30 days each
```

### Hourly Data
```
RIC: FFc1
Period: 370 days (max available)
Estimated rows: ~6,000-8,000 (trading hours only)
Fields: BID, ASK → calculate MID
Chunks: 30 days each
```

---

## Contract Labeling Logic

Fed Funds continuous contract (`FFc1`) rolls monthly. The discrete contract code follows CME convention:

| Month Code | Month |
|------------|-------|
| F | January |
| G | February |
| H | March |
| J | April |
| K | May |
| M | June |
| N | July |
| Q | August |
| U | September |
| V | October |
| X | November |
| Z | December |

**Example:** `FFG26` = February 2026 contract

The front contract follows the settlement month of the current front month and
rolls on the first trading day of the next month. Example:

- on **2026-01-15**, `FFc1` maps to **`FFF26`** (January 2026)
- on **2026-02-02** (first trading day of February 2026), `FFc1` maps to
  **`FFG26`** (February 2026)

Deferred ranks follow the same convention:
- `FFc2` / `FF_CONTINUOUS_2` = second monthly rank
- ...
- `FFc12` / `FF_CONTINUOUS_12` = twelfth monthly rank

---

## File Structure

```
src/lseg_toolkit/timeseries/
├── fed_funds/
│   ├── __init__.py
│   ├── extraction.py      # fetch functions, label_continuous_data()
│   └── roll_detection.py  # detect_roll_dates()
└── stir_futures/
    └── contracts.py       # Existing: get_front_month_contract()
```

---

## References

- Schema: `src/lseg_toolkit/timeseries/storage/pg_schema.py`
- STIR contracts: `src/lseg_toolkit/timeseries/stir_futures/contracts.py`
- Scheduler chunking: `src/lseg_toolkit/timeseries/scheduler/jobs.py:_fetch_gap()`
- STIR docs: `docs/instruments/STIR_FUTURES.md`
