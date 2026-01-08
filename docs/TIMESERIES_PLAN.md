# Time Series Implementation History

> **Note:** This is a historical planning document. The implementation is complete.
>
> - **For users:** See [TIMESERIES.md](TIMESERIES.md)
> - **For instrument list:** See [INSTRUMENTS.md](INSTRUMENTS.md)
> - **For schema details:** See [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md)

---

## Key Discoveries

These findings were made during validation and are preserved for reference.

### CME to LSEG Symbol Mapping

CME and LSEG use different symbology for the same instruments:

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| ZN | TYc1 | 10-Year Treasury Note |
| ZB | USc1 | 30-Year Treasury Bond |
| ZF | FVc1 | 5-Year Treasury Note |
| ZT | TUc1 | 2-Year Treasury Note |
| FGBL | FGBLc1 | Euro-Bund 10Y |
| FGBM | FGBMc1 | Euro-Bobl 5Y |
| FGBS | FGBSc1 | Euro-Schatz 2Y |

### RIC Patterns by Asset Class

**Bond Futures (Continuous):**
- US Treasury: `TYc1`, `USc1`, `FVc1`, `TUc1`
- European: `FGBLc1`, `FGBMc1`, `FGBSc1`
- Pattern: `{ROOT}c{N}` where N=1 for front month

**FX Spot:**
- Pattern: `{CCY}=` (e.g., `EUR=`, `GBP=`, `JPY=`)
- Cross rates: `{CCY1}{CCY2}=` (e.g., `EURGBP=`)

**FX Forwards:**
- Pattern: `{CCY}{TENOR}=` (e.g., `EUR1M=`, `EUR3M=`, `EUR1Y=`)

**OIS (SOFR):**
- Pattern: `USD{TENOR}OIS=` (e.g., `USD1MOIS=`, `USD1YOIS=`, `USD30YOIS=`)
- Full curve: 1M, 2M, 3M, 4M, 5M, 6M, 9M, 1Y, 18M, 2Y-10Y, 12Y, 15Y, 20Y, 25Y, 30Y

**Treasury Yields:**
- Pattern: `US{TENOR}YT=RRPS` (e.g., `US10YT=RRPS`)
- Note: Use `=RRPS` suffix, not `=RR`

**Fixings:**
- SOFR: `USDSOFR=`
- ESTR: `EUROSTR=`

### LSEG Field Mappings

| Data Shape | LSEG Fields | Our Columns |
|------------|-------------|-------------|
| OHLCV | OPEN_PRC, HIGH_1, LOW_1, TRDPRC_1, SETTLE, ACVOL_UNS, OPINT_1 | open, high, low, close, settle, volume, open_interest |
| FX Quote | BID, ASK, MID_PRICE, OPEN_BID, BID_HIGH_1, BID_LOW_1 | bid, ask, mid, open_bid, bid_high, bid_low |
| Rate | BID, ASK, MID_PRICE, OPEN_BID, BID_HIGH_1, BID_LOW_1 | rate, bid, ask, open_rate, high_rate, low_rate |
| Bond | B_YLD_1, A_YLD_1, HIGH_YLD, LOW_YLD, MOD_DURTN, CONVEXITY, BPV | yield_bid, yield_ask, yield_high, yield_low, mod_duration, convexity, dv01 |
| Fixing | FIXING_1, ACVOL_UNS | value, volume |

### Intraday Data Notes

- **Retention:** ~90 days for most instruments
- **Request limit:** 50,000 bars max
- **Requires `count` parameter:** Date ranges don't work well for intraday
- **All timestamps are UTC**

### Known Limitations

1. **Expired contracts:** `^N` format (e.g., `TYH1^2`) returns empty - historical discrete contracts not accessible
2. **Permission issues:** Some RICs require additional entitlements
3. **No real-time:** This library is for historical data only

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| DuckDB over SQLite | Better analytics performance, native Parquet export |
| Shape-specific tables | Different asset classes have fundamentally different data |
| Module-level functions | Matches existing codebase patterns |
| No DataProvider protocol | Abstraction point is output schema, not data source |

---

## Original Implementation Timeline

1. **Phase 0:** LSEG validation (discovered RIC patterns)
2. **Phase 1:** Core models and enums
3. **Phase 2:** Storage layer (SQLite, later migrated to DuckDB)
4. **Phase 3:** Fetch layer with field mappings
5. **Phase 4:** Continuous contract rolling logic
6. **Phase 5:** CLI and pipeline
7. **Phase 6:** Testing and documentation
