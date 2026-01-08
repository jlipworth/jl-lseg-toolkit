# Outstanding Work & Backlog

**Last Updated**: 2026-01-07

## Completed (This Session)

- [x] **Intraday Granularity Testing** - Validated all asset classes for tick/minute/5min/etc support
- [x] **Timezone Documentation** - Confirmed all LSEG timestamps are UTC
- [x] **Comprehensive Intraday Support Table** - Updated INSTRUMENTS.md with 30+ asset class breakdown
- [x] **RIC Pattern Discovery** - Found `=RRPS` for US yields intraday, `EUREST{tenor}=` for EUR OIS
- [x] **Storage Schema Redesign (RUNBOOK 23)** - Implemented multi-table schema by data shape
- [x] **Async Cache Layer (RUNBOOK 24)** - Implemented DataCache with sync/async APIs
- [x] **Equity Indices (Spot)** - Validated 34/36 global indices (US, Canada, Europe, Asia, LatAm)
- [x] **Volatility Indices** - Validated 8/18 VIX family indices (.VIX, .VXD, .VVIX, .V2TX, etc.)
- [x] **Index Futures Expansion** - Added 9 new futures (VX, SXF, FXXP, FMIB, YAP, SSN, IND, WSP, IPC)

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
| 19 | Stock Index Futures | ✅ Done (25 futures across US, EU, Asia, LatAm) |
| 20 | Commodity Futures | ✅ Done (24/24 commodities) |
| 25 | Timezone Conventions | ✅ Done (UTC confirmed) |
| 26 | Equity Indices (Spot) | ✅ Done (34/36 global indices + 8 VIX) |

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

## Schema Roadmap

### Instrument Detail Tables

| Table | Status | Asset Classes |
|-------|--------|---------------|
| `instrument_futures` | ✅ Done | Bond, STIR, Index, FX, Commodity futures |
| `instrument_fx` | ✅ Done | FX spot, FX forwards |
| `instrument_rate` | ✅ Done | OIS, IRS, FRA, Repo, Deposit |
| `instrument_bond` | ✅ Done | Govt yields, Corp bonds |
| `instrument_fixing` | ✅ Done | SOFR, ESTR, SONIA, EURIBOR |
| `instrument_equity` | ✅ Done | Stocks (AAPL.O, MSFT.O, etc.) |
| `instrument_etf` | ✅ Done | ETFs (SPY.P, QQQ.O, etc.) |
| `instrument_index` | ✅ Done | Spot indices (.SPX, .DJI, etc.) |
| `instrument_commodity` | 🔄 TODO | Commodity spot (not futures) |
| `instrument_cds` | 🔄 TODO | CDS indices, sovereign CDS |
| `instrument_option` | 🔄 TODO | Options chains metadata |

### Save Function Coverage

| Data Shape | Table | Save Function | Status |
|------------|-------|---------------|--------|
| OHLCV | timeseries_ohlcv | `_save_ohlcv_data` | ✅ Done |
| Quote | timeseries_quote | `_save_quote_data` | ✅ Done |
| Rate | timeseries_rate | `_save_rate_data` | ✅ Done |
| Bond | timeseries_bond | `_save_bond_data` | ✅ Done |
| Fixing | timeseries_fixing | `_save_fixing_data` | ✅ Done |

### Asset Class → Data Shape Mapping

| Asset Class | Data Shape | Notes |
|-------------|------------|-------|
| bond_futures, stir_futures, index_futures, fx_futures, commodity_futures | OHLCV | Futures use settle + OI |
| equity, etf, equity_index | OHLCV | Stocks/ETFs use close + volume |
| commodity | OHLCV | Commodity spot (gold, oil) |
| fx_spot, fx_forward | Quote | Bid/ask quotes |
| ois, irs, fra, deposit, repo | Rate | Rate quotes |
| govt_yield, corp_bond | Bond | Yield + price + analytics |
| fixing | Fixing | Single daily value |
| cds | Rate or custom | TBD - needs research |

---

## Technical Debt

### 1. Code Refactoring (from agent review)

See `dev_scripts/refactor_recommendations.md` for detailed analysis.

**Priority 1 - Critical:**
| Item | Impact | Estimated LOC Reduction |
|------|--------|-------------------------|
| Extract FieldMapper class | Centralize LSEG field mappings | -400 lines |
| Extract `_bulk_insert` helper | DRY for all save functions | -150 lines |
| Unify instrument detail saves | Replace 7 functions with 1 | -310 lines |

### 2. Code Updates Needed

| File | Change Needed |
|------|---------------|
| `fetch.py` | Add field mappings for different data shapes |
| `constants.py` | Add LSEG→storage field mappings |

### 3. Missing Tests

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
