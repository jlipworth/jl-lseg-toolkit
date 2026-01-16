# LSEG Data - Permission Restrictions and Missing Instruments

This document tracks RICs and instruments that cannot be pulled from LSEG due to permissions issues.

## Government Bond Yields

### Japanese Government Bonds (JGBs)

| RIC | Description | Status |
|-----|-------------|--------|
| `JP2YT=RR` | 2Y JGB Yield | Access Denied |
| `JP5YT=RR` | 5Y JGB Yield | Access Denied |
| `JP10YT=RR` | 10Y JGB Yield | Access Denied |
| `JP30YT=RR` | 30Y JGB Yield | Access Denied |

**Issue**: Requires JGB data package

**Workaround**: JGB futures (`JGBc1`) and JPY OIS/IRS work. Derive yield information from futures contracts.

### US Treasury Yields - RIC Pattern Issue

| RIC Pattern | Status | Workaround |
|-------------|--------|------------|
| `US{tenor}T=RR` | Access Denied | Use `=RRPS` suffix |
| `US1YT=RRPS` | Working | All tenors (1M-30Y) available |

## Bond Basis and Invoice Chain

| RIC | Description | Status |
|-----|-------------|--------|
| `0#TY=INV` | Invoice price chain for Treasury futures | Access Denied |
| `TBEA` | Contributor-specific | Access Denied |
| `BGCP` | Contributor-specific | Access Denied |

**Note**: Other bond basis data (CTD, deliverable basket) works fine; only the invoice chain is restricted.

## Repo Rates and Money Market Rates

| RIC | Description | Status |
|-----|-------------|--------|
| `USONFFE=` | Fed Funds Effective | Not available in testing |
| `TGCR=` | Treasury repo tri-party rate | Not available |
| `BGCR=` | Broad GC Rate | Not available |
| `CABOCR=ECI` | Bank of Canada rate | Requires ECI permissions |

## Interest Rate Options - Swaptions

| RIC | Description | Status |
|-----|-------------|--------|
| `EUR1YX10Y=TTKL` | EUR 1Yx10Y Swaption | Access Denied |
| `EUR5YX5Y=TTKL` | EUR 5Yx5Y Swaption | Access Denied |
| `GBP1YX10Y=TTKL` | GBP 1Yx10Y Swaption | Access Denied |
| `USD1YX10Y=TTKL` | USD 1Yx10Y Swaption | Not found |

**Issue**: Requires Tradeweb premium subscription (`=TTKL` suffix)

## Interest Rate Caps & Floors

### USD SOFR Caps/Floors

| RIC | Description | Status |
|-----|-------------|--------|
| `USDSRCAPATM=TRDL` | USD SOFR ATM Caps (Tradeweb) | Access Denied |
| `USDSRCAPATM=ICAP` | USD SOFR ATM Caps (ICAP) | Access Denied |
| `USDSRCAPV=TRDL` | USD SOFR Positive Caps | Access Denied |
| `USD5YSRCP150=FMD` | 5Y +1.50% Cap (FMD) | Access Denied |
| `USD5YSRCN250=FMD` | 5Y -2.50% Cap (FMD) | Access Denied |

### EUR ESTR Caps/Floors

| RIC | Description | Status |
|-----|-------------|--------|
| `EURESCAPATM=TRDL` | EUR ESTR ATM Caps | Access Denied |
| `EURESCAPV=FMD` | EUR ESTR Positive Caps | Access Denied |
| `EU3Y6LATM=ICAP` | Euro 3Y ATM Cap/Floor | Access Denied |
| `EU5Y6LATM=ICAP` | Euro 5Y ATM Cap/Floor | Access Denied |

**Issue**: Requires Tradeweb or ICAP premium subscription

## FX Options - Risk Reversals & Butterflies

| RIC | Description | Status |
|-----|-------------|--------|
| `EURRR25=` | EUR/USD 25D Risk Reversal | Access Denied |
| `EURBF25=` | EUR/USD 25D Butterfly | Access Denied |

**Issue**: Premium data - pattern applies across all currency pairs

**Note**: Standard ATM volatility is available; risk reversals/butterflies are restricted.

## Equity Volatility Indices

| RIC | Description | Status |
|-----|-------------|--------|
| `.VXN` | Nasdaq Volatility Index | No data |
| `.RVX` | Russell Volatility Index | No data |
| `.OVX` | Oil Volatility Index | No data |
| `.GVZ` | Gold Volatility Index | No data |

**Note**: Core indices work (`.VIX`, `.VXD`, `.VVIX`)

## Credit Spreads

| RIC | Description | Status |
|-----|-------------|--------|
| `.BBXTUICU` | BBVA US/EU IG Credit Spread | Access Denied |

**Note**: Other credit spread indices from S&P work but have limited data.

---

## Permission Restriction Patterns

### Data Package Requirements (Highest Tier)
- JGB data package
- Specific country/regional data packages

### Contributor-Specific Premium Sources
- Tradeweb data (`=TTKL`, `=TRDL`)
- ICAP data (`=ICAP`)
- FMD data (`=FMD`)

### RIC Suffix Issues
- US Treasuries: `=RR` fails, use `=RRPS`
- Invoice chains require special permissions

### Data Tier Restrictions
- Premium volatility products
- Advanced option analytics (risk reversals, butterflies)
- Premium credit indices

---

## Working Workarounds

| Problem | Solution |
|---------|----------|
| JGB Yields | Use JGB futures and derivative instruments |
| US Treasury Yields | Switch from `=RR` to `=RRPS` suffix |
| Swaptions | Consider alternative instruments or upgrade subscription |
| Premium Vol Products | Use standard ATM volatility instead of advanced Greeks |
