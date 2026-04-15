## Bloomberg Tickers — Partial Support (Unvalidated)

> ⚠️ **Status: partial / unvalidated.** The ticker patterns below were probed against a live
> Terminal on 2026-01-16, but the `bbg-extract` package surface has **not** been re-validated
> end-to-end since the rebase onto master. The maintainer does not currently have ongoing
> Bloomberg Terminal access, so behavior in new environments is unconfirmed.
>
> Anyone running these workflows against a live Terminal should follow
> [`docs/BLOOMBERG_LIVE_VALIDATION_RUNBOOK.md`](../BLOOMBERG_LIVE_VALIDATION_RUNBOOK.md) and open
> issues for any divergence from the documented ticker/field matrix.

This document covers Bloomberg Terminal tickers for instruments where LSEG has permission restrictions.

**API**: BLPAPI Desktop API via localhost:8194
**Partial package**: `src/lseg_toolkit/bloomberg/` (JGB yields, FX ATM vol)
**Partial CLI**: `bbg-extract` (unvalidated)
**Research / probe scripts**: `bloomberg_scripts/` (research-only; not part of the supported surface)
**Research findings log**: `docs/BLOOMBERG_FINDINGS.md`

Install Bloomberg runtime support with:

```bash
uv sync --group bloomberg
```

Current partial (unvalidated) Bloomberg surface:
- `bbg-extract jgb`
- `bbg-extract fx-atm-vol`

Current research-only areas (unvalidated, Terminal required):
- swaptions
- caps/floors
- FX RR/BF
- treasury basis / CTD exploration

---

### Quick Start

Supported Bloomberg commands today:

```bash
uv sync --group bloomberg
bbg-extract jgb
bbg-extract jgb --historical --start-date 2025-01-01
bbg-extract fx-atm-vol --pairs EURUSD USDJPY --tenors 1M 3M
```

If `bbg-extract` reports a Bloomberg runtime error, first verify:
- Bloomberg Terminal is running and logged in
- Desktop API is reachable on `localhost:8194`
- under WSL, `nc -z localhost 8194` succeeds


### JGB Yields ✅ WORKING

**LSEG Status**: ⛔ Access Denied (requires JGB data package)
**Bloomberg Status**: ✅ Working

| Tenor | Bloomberg Ticker | Fields | Status | Sample Value (2026-01-16) |
|-------|-----------------|--------|--------|---------------------------|
| 2Y | `GJGB2 Index` | PX_LAST | ✅ | 1.206% |
| 5Y | `GJGB5 Index` | PX_LAST | ✅ | 1.652% |
| 10Y | `GJGB10 Index` | PX_LAST | ✅ | 2.190% |
| 20Y | `GJGB20 Index` | PX_LAST | ✅ | 3.166% |
| 30Y | `GJGB30 Index` | PX_LAST | ✅ | 3.494% |
| 40Y | `GJGB40 Index` | PX_LAST | ✅ | 3.816% |

**Supported extractor**: `src/lseg_toolkit/bloomberg/jgb.py`
**Original validation script**: `bloomberg_scripts/extract_jgb.py`

---

### FX ATM Implied Volatility ✅ WORKING

**LSEG Status**: ⛔ Access Denied (premium FX options data)
**Bloomberg Status**: ✅ Working

**Working Pattern**: `{PAIR}V{TENOR} BGN Curncy`

**Validated 2026-01-16**: All 6 pairs × 8 tenors = **48 data points** ✅

| Pair | 1W | 1M | 2M | 3M | 6M | 9M | 1Y | 2Y |
|------|----|----|----|----|----|----|----|----|
| EURUSD | ✅ 4.39 | ✅ 4.99 | ✅ 5.23 | ✅ 5.45 | ✅ 5.86 | ✅ 6.19 | ✅ 6.41 | ✅ 6.88 |
| USDJPY | ✅ 7.63 | ✅ 8.40 | ✅ 8.60 | ✅ 8.83 | ✅ 9.07 | ✅ 9.25 | ✅ 9.28 | ✅ 9.15 |
| GBPUSD | ✅ 5.00 | ✅ 5.61 | ✅ 5.91 | ✅ 6.21 | ✅ 6.84 | ✅ 7.28 | ✅ 7.54 | ✅ 7.94 |
| AUDUSD | ✅ 6.03 | ✅ 7.13 | ✅ 7.55 | ✅ 7.86 | ✅ 8.50 | ✅ 8.89 | ✅ 9.13 | ✅ 9.42 |
| USDCHF | ✅ 5.63 | ✅ 6.20 | ✅ 6.45 | ✅ 6.67 | ✅ 7.03 | ✅ 7.34 | ✅ 7.47 | ✅ 7.79 |
| USDCAD | ✅ 3.37 | ✅ 4.04 | ✅ 4.30 | ✅ 4.41 | ✅ 4.82 | ✅ 5.08 | ✅ 5.28 | ✅ 5.61 |

**Example Tickers**:
| Ticker | Value | Description |
|--------|-------|-------------|
| `EURUSDV1M BGN Curncy` | 4.99 | EUR-USD OPT VOL 1M |
| `USDJPYV1M BGN Curncy` | 8.40 | USD-JPY OPT VOL 1M |
| `GBPUSDV3M BGN Curncy` | 6.21 | GBP-USD OPT VOL 3M |

**Supported extractor**: `src/lseg_toolkit/bloomberg/fx_atm_vol.py`
**Original validation script**: `bloomberg_scripts/extract_fx_vol.py`

---

### FX Risk Reversals & Butterflies ❌ NOT WORKING

**Tested Patterns (all return same value or fail)**:

| Pattern | Example | Result |
|---------|---------|--------|
| `{PAIR}{TENOR}{DELTA}RR BGN Curncy` | `EURUSD1M25RR BGN Curncy` | Returns same as ATM (not real RR) |
| `{PAIR}{TENOR}{DELTA}BF BGN Curncy` | `EURUSD1M25BF BGN Curncy` | Returns same as ATM (not real BF) |
| `{PAIR}RR{TENOR} BGN Curncy` | `EURUSDRR1M BGN Curncy` | ❌ Invalid |
| `{PAIR}25RR{TENOR} BGN Curncy` | `EURUSD25RR1M BGN Curncy` | ❌ Invalid |

**Note**: The RR/BF tickers exist but return the same value as ATM vol (suspicious). Real RR/BF data may require different tickers or terminal-only access.

---

### Swaption Volatility ❌ API ACCESS NOT CONFIRMED

**LSEG Status**: ⛔ Access Denied (requires Tradeweb `=TTKL` subscription)
**Bloomberg Status**: ❌ Visible on terminal (VCUB), but API ticker not working

**Terminal Discovery (2026-01-16)**:
- Screen label: `EUR SWPT NVOL 1Y10Y` (EUR Swaption Normal Vol, 1Y expiry into 10Y swap)
- Possible ticker found: `EUSN0110 BVOL Curncy`
  - `EUSN` = EUR Swaption
  - `01` = 1Y expiry
  - `10` = 10Y tenor
  - `BVOL` = Black vol (lognormal) / `NVOL` = Normal vol (Bachelier, bps)

**Tested API Patterns (all failed)**:

| Pattern | Example | Result |
|---------|---------|--------|
| `EUSN{exp}{tenor} BVOL Curncy` | `EUSN0110 BVOL Curncy` | ❌ No data via API |
| `EUSN{exp}{tenor} NVOL Curncy` | `EUSN0110 NVOL Curncy` | ❌ No data via API |
| `USSN{exp}{tenor} BVOL Curncy` | `USSN0110 BVOL Curncy` | ❌ No data via API |
| `USSV{exp}{tenor} BGN Curncy` | `USSV1Y10Y BGN Curncy` | ❌ Unknown Security |
| `USSW{exp}{tenor} BGN Curncy` | `USSW1Y10Y BGN Curncy` | ❌ Unknown Security |
| `{CCY}SWPTNVOL{exp}{tenor}` | `EURSWPTNVOL1Y10Y Curncy` | ❌ Unknown Security |
| `{CCY} SWPT NVOL {exp}{tenor} Index` | `EUR SWPT NVOL 1Y10Y Index` | Returns FX spot (wrong) |

**60+ patterns tested** including:
- V-pattern (like FX vol): `USDSWV1Y10Y`
- Normal vs Black vol prefixes: `USSN`, `USSB`, `USSL`
- SOFR-based: `USSOFRV1Y10Y`
- Different sources: ICAP, GFI, BGN
- Index vs Curncy yellow keys
- Various spacing/formatting

**Standard Grid**:
- Expiries: 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y
- Tenors: 2Y, 5Y, 10Y, 30Y
- = 28 points per currency

**Next Steps for Swaption Vol**:
1. On terminal: `EUSN0110 BVOL Curncy <GO>` - verify if this ticker resolves
2. On terminal: Click on vol cell in VCUB → `<HELP><HELP>` to see field/ticker info
3. Try `ALLQ EUSN0110 <GO>` to see all quotes
4. Check if B-PIPE subscription required for API access
5. Contact Bloomberg help desk for correct API ticker format

**Conclusion**: Swaption vol data is visible on Bloomberg terminal (VCUB function) but may not be accessible via Desktop API. May require B-PIPE or special permissions.

---

### Treasury Futures & Bond Basis 🔄 EXPERIMENTAL

**Validated 2026-01-16**

**Support level**: Experimental / research helper, not part of the supported `bbg-extract` CLI yet.

**Futures Tickers** (generic front-month):

| Contract | Ticker | Name | Status |
|----------|--------|------|--------|
| 2Y Note | `TU1 Comdty` | Generic 1st 'TU' Future | ✅ |
| 5Y Note | `FV1 Comdty` | Generic 1st 'FV' Future | ✅ |
| 10Y Note | `TY1 Comdty` | Generic 1st 'TY' Future | ✅ |
| Ultra 10Y | `UXY1 Comdty` | Generic 1st 'UXY' Future | ✅ |
| T-Bond | `US1 Comdty` | Generic 1st 'US' Future | ✅ |
| Ultra Bond | `WN1 Comdty` | Generic 1st 'WN' Future | ✅ |

**Specific Contract Pattern**: `{ROOT}{MONTH}{YEAR} Comdty` (e.g., `TYH6 Comdty` = 10Y Mar26)

**CTD / Basis Fields** (require specific contract, not generic):

| Field | Description | Status |
|-------|-------------|--------|
| `FUT_CTD_TICKER` | CTD bond ticker | ✅ `T 4.125 11/15/32` |
| `FUT_CTD_CUSIP` | CTD CUSIP | ✅ `91282CFV8` |
| `FUT_CTD_ISIN` | CTD ISIN | ✅ `US91282CFV81` |
| `FUT_CTD_NET_BASIS` | Net basis (32nds) | ✅ `2.20` |
| `FUT_CTD_GROSS_BASIS` | Gross basis | ✅ `4.53` |
| `FUT_CTD_IMPLIED_REPO` | Implied repo rate | ❌ Not available |
| `FUT_CTD_CONV_FACTOR` | Conversion factor | ❌ Not available |
| `FUT_DLVRBL_BNDS_*` | Deliverable basket | ❌ Not available (terminal DLV only) |

**Historical Availability**:

| Field | Historical | Notes |
|-------|------------|-------|
| `PX_LAST` | ✅ Yes | Years of history |
| `FUT_CTD_NET_BASIS` | ✅ Yes | Works on generic (TY1) |
| `FUT_CTD_GROSS_BASIS` | ✅ Yes | Works on generic (TY1) |
| `FUT_CTD_IMPLIED_REPO` | ❌ No | Not available historically |

**Important**: Generic contracts (TY1) return historical basis but NOT current CTD info. Use specific contracts (TYH6) for current CTD ticker/CUSIP.

**Contract Fields**:

| Field | Description |
|-------|-------------|
| `FUT_CONT_SIZE` | Contract size (100000 for TY) |
| `FUT_FIRST_TRADE_DT` | First trade date |
| `LAST_TRADEABLE_DT` | Last trading date |
| `FUT_DLV_DT_FIRST` | First delivery date |
| `FUT_DLV_DT_LAST` | Last delivery date |

**Deliverable Basket**: Not available via API. Use terminal `DLV` function or reconstruct from Treasury issuance dates + contract eligibility rules.

**Test Scripts**: `test_bond_basis.py`, `test_bond_futures_basis.py`

---

### Interest Rate Caps/Floors ❌ TICKER FORMAT UNKNOWN

**LSEG Status**: ⛔ Access Denied (requires Tradeweb/ICAP premium)
**Bloomberg Status**: ❌ Ticker format not yet found

**Tested Patterns (all failed)**:

| Pattern | Example | Result |
|---------|---------|--------|
| `USCP{tenor}A ICAP Curncy` | `USCP5YA ICAP Curncy` | ❌ Unknown Security |
| `USCP{tenor}+{strike} ICAP Curncy` | `USCP5Y+150 ICAP Curncy` | ❌ Unknown Security |
| `EUCP{tenor}A ICAP Curncy` | `EUCP5YA ICAP Curncy` | ❌ Unknown Security |
| `USDSRCAP{tenor} ICAP Curncy` | `USDSRCAP5Y ICAP Curncy` | ❌ Unknown Security |
| `USCPVOL{tenor} BGN Curncy` | `USCPVOL5Y BGN Curncy` | ❌ Unknown Security |

**Note**: Need to use Bloomberg terminal SECF to discover correct ticker format.

---

### Known Working Reference Tickers

These common instruments work and can be used to verify Bloomberg connection:

| Instrument | Bloomberg Ticker | Type | Status |
|------------|-----------------|------|--------|
| IBM | `IBM US Equity` | Equity | ✅ |
| S&P 500 | `SPX Index` | Index | ✅ |
| VIX | `VIX Index` | Vol Index | ✅ |
| US 10Y Yield | `USGG10YR Index` | Govt Yield | ✅ |
| EUR 10Y Swap | `EUSA10 Curncy` | IRS | ✅ |
| SOFR Rate | `SOFRRATE Index` | Rate | ✅ |
| SOFR OIS 1Y | `USOSFR1 Curncy` | OIS | ✅ |

**Note**: `USSW10 Curncy` (USD 10Y Swap) returned no data - may need different source.

---

### Bloomberg API Services

| Service | Purpose | Status |
|---------|---------|--------|
| `//blp/refdata` | Reference data (snapshots) | ✅ Working |
| `//blp/mktdata` | Real-time market data | 🔄 Not tested |
| `//blp/instruments` | Security search (like SECF) | 🔄 Not tested |

---

### Fields Reference

**Common Fields**:
| Field | Description |
|-------|-------------|
| `PX_LAST` | Last price |
| `PX_BID` | Bid price |
| `PX_ASK` | Ask price |
| `NAME` | Security name |
| `LAST_UPDATE` | Last update timestamp |
| `SECURITY_TYP` | Security type |

---

### Scripts Reference

| Script | Purpose | Status |
|--------|---------|--------|
| `test_connection.py` | Test Bloomberg connection | ✅ Working |
| `test_all_instruments.py` | Test all planned instruments | ✅ Working |
| `test_fx_tickers.py` | Debug FX vol ticker formats | ✅ Working |
| `test_fx_vol_v2.py` | Test V-pattern FX vol | ✅ Working |
| `test_swaption_tickers.py` | Test swaption ticker patterns (60+) | ❌ All failed |
| `test_swaption_nvol.py` | Test NVOL/BVOL patterns | ❌ All failed |
| `test_swaption_eusn.py` | Test EUSN pattern from terminal | ❌ All failed |
| `search_securities.py` | Search for tickers (SECF-like) | 🔄 Untested |
| `search_instruments.py` | Search //blp/instruments service | 🔄 Untested |
| `extract_jgb.py` | Extract JGB yields (1Y-40Y) | ✅ Working |
| `extract_fx_vol.py` | Extract FX ATM vol (6 pairs × 8 tenors) | ✅ Working |
| `extract_swaptions.py` | Extract swaption vols | ❌ Needs correct tickers |

---

### JGB Futures 🔄 TO INVESTIGATE

**LSEG Status**: Unknown
**Bloomberg Status**: 🔄 Needs validation

**Expected Tickers** (generic front-month):

| Contract | Ticker | Exchange | Status |
|----------|--------|----------|--------|
| 10Y JGB | `JB1 Comdty` | OSE | 🔄 Untested |
| Mini 10Y JGB | `JBM1 Comdty` | OSE | 🔄 Untested |
| 5Y JGB | `JF1 Comdty` | OSE | 🔄 Untested |

**Specific Contract Pattern**: `{ROOT}{MONTH}{YEAR} Comdty` (e.g., `JBH6 Comdty` = 10Y Mar26)

**Fields Needed**:
| Field | Description |
|-------|-------------|
| `PX_LAST` | Last price |
| `PX_OPEN`, `PX_HIGH`, `PX_LOW` | OHLC |
| `VOLUME` | Volume |
| `OPEN_INT` | Open interest |

**Historical**: Need full history

---

### SOFR Term Rates 🔄 TO INVESTIGATE

**LSEG Status**: Unknown
**Bloomberg Status**: 🔄 Needs validation

**Expected Tickers**:

| Rate | Ticker | Description | Status |
|------|--------|-------------|--------|
| SOFR (daily) | `SOFRRATE Index` | Daily SOFR fixing | ✅ Known working |
| SOFR Term 1M | `TSFR1M Index` | CME Term SOFR 1M | 🔄 Untested |
| SOFR Term 3M | `TSFR3M Index` | CME Term SOFR 3M | 🔄 Untested |
| SOFR Term 6M | `TSFR6M Index` | CME Term SOFR 6M | 🔄 Untested |
| SOFR Term 12M | `TSFR12M Index` | CME Term SOFR 12M | 🔄 Untested |

**Alternative Patterns** (if above fail):
- `USOSFR{tenor} Index` - OIS-implied forward
- `SOFR{tenor} Index` - Simple pattern
- `US0001M Index` - Old LIBOR-style (may map to SOFR now)

**Fields Needed**:
| Field | Description |
|-------|-------------|
| `PX_LAST` | Rate value |
| `LAST_UPDATE` | Timestamp |

**Historical**: Need full history (Term SOFR published since mid-2021)

---

### Next Steps

1. **JGB Futures**: Test `JB1 Comdty` and validate historical data availability
2. **SOFR Term Rates**: Test `TSFR1M/3M/6M/12M Index` patterns
3. **USDJPY FX Options**: Find correct ticker format (not `USDJPY1M25RR`)
4. **Swaption Vols**: Use terminal SECF or `//blp/instruments` to find tickers
5. **Caps/Floors**: Use terminal SECF to find correct ticker format
6. **Validate remaining FX pairs**: GBPUSD, AUDUSD, USDCAD, USDCHF

---

### Comparison: LSEG vs Bloomberg

| Instrument | LSEG RIC | LSEG Status | Bloomberg Ticker | BBG Status |
|------------|----------|-------------|------------------|------------|
| JGB 10Y | `JP10YT=RR` | ⛔ Access Denied | `GJGB10 Index` | ✅ Working |
| FX ATM Vol (EURUSD 1M) | ??? | ⛔ Access Denied | `EURUSDV1M BGN Curncy` | ✅ Working |
| FX ATM Vol (USDJPY 1M) | ??? | ⛔ Access Denied | `USDJPYV1M BGN Curncy` | ✅ Working |
| EUR Swaption 1Yx10Y | `EUR1YX10Y=TTKL` | ⛔ Access Denied | `EUSN0110 BVOL Curncy` (?) | ❌ API not working |
| USD SOFR Cap 5Y | `USDSRCAPATM=ICAP` | ⛔ Access Denied | `???` | ❌ Unknown |
| FX RR/BF | ??? | ⛔ Access Denied | Various patterns | ❌ Returns wrong data |

---

### Summary: What Works

| Category | Status | Data Points | Pattern |
|----------|--------|-------------|---------|
| **JGB Yields** | ✅ Working | 6-15 tenors | `GJGB{tenor} Index` |
| **FX ATM Vol** | ✅ Working | 48 (6 pairs × 8 tenors) | `{PAIR}V{TENOR} BGN Curncy` |
| **Treasury Futures** | ✅ Working | 6 contracts | `TY1 Comdty` etc. |
| **JGB Futures** | 🔄 To test | 3 contracts | `JB1 Comdty` etc. |
| **SOFR Term Rates** | 🔄 To test | 4 tenors | `TSFR{tenor} Index` |
| **Swaption Vol** | ❌ Not via API | Terminal only | `EUSN0110 BVOL Curncy` (?) |
| **Caps/Floors** | ❌ Unknown | - | Need to discover |
| **FX RR/BF** | ❌ Wrong data | - | Tickers exist but return ATM |

---
