## Known Limitations


### Intraday Data - WORKS! (with recent dates)

**Key Finding**: Intraday requires recent date range (30-90 days retention)

| Interval | Status | Example (TYc1, 1 day) |
|----------|--------|----------------------|
| daily | ✅ | 1 row |
| hourly | ✅ | 24 rows |
| 30min | ✅ | 48 rows |
| 15min | ❌ | Not supported |
| 10min | ✅ | 140 rows |
| 5min | ✅ | 277 rows |
| 1min | ✅ | 1,298 rows |
| tick | ✅ | 98,843 rows |

### Expired Contracts
The `^2` suffix for expired contracts (e.g., `TYH1^2` for Mar 2021) returns empty results. Needs investigation.

### Government Bond Yields
- **US Treasuries**: Use `=RRPS` suffix (e.g., `US10YT=RRPS`) - WORKS!
- **Other countries**: Use `=RR` suffix (e.g., `DE10YT=RR`, `GB10YT=RR`) - WORKS!
- **Eurozone**: All 11 countries validated with `{CC}{tenor}T=RR` pattern

### JGB Futures
Correct RIC: `JGBc1` (not `JBc1`) - WORKS!

### Options
Most options chains return "not found" or "access denied" - requires higher data tier.

---


---

## Validation History


| Date | Action | Result |
|------|--------|--------|
| 2025-01-05 | Initial validation run | Bond futures (TY, US, TU, FGBL, FGBM, FGBS), FX, OIS working |
| 2025-01-05 | Expanded OIS testing | Full curve 1M-30Y validated for USD SOFR |
| 2025-01-05 | Interval testing (old dates) | Daily only; all intraday empty |
| 2026-01-05 | Interval testing (recent dates) | **All intraday works!** hourly, 30min, 10min, 5min, 1min, tick |
| 2026-01-05 | US Treasury yields | Full curve works with `=RRPS` suffix |
| 2026-01-05 | FRAs | USD FRAs 1x4 through 3x9 all working |
| 2026-01-05 | USD Deposits | O/N through 1Y all working |
| 2026-01-06 | EUR IRS | 17/17 tenors validated with `EURIRS{tenor}=` |
| 2026-01-06 | GBP OIS | 14/14 tenors validated with `GBP{tenor}OIS=` |
| 2026-01-06 | JPY rates | OIS 8/8, IRS 9/9, FRAs 4/4 working |
| 2026-01-06 | CHF rates | OIS 8/8, IRS 9/9, SARON working |
| 2026-01-06 | CAD rates | OIS 8/8, IRS 8/9, CORRA working |
| 2026-01-06 | Eurozone sovereigns | All 11 countries (DE, FR, IT, ES, NL, BE, AT, PT, IE, GR, FI) validated |
| 2026-01-06 | Index futures | 16 validated (ES, NQ, RTY, YM, STXE, FDX, FFI, FCE, FSMI, AEX, JNI, NIY, HSI, HCEI, KS, TX) |
| 2026-01-06 | Commodity futures | 24/24 all working (energy, metals, grains, softs, livestock) |
| 2026-01-06 | USD IRS | 10/10 tenors validated with `USDIRS{tenor}=` |
| 2026-01-06 | JGB futures | Found with `JGBc1` (not `JBc1`) |
| 2026-01-06 | Options research | Limited access - only VIX index and STIR chains work |
| 2026-01-06 | Swaptions research | `=TTKL` pattern requires Tradeweb subscription |
| 2026-01-06 | G7 Sovereign curves | Full curves validated: US 13/13, DE 9/9, GB 9/9, FR 9/9, IT 9/9, CA 8/8, AU 6/6, CH 4/4 |
| 2026-01-06 | JGB yields | JP{tenor}T=RR exists but returns "access_denied" (needs JGB data package) |
| 2026-01-06 | Corporate bonds | CUSIP-based RICs work! Rich historical data (yields, spreads, duration) |
| 2026-01-06 | Bond indices | CSI Credit Bond indices, ICE Treasury indices validated |
| 2026-01-06 | DuckDB storage | Implemented with native Parquet export, SQLite migration |
| 2026-01-06 | Full sovereign curves | Added short-end tenors (1M-9M) - DE 18, GB 20, FR 19 tenors total |
| 2026-01-06 | Options validated | OPRA equity (SPX, VIX, AAPL), CME futures (ES, NQ, TY), commodity (CL, GC) - all working |
| 2026-01-06 | OAS/Spreads | Corporate bond OAS fields work with full history (OAS_BID, ZSPREAD, BMK_SPD, etc.) |
| 2026-01-06 | Caps/Floors | RICs exist but require premium subscription (Tradeweb/ICAP) |
| 2026-01-06 | FX Futures | All 9 CME FX futures validated (URO, BP, JY, AD, CD, SF, MP, NE, BR) |
| 2026-01-06 | VIX Futures | VXc1, VXc2, VXc3 and chain (14 contracts) validated |
| 2026-01-06 | EM FX Spot | All 18 EM pairs validated (MXN, BRL, ZAR, TRY, INR, CNH, SGD, HKD, KRW, PLN, CZK, HUF, RUB, THB, TWD, IDR, PHP, MYR) |
| 2026-01-06 | FX Crosses | 17/18 cross pairs validated |
| 2026-01-06 | FX Forwards | 10/11 tenors working for EUR, GBP, JPY, CHF, AUD, CAD |
| 2026-01-06 | European Bond Futures | 7/8 validated (FGBL, FGBM, FGBS, FGBX, FOAT, FBTP, FLG) |
| 2026-01-06 | Canadian Bond Futures | All 3 validated (CGB, CGF, CGZ) |
| 2026-01-06 | Australian Bond Futures | Not found (YT, XT, XM patterns) |
| 2026-01-06 | Overnight Rates | SOFR, EUROSTR, SARON, CORRA working; SONIA/TONA access denied |
| 2026-01-06 | EURIBOR | 4/5 tenors working (1M, 3M, 6M, 12M; 1W not found) |
| 2026-01-06 | Repo Rates | 5 tenors validated (ON, 1W, 2W, 1M, 3M) |
| 2026-01-06 | Sovereign CDS | Pattern `{CC}GVCUSD5Y=` works! 17 countries validated with 260 rows history |
| 2026-01-06 | Australian Bond Futures | Found correct pattern `YTTc1` (3Y) and `YTCc1` (10Y) - both working |
| 2026-01-06 | Euro Stoxx Options | Pattern `STXE{strike}{month}{YY}.EX` validated |
| 2026-01-06 | DAX Options | Pattern `GDAX{week}W{strike}{month}{YY}.EX` for weeklies |
| 2026-01-06 | Bund Options | Pattern `OGBL{strike}{month}{YY}` validated (OGBL1300C6, etc.) |
| 2026-01-06 | Scandinavian FX | SEK=, NOK=, DKK=, EURSEK=, EURNOK=, EURDKK= all working |
| 2026-01-06 | Additional EM FX | 35 more currencies validated (CEEMEA, Middle East, Asia, LatAm, Africa) |
| 2026-01-06 | NDFs | 26/29 working (CNY, KRW, INR, TWD, BRL, IDR, PHP) |
| 2026-01-06 | EM FX Forwards | 11/12 currencies with full curve (1M-1Y), BRL uses NDF |
| 2026-01-06 | FX Implied Vol | Pattern `{CCY}{tenor}O=` works! G10, crosses, and EM vol validated (55+ RICs) |
| 2026-01-06 | Currency Indices | .DXY, DXc1 (Dollar Index), EURX=, JPYX= working |
| 2026-01-06 | FX Cross Futures | RPc1, RYc1, RFc1, CNHc1, KRWc1 validated |

---


---

## Swap Spreads & Asset Swap Spreads (Roadmap)


### Swap Spreads (Swap Rate - Treasury Yield)

| Tenor | Symbol | LSEG RIC | Status | Notes |
|-------|--------|----------|--------|-------|
| 2Y Swap Spread | USS2Y | `🔄` | 🔄 | 2Y Swap - 2Y Treasury |
| 5Y Swap Spread | USS5Y | `🔄` | 🔄 | 5Y Swap - 5Y Treasury |
| 10Y Swap Spread | USS10Y | `🔄` | 🔄 | 10Y Swap - 10Y Treasury |
| 30Y Swap Spread | USS30Y | `🔄` | 🔄 | 30Y Swap - 30Y Treasury |

### Asset Swap Spreads (Z-Spread over Swap Curve)

| Instrument | LSEG RIC | Status | Notes |
|------------|----------|--------|-------|
| On-the-run 10Y ASW | `🔄` | 🔄 | Treasury asset swap spread |
| Corporate Bond ASW | `🔄` | 🔄 | Per-bond asset swap |

### Related Fields to Research

| Field | Description | Status |
|-------|-------------|--------|
| `TR.AssetSwapSpread` | Asset swap spread | 🔄 |
| `TR.ZSpread` | Z-spread over swap curve | 🔄 |
| `TR.OAS` | Option-adjusted spread | 🔄 |
| `TR.ISpread` | I-spread (interpolated swap) | 🔄 |
| `TR.GSpread` | G-spread (govt benchmark) | 🔄 |

---


---

## Bond Basis Trading (Roadmap)


### Deliverable Basket & CTD

| Data | LSEG RIC | Status | Notes |
|------|----------|--------|-------|
| Deliverable basket | `0#TYc1=DLV` | ✅ | Returns CUSIP RICs |
| CTD ranking | `0#TYc1=CTD` | ✅ | Ranked by basis |
| Net basis | `NET_BASIS` field | ✅ | On CTD RICs |
| Carry cost | `CARRY_COST` field | ✅ | On CTD RICs |
| Implied repo | `REPO_RATE` field | ✅ | On CTD RICs |
| Conversion factors | CME source | ❌ | Not in LSEG API |
| Invoice chain | `0#TY=INV` | ❌ | Access Denied |

### CF Calculation (CME Formula)

Conversion factors must be calculated or obtained from CME. See [BOND_BASIS_RICS.md](ric-guides/BOND_BASIS_RICS.md).

**Historical CF Considerations:**
- Current era (2020s): Low coupons (3-5%) → CFs typically 0.85-0.95
- Historical era (1980s-90s): High coupons (8%+) → CFs could be > 1.0
- When fetching historical basis data, must use the CF that was in effect at that time
- CME publishes historical CF lookup tables by contract delivery month
- The coupon rate of deliverable bonds changes the CF significantly

---


---

## Next Validation Priorities


**Completed:**
- ~~STIR Futures~~: SOFR (SRAc1), Fed Funds (FFc1), Euribor (FEIc1), SONIA (SONc1) ✅
- ~~Stock Index Futures~~: ES, NQ, RTY, YM, STXE, FDX, FFI, JNI, HSI + more ✅
- ~~EUR/GBP/G7 OIS~~: All G7+ currencies validated ✅
- ~~Commodity Futures~~: All 24 commodities validated ✅
- ~~Credit (CDX Indices)~~: CDX IG/HY 1Y-10Y working ✅
- ~~Corporate Bonds~~: CUSIP-based RICs work with rich field coverage ✅
- ~~Full Sovereign Curves~~: All tenors validated (US 13, DE 18, GB 20, FR 19, IT 19, etc.) ✅
- ~~DuckDB Migration~~: Implemented with native Parquet export ✅

**Remaining:**
1. **Swap Spreads**: RICs exist (`USDSSPRD{tenor}=`) but no data populated - may need premium
2. ~~**FX Forwards**~~: ✅ 72 forward swap points + 12 outrights + 14 cross forwards + 44 EM forwards + 26 NDFs
3. **iTraxx Indices**: Find correct RIC patterns for European credit
4. ~~**Sovereign CDS**~~: ✅ Pattern `{CC}GVCUSD5Y=` works for 17 countries
5. ~~**Options**~~: ✅ Validated! OPRA, CME futures, commodity options all work
6. ~~**European Options**~~: ✅ Bund (`OGBL`), Euro Stoxx (`STXE`), DAX (`GDAX`) validated
7. ~~**Australian Bond Futures**~~: ✅ Found correct patterns `YTTc1` (3Y) and `YTCc1` (10Y)
8. **Async Cache Layer**: Implement for efficient data retrieval (RUNBOOK 24)
9. ~~**FX Implied Vol**~~: ✅ Full surface from 2W-5Y for G10 (27+ additional tenors)

**Newly Completed (2026-01-06):**
- ~~FX Futures~~: All 9 CME FX futures validated ✅
- ~~VIX Futures~~: Full chain validated ✅
- ~~EM FX Spot~~: All 18 pairs + 35 additional EM currencies validated ✅
- ~~FX Crosses~~: 17/18 pairs validated ✅
- ~~European Bond Futures~~: 7/8 validated ✅
- ~~Canadian Bond Futures~~: All 3 validated ✅
- ~~OAS/Spreads~~: Corporate bond OAS fields with history ✅
- ~~Overnight Rates~~: SOFR, EUROSTR, SARON, CORRA validated ✅
- ~~Sovereign CDS~~: 17 countries validated with full history ✅
- ~~Australian Bond Futures~~: 3Y and 10Y validated ✅
- ~~European Index Options~~: Euro Stoxx 50 and DAX validated ✅
- ~~Bund Options~~: Pattern validated (OGBL) ✅
- ~~FX Vol Extended Tenors~~: 2W-5Y for G10 (27 additional RICs) ✅
- ~~FX Forward Swap Points~~: 72 RICs (9 G10 currencies × 8 tenors) ✅
- ~~FX Forward Outrights~~: 12 RICs ({CCY}{tenor}V= pattern) ✅
- ~~FX Cross Forwards~~: 14 EUR/GBP cross forward points ✅
- ~~NDFs~~: 26/29 restricted currency NDFs (CNY, KRW, INR, TWD, BRL, IDR, PHP) ✅
- ~~US Treasury Futures~~: All 8/8 validated with correct RICs (YRc1, ZPc1, AULc1) ✅
- ~~DXY~~: Spot (.DXY), futures (DXc1-3), and options (1DX pattern) with full history ✅
- ~~European Bond Futures~~: 11/12 validated (added BTP Short, BONO, Swiss CONF) ✅

---


---

## Final Step: Pre-Release Refactor (RUNBOOK 999)


Before publishing the timeseries extraction module:

1. **Code Review**: Holistic review of the entire `src/lseg_toolkit/timeseries/` module
2. **API Consistency**: Ensure all public functions have consistent signatures
3. **Error Handling**: Standardize exception types and messages
4. **Documentation**: Update all docstrings and type hints
5. **Integration Tests**: Add end-to-end tests with LSEG session
6. **Performance**: Profile and optimize bulk data operations
7. **CLI**: Review `lseg-extract` command interface
8. **README**: Update with examples for new asset classes
