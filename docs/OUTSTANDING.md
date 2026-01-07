# Outstanding Work & Backlog

**Last Updated**: 2026-01-07

## Completed (This Session)

- [x] **Intraday Granularity Testing** - Validated all asset classes for tick/minute/5min/etc support
- [x] **Timezone Documentation** - Confirmed all LSEG timestamps are UTC
- [x] **Comprehensive Intraday Support Table** - Updated INSTRUMENTS.md with 30+ asset class breakdown
- [x] **RIC Pattern Discovery** - Found `=RRPS` for US yields intraday, `EUREST{tenor}=` for EUR OIS

---

## In Progress

### Storage Schema Redesign (RUNBOOK 23)

**Status**: Schema design drafted, needs implementation

**Problem**: Current `ohlcv_daily` table tries to store all data types, but:
- Rates (OIS, IRS) have bid/ask/mid, not OHLCV
- Govt yields have price + yield + analytics
- Fixings (SOFR, EURIBOR) are single daily values

**Proposed Solution**: Normalize by data shape:
- `ohlcv_daily` - Futures, equities, commodities
- `quote_daily` - FX, OIS, IRS, FRA (bid/ask/mid)
- `bond_daily` - Govt yields (price + yield + analytics)
- `fixing_daily` - SOFR, ESTR, SONIA, EURIBOR

**Open Questions** (see `docs/STORAGE_SCHEMA.md`):
1. Separate table for govt bonds or extend quote_daily?
2. Separate intraday tables per data shape?
3. Store regional FX session data (Asia/EUR/AMER)?
4. Value date vs trade date indexing?

**Files**:
- `docs/STORAGE_SCHEMA.md` - Draft schema design
- `src/lseg_toolkit/timeseries/duckdb_storage.py` - Needs update

---

## Pending

### RUNBOOK 24: Async Cache Layer

**Priority**: HIGH

**Objective**: Cache-first architecture for data retrieval

```python
# Desired API
cache = DataCache(db_path="data/timeseries.duckdb")
df = cache.get_or_fetch(ric="TYc1", start="2024-01-01", end="2024-12-31")
```

**Features**:
- Check local DB before hitting LSEG API
- Gap detection (find missing date ranges)
- Async/parallel fetching for multiple RICs
- Progress tracking for batch extraction

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

### 1. Plan File Cleanup

The plan file at `~/.claude/plans/majestic-exploring-quilt.md` is stale:
- Many runbooks marked "Not Started" are actually complete
- Should archive or delete after this session

### 2. Code Updates Needed

| File | Change Needed |
|------|---------------|
| `duckdb_storage.py` | Implement new schema (quote_daily, bond_daily, fixing_daily) |
| `fetch.py` | Add field mappings for different data shapes |
| `constants.py` | Add LSEG→storage field mappings |

### 3. Missing Tests

- No tests for intraday data fetching
- No tests for DuckDB storage
- No integration tests with LSEG API

---

## Session Notes

### Key Discoveries (2026-01-07)

1. **Intraday requires `count` parameter**, not date range
2. **US yields**: Use `=RRPS` suffix for intraday (not `=RR`)
3. **EUR OIS**: Use `EUREST{tenor}=` pattern (not `EUR{tenor}OIS=`)
4. **All timestamps are UTC** - verified against exchange hours
5. **Query limit**: 50,000 bars max per request

### Data Shape Classification

| Shape | Asset Classes | Key Fields |
|-------|--------------|------------|
| OHLCV | Futures, Equities, Commodities | open, high, low, close, settle, volume, OI |
| Quote | FX, OIS, IRS, FRA | bid, ask, mid, bid_high, bid_low |
| Bond | Govt Yields | price OHLC + yield OHLC + analytics |
| Fixing | SOFR, ESTR, SONIA | single value per day |
