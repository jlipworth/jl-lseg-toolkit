# LSEG Timeseries Data Validation Results

> **Note:** This document contains raw validation results from development.
> For the consolidated instrument list, see [INSTRUMENTS.md](../INSTRUMENTS.md).

Validation run: 2026-01-06

## Summary (Updated 2026-01-06)

**Phase 2 Validation Complete:**
- **USD Treasury Yields:** 11/11 (100%) - all tenors with `=RRPS` pattern
- **USD OIS Curve:** 14/14 (100%) - all tenors with bare `=` pattern
- **SOFR Fixings:** 2/6 (33%) - daily and 30-day avg
- **Treasury Repo:** 8/10 (80%) - ON through 6M
- **USD FRAs:** 12/12 (100%) - all standard tenors
- **USD Deposits:** 9/9 (100%) - ON through 1Y
- **STIR Futures:** 6/14 (43%) - SRAc1, FFc1, FEIc1, SONc1

**Total Working RICs:** 62+

## Working RICs by Asset Class

### Bond Futures ✓ (6/11)

| RIC | Description | Daily | Hourly | Minute | Notes |
|-----|-------------|-------|--------|--------|-------|
| `TYc1` | US 10Y continuous | ✓ | ✗ | ✗ | Use TY, not ZN |
| `USc1` | US 30Y continuous | ✓ | ✗ | ✗ | Use US, not ZB |
| `TUc1` | US 2Y continuous | ✓ | ✗ | ✗ | |
| `FGBLc1` | Euro-Bund 10Y | ✓ | ✗ | ✗ | |
| `FGBMc1` | Euro-Bobl 5Y | ✓ | ✗ | ✗ | |
| `FGBSc1` | Euro-Schatz 2Y | ✓ | ✗ | ✗ | |

**Not Working:**
- `ZNc1` - CME symbol, use `TYc1` instead
- `JBc1` - JGB 10Y not available
- `TYH5` - Discrete contracts not in historical data
- `TYH1^2`, `FGBLH1^2` - Expired contracts not accessible

### FX Spot ✓ (8/8)

| RIC | Description | Daily | Hourly | Minute |
|-----|-------------|-------|--------|--------|
| `EUR=` | EUR/USD | ✓ | ✗ | ✗ |
| `GBP=` | GBP/USD | ✓ | ✗ | ✗ |
| `JPY=` | USD/JPY | ✓ | ✗ | ✗ |
| `CHF=` | USD/CHF | ✓ | ✗ | ✗ |
| `AUD=` | AUD/USD | ✓ | ✗ | ✗ |
| `CAD=` | USD/CAD | ✓ | ✗ | ✗ |
| `EURGBP=` | EUR/GBP | ✓ | ✗ | ✗ |
| `EURJPY=` | EUR/JPY | ✓ | ✗ | ✗ |

### FX Forwards ✓ (6/6)

| RIC | Description | Daily |
|-----|-------------|-------|
| `EUR1M=` | EUR/USD 1M fwd | ✓ |
| `EUR3M=` | EUR/USD 3M fwd | ✓ |
| `EUR6M=` | EUR/USD 6M fwd | ✓ |
| `EUR1Y=` | EUR/USD 1Y fwd | ✓ |
| `GBP1M=` | GBP/USD 1M fwd | ✓ |
| `JPY1M=` | USD/JPY 1M fwd | ✓ |

### USD OIS Curve ✓ (14/14) - UPDATED 2026-01-06

All tenors work with bare `USD{tenor}OIS=` pattern for both snapshot and history.

| RIC | Description | Daily | Fields | Notes |
|-----|-------------|-------|--------|-------|
| `USD1MOIS=` | 1-Month OIS | ✓ | 7 | BID/ASK + meta |
| `USD2MOIS=` | 2-Month OIS | ✓ | 7 | |
| `USD3MOIS=` | 3-Month OIS | ✓ | 7 | |
| `USD6MOIS=` | 6-Month OIS | ✓ | 7 | |
| `USD9MOIS=` | 9-Month OIS | ✓ | 7 | |
| `USD1YOIS=` | 1-Year OIS | ✓ | 7 | |
| `USD2YOIS=` | 2-Year OIS | ✓ | 7 | |
| `USD3YOIS=` | 3-Year OIS | ✓ | 7 | |
| `USD5YOIS=` | 5-Year OIS | ✓ | 7 | |
| `USD7YOIS=` | 7-Year OIS | ✓ | 7 | |
| `USD10YOIS=` | 10-Year OIS | ✓ | 7 | |
| `USD15YOIS=` | 15-Year OIS | ✓ | 7 | |
| `USD20YOIS=` | 20-Year OIS | ✓ | 7 | |
| `USD30YOIS=` | 30-Year OIS | ✓ | 7 | |

**Available Fields:**
- Rates: `BID`, `ASK`, `HST_CLOSE`, `PRIMACT_1`
- Meta: `VALUE_TS1`, `VALUE_DT1`, `CF_NAME`, `DSPLY_NAME`, `CURRENCY`, `CF_CURR`

**Not Working:**
- `=TREU`, `=ICAP` contributor suffixes - Access Denied
- `USDSOFR{tenor}=` pattern - Record not found

### SOFR Fixings ✓ (2/6)

| RIC | Description | Daily | Fields |
|-----|-------------|-------|--------|
| `USDSOFR=` | Daily SOFR fixing | ✓ | 3 |
| `SOFR1MAVG=` | 30-day compounded SOFR | ✓ | 3 |

**Fields:** `PRIMACT_1`, `VALUE_DT1`, `VALUE_TS1`

**Not Found:**
- `SOFR90DAVG=`, `SOFR180DAVG=`, `USDSOFRAVE=`, `USSOFRFIX=`

### US Treasury Yields ✓ (11/11) - UPDATED 2026-01-06

All tenors work with `=RRPS` pattern for both snapshot and history.

| RIC | Description | Daily | Fields | Notes |
|-----|-------------|-------|--------|-------|
| `US1MT=RRPS` | 1-Month T-Bill | ✓ | 10 | Full yield + risk metrics |
| `US3MT=RRPS` | 3-Month T-Bill | ✓ | 10 | Full yield + risk metrics |
| `US6MT=RRPS` | 6-Month T-Bill | ✓ | 10 | Full yield + risk metrics |
| `US1YT=RRPS` | 1-Year | ✓ | 10 | Full yield + risk metrics |
| `US2YT=RRPS` | 2-Year | ✓ | 10 | Full yield + risk metrics |
| `US3YT=RRPS` | 3-Year | ✓ | 10 | Full yield + risk metrics |
| `US5YT=RRPS` | 5-Year | ✓ | 10 | Full yield + risk metrics |
| `US7YT=RRPS` | 7-Year | ✓ | 10 | Full yield + risk metrics |
| `US10YT=RRPS` | 10-Year | ✓ | 10 | Full yield + risk metrics |
| `US20YT=RRPS` | 20-Year | ✓ | 10 | Full yield + risk metrics |
| `US30YT=RRPS` | 30-Year | ✓ | 10 | Full yield + risk metrics |

**Available Fields (=RRPS pattern):**
- Yields: `MID_YLD_1`, `SEC_YLD_1`
- Prices: `BID`, `ASK`, `HIGH_1`, `LOW_1`, `OPEN_PRC`, `HST_CLOSE`, `PRIMACT_1`
- Risk: `MOD_DURTN`, `BPV`, `DURATION`, `CONVEXITY`
- Meta: `VALUE_TS1`, `VALUE_DT1`, `CF_NAME`, `DSPLY_NAME`, `CURRENCY`

**Alternative Patterns:**
- `=X` pattern (e.g., `US10YT=X`): Works for snapshot + history, fewer fields (no MID_YLD_1, no risk metrics)
- `=RR` pattern: Works for snapshot only, no history
- Bare `=` pattern: Not found

### European Government Bond Yields ✓ (4/4)

| RIC | Description | Daily | Notes |
|-----|-------------|-------|-------|
| `DE10YT=RR` | German 10Y | ✓ | |
| `DE5YT=RR` | German 5Y | ✓ | |
| `DE2YT=RR` | German 2Y | ✓ | |
| `GB10YT=RR` | UK 10Y Gilt | ✓ | |

**Not Tested:**
- `JP10YT=RR` - Japan 10Y

## Key Findings

### 1. No Intraday Data Available
All tested RICs only return daily data. Hourly and minute intervals return empty results.

### 2. Use LSEG RICs, Not CME Symbols
| CME Symbol | LSEG RIC |
|------------|----------|
| ZN | TY |
| ZB | US |
| ZF | FV |
| ZT | TU |

### 3. Expired Contracts Not Accessible
The `^2` suffix for expired contracts (e.g., `TYH1^2`) does not return historical data.

### 4. Discrete Contract RICs
Current discrete contracts (e.g., `TYH5` for Mar 2025) may not be accessible for historical time series.

### 5. OIS RIC Pattern
Only `USD1MOIS=` works. Other patterns like `USDSOFR1M=` do not exist.

### 6. US Treasury Yields Work with =RRPS Pattern
`US{tenor}T=RRPS` pattern works for all tenors (1M to 30Y) with full yield and risk metrics.
The `=RR` pattern only works for snapshots, not historical data.

## Fields Discovered

### Futures Fields
- `TRDPRC_1` - Last traded price
- `OPEN_PRC` - Opening price
- `HIGH_1` - Daily high
- `LOW_1` - Daily low
- `SETTLE` - Settlement price
- `ACVOL_UNS` - Volume (unsigned)
- `OPINT_1` - Open interest

### FX Fields
- `BID`, `ASK` - Bid/ask prices
- `BID_HIGH_1`, `BID_LOW_1` - Daily high/low
- `MID_PRICE` - Mid price

### Bond Yield Fields
- `B_YLD_1` - Bid yield
- `A_YLD_1` - Ask yield
- `MID_YLD_1` - Mid yield
- `MOD_DURTN` - Modified duration
- `BPV` - Basis point value

## Recommendations for Implementation

1. **Focus on daily data only** - No intraday support
2. **Use LSEG RIC roots** - Map CME symbols to LSEG
3. **Skip expired contracts** - Not accessible via get_history
4. **OIS** - Need to validate full curve (currently only USD1MOIS= confirmed)
5. **US Treasury Yields** - Use `=RRPS` pattern for all tenors (1M-30Y)
