# Outstanding Work & Backlog

**Last Updated**: 2026-01-07

## Completed (This Session)

- [x] **Intraday Granularity Testing** - Validated all asset classes for tick/minute/5min/etc support
- [x] **Timezone Documentation** - Confirmed all LSEG timestamps are UTC
- [x] **Comprehensive Intraday Support Table** - Updated INSTRUMENTS.md with 30+ asset class breakdown
- [x] **RIC Pattern Discovery** - Found `=RRPS` for US yields intraday, `EUREST{tenor}=` for EUR OIS
- [x] **Storage Schema Redesign (RUNBOOK 23)** - Implemented multi-table schema by data shape
- [x] **Async Cache Layer (RUNBOOK 24)** - Implemented DataCache with sync/async APIs

---

## In Progress

(No items currently in progress)

---

## Validated & Documented (No Action Needed)

These runbooks are effectively complete - the data is validated and documented in `docs/INSTRUMENTS.md`:

| Runbook | Topic | Status |
|---------|-------|--------|
| 7 | USD Treasury Yields | ✅ Done (all tenors in INSTRUMENTS.md) |
| 8 | USD OIS/SOFR Curve | ✅ Done (14/14 working) |
| 9 | Treasury Repo Rates | ✅ Done (8/10 working) |
| 10 | USD FRAs & Money Market | ✅ Done (12/12 FRAs working) |
| 11 | STIR Futures | ✅ Done (SRAc1, FFc1 working) |
| 14 | EUR Rates | ✅ Done (EUR IRS 17/17, EURIBOR 4/5) |
| 15 | GBP Rates | ✅ Done (GBP OIS 14/14, Gilts 4/4) |
| 16 | JPY Rates | ✅ Done (JPY OIS 8/8, JPY IRS 9/9) |
| 17 | CHF Rates | ✅ Done (CHF OIS 8/8) |
| 18 | CAD Rates | ✅ Done (CAD OIS 8/8) |
| 19 | Stock Index Futures | ✅ Done (ES, NQ, STXE, etc) |
| 20 | Commodity Futures | ✅ Done (24/24 commodities) |
| 25 | Timezone Conventions | ✅ Done (UTC confirmed) |

---

## Deferred / Low Priority

### RUNBOOK 21: Credit Instruments (CDS)

**Status**: Partial - daily only, intraday not available
**Priority**: LOW

CDS indices (IBOXIG05=MP, IBOXHY05=MP) work for daily data but not intraday.
Documented in INSTRUMENTS.md.

### RUNBOOK 22: Options Research

**Status**: Not started
**Priority**: LOW

Individual options RICs don't support time series (only snapshots).
Need to research chain discovery and Greeks fields.

---

## Technical Debt

### 1. Code Updates Needed

| File | Change Needed |
|------|---------------|
| `fetch.py` | Add field mappings for different data shapes |
| `constants.py` | Add LSEG→storage field mappings |

### 2. Missing Tests

- No tests for intraday data fetching
- ~~No tests for DuckDB storage~~ (added in test_duckdb_storage.py)
- ~~No tests for cache layer~~ (added in test_cache.py - 33 tests)
- No integration tests with LSEG API

---

## Session Notes

### Key Discoveries (2026-01-07)

1. **Intraday requires `count` parameter**, not date range
2. **US yields**: Use `=RRPS` suffix for intraday (not `=RR`)
3. **EUR OIS**: Use `EUREST{tenor}=` pattern (not `EUR{tenor}OIS=`)
4. **All timestamps are UTC** - verified against exchange hours
5. **Query limit**: 50,000 bars max per request

### RUNBOOK 24 Implementation

Implemented `DataCache` in `src/lseg_toolkit/timeseries/cache.py`:

```python
from lseg_toolkit.timeseries import DataCache, CacheConfig

# Sync usage
cache = DataCache()
df = cache.get_or_fetch("TYc1", start="2024-01-01", end="2024-12-31")

# Async usage
results = await cache.async_get_or_fetch_many(
    ["TYc1", "USc1", "FVc1"],
    start="2024-01-01",
    end="2024-12-31"
)
```

Key features:
- **InstrumentRegistry**: Validates RICs against known set from constants.py
- **Granularity-aware gap detection**: Daily data doesn't satisfy 5min requests
- **Async/await**: Parallel fetching with semaphore rate limiting
- **Progress tracking**: Callback support for batch operations

### Data Shape Classification

| Shape | Asset Classes | Key Fields |
|-------|--------------|------------|
| OHLCV | Futures, Equities, Commodities | open, high, low, close, settle, volume, OI |
| Quote | FX, OIS, IRS, FRA | bid, ask, mid, bid_high, bid_low |
| Bond | Govt Yields | price OHLC + yield OHLC + analytics |
| Fixing | SOFR, ESTR, SONIA | single value per day |
