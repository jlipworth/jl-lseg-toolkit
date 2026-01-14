## Options (Validated 2026-01-06)


**Key Finding**: Options ARE available with correct RIC patterns! Three pattern families exist.

### OPRA Equity Options (US Exchanges) ✅

**Pattern**: `{ROOT}{month}{DD}{YY}{strike*100}.U`

**Month Codes**:
- Calls: A=Jan, B=Feb, C=Mar, D=Apr, E=May, F=Jun, G=Jul, H=Aug, I=Sep, J=Oct, K=Nov, L=Dec
- Puts: M=Jan, N=Feb, O=Mar, P=Apr, Q=May, R=Jun, S=Jul, T=Aug, U=Sep, V=Oct, W=Nov, X=Dec

| Instrument | Example RIC | Description | Status |
|------------|-------------|-------------|--------|
| SPX Options | `SPXo202660000.U` | SPX Mar 20 2026 $6000 Put | ✅ |
| SPX Weekly | `SPXWm062669200.U` | SPXW Jan 6 2026 $6920 Put | ✅ |
| VIX Options | `VIXA212601500.U` | VIX Jan 21 2026 $15 Call | ✅ |
| AAPL Options | `AAPLA092624000.U` | AAPL Jan 9 2026 $240 Call | ✅ |
| QQQ Options | `0#QQQ*.U` | Chain - 7,761 options | ✅ |

**Chain Patterns**:
- `0#SPX*.U` - 9,157 SPX options
- `0#VIX*.U` - 1,121 VIX options
- `0#AAPL*.U` - 2,773 AAPL options
- `0#XSP*.U` - 13,443 Mini-SPX options

### CME Futures Options ✅

**Pattern**: `{ROOT}{strike}{month}{YY}`

**Month Codes** (same as OPRA): A-L = Calls (Jan-Dec), M-X = Puts (Jan-Dec)

| Instrument | Example RIC | Description | Status |
|------------|-------------|-------------|--------|
| E-mini S&P 500 | `ES6000C26` | ES 6000 Mar26 Call | ✅ |
| E-mini S&P 500 | `ES6000O26` | ES 6000 Mar26 Put | ✅ |
| E-mini Nasdaq | `NQ22000C26` | NQ 22000 Mar26 Call | ✅ |
| 10Y T-Note | `TY111O26` | TY 111 Mar26 Put | ✅ |
| 10Y T-Note | `TY114C26` | TY 114 Mar26 Call | ✅ |
| 30Y T-Bond | `US+` | Chain available | ✅ |
| 5Y T-Note | `FV+` | Chain available | ✅ |
| 2Y T-Note | `TU+` | Chain available | ✅ |

**Chain Patterns**:
- `0#TY+` - 10Y T-Note options by expiry
- `0#US+` - 30Y T-Bond options by expiry
- `0#FV+` - 5Y T-Note options by expiry
- `0#TU+` - 2Y T-Note options by expiry

### NYMEX/COMEX Commodity Options ✅

**Crude Oil Pattern**: `CL{strike*10}{month}{YY}` (strike 70 = 700 in RIC)
**Gold Pattern**: `GC{strike}{month}{YY}`

| Instrument | Example RIC | Description | Status |
|------------|-------------|-------------|--------|
| WTI Crude | `CL700O26` | CL $70 Mar26 Put | ✅ |
| WTI Crude | `CL750C26` | CL $75 Mar26 Call | ✅ |
| Gold | `GC2600D26` | GC $2600 Apr26 Call | ✅ |
| Gold | `GC2700P26` | GC $2700 Apr26 Put | ✅ |

**Chain Patterns**:
- `0#CL+` - 84 crude oil option expiries
- `0#GC+` - 31 gold option expiries
- `0#NG+` - 48 natural gas option expiries

### STIR Options (Working)

| Instrument | LSEG RIC | Status | Notes |
|------------|----------|--------|-------|
| VIX Index | `.VIX` | ✅ | VIX spot index |
| Euribor Options | `0#FEI:` | ✅ | STIR options chain |
| SONIA Options | `0#SON:` | ✅ | GBP STIR options |

### European Index Options (Validated 2026-01-06) ✅

**Euro Stoxx 50 Options**

**Pattern**: `STXE{strike}{month}{YY}.EX`

| Instrument | Example RIC | Description | Status |
|------------|-------------|-------------|--------|
| Euro Stoxx 50 | `STXE56500M6.EX` | 5650 Jan26 Put | ✅ |
| Euro Stoxx 50 | `STXE57500A6.EX` | 5750 Jan26 Call | ✅ |
| Chain | `0#STXEEOM*.EX` | All monthly options | ✅ |

**DAX Options**

**Pattern**: `GDAX{week}W{strike}{month}{YY}.EX` (weekly) or `ODAX{strike}{month}{YY}.EX` (monthly)

| Instrument | Example RIC | Description | Status |
|------------|-------------|-------------|--------|
| DAX Weekly | `GDAX2W244000M6.EX` | 24400 2nd Fri Jan26 | ✅ |
| DAX Monthly | `ODAX{strike}{month}{YY}.EX` | Monthly options | 🔄 |

### European Bond Futures Options (Eurex) - Validated 2026-01-06 ✅

**Bund Options**

**Pattern**: `OGBL{strike}{month}{YY}` (C=Call, O=Put month codes same as US)

| Instrument | Example RIC | Description | Status |
|------------|-------------|-------------|--------|
| Bund 127 Put | `OGBL1270O6` | Mar26 127 Put | ✅ |
| Bund 130 Call | `OGBL1300C6` | Mar26 130 Call | ✅ |
| Chain | `0#OGBL+` | All Bund options | ✅ |

**Bobl/Schatz Options**

| Instrument | Symbol | LSEG RIC Pattern | Status | Notes |
|------------|--------|------------------|--------|-------|
| Bobl Options | OGBM | `OGBM{strike}{month}{YY}` | 🔄 | Needs validation |
| Schatz Options | OGBS | `OGBS{strike}{month}{YY}` | 🔄 | Needs validation |

### FX Options (Needs Research)

| Pair | Exchange | LSEG RIC Pattern | Status | Notes |
|------|----------|------------------|--------|-------|
| EUR/USD Options | CME | `URO{strike}{month}{YY}` | ❓ | Options on 6E futures |
| GBP/USD Options | CME | `BP{strike}{month}{YY}` | ❓ | Options on 6B futures |
| JPY/USD Options | CME | `JY{strike}{month}{YY}` | ❓ | Options on 6J futures |

### Swaptions (Options on Interest Rate Swaps) - Validated 2026-01-06

**Pattern Found**: `{CCY}{expiry}X{tenor}=TTKL`
**Status**: Access Denied - requires higher data tier (Tradeweb subscription)

| Instrument | LSEG RIC Pattern | Status | Notes |
|------------|------------------|--------|-------|
| EUR 1Yx10Y Swaption | `EUR1YX10Y=TTKL` | ⛔ | Access Denied |
| EUR 5Yx5Y Swaption | `EUR5YX5Y=TTKL` | ⛔ | Access Denied |
| GBP 1Yx10Y Swaption | `GBP1YX10Y=TTKL` | ⛔ | Access Denied |
| USD 1Yx10Y Swaption | `USD1YX10Y=TTKL` | ❌ | Not found |

**Note**: The `=TTKL` suffix indicates Tradeweb data. Swaptions require a premium data subscription.

**Alternative Patterns Tested (all failed):**
- `{CCY}{expiry}x{tenor}PAY=` - Not found
- `{CCY}{expiry}x{tenor}REC=` - Not found
- `{CCY}SWPTN{expiry}x{tenor}=` - Not found
- `{CCY}{expiry}X{tenor}SWPTNVOL=` - Not found

**Swaption Tenors (Standard Grid):**
- Expiries: 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y
- Underlying swaps: 2Y, 5Y, 10Y, 30Y
- Standard grid: 1Yx10Y (1-year option into 10-year swap)

### Swaption Volatility Surface

| Data | LSEG RIC Pattern | Status | Notes |
|------|------------------|--------|-------|
| USD Swaption Vol Grid | `USDSWPTVOL{exp}x{tenor}=` | ❓ | ATM normal vol |
| USD Swaption Cube | Vol surface + skew | ❓ | Requires 3D structure |
| EUR Swaption Vol Grid | `EURSWPTVOL{exp}x{tenor}=` | ❓ | ATM normal vol |

### Options on Swap Spreads

| Instrument | Description | LSEG RIC Pattern | Status | Notes |
|------------|-------------|------------------|--------|-------|
| Swap Spread Options | Options on spread | ❓ | ❓ | OTC, may not have RICs |

**Note**: Options on swap spreads are typically OTC instruments and may not have direct RIC coverage. These are often constructed synthetically from swaptions and Treasury futures options.

### Interest Rate Caps & Floors (Validated 2026-01-06)

**Status**: ⛔ RICs exist but require **premium subscription** (Access Denied)

#### USD SOFR Caps/Floors

| RIC Pattern | Description | Status |
|-------------|-------------|--------|
| `USDSRCAPATM=TRDL` | USD SOFR ATM Caps (Tradeweb) | ⛔ Access Denied |
| `USDSRCAPATM=ICAP` | USD SOFR ATM Caps (ICAP) | ⛔ Access Denied |
| `USDSRCAPV=TRDL` | USD SOFR Positive Caps | ⛔ Access Denied |
| `USD5YSRCP150=FMD` | 5Y +1.50% Cap (FMD) | ⛔ Access Denied |
| `USD5YSRCN250=FMD` | 5Y -2.50% Cap (FMD) | ⛔ Access Denied |

#### EUR ESTR Caps/Floors

| RIC Pattern | Description | Status |
|-------------|-------------|--------|
| `EURESCAPATM=TRDL` | EUR ESTR ATM Caps | ⛔ Access Denied |
| `EURESCAPV=FMD` | EUR ESTR Positive Caps | ⛔ Access Denied |
| `EU3Y6LATM=ICAP` | Euro 3Y ATM Cap/Floor | ⛔ Access Denied |
| `EU5Y6LATM=ICAP` | Euro 5Y ATM Cap/Floor | ⛔ Access Denied |

**Note**: Cap/floor data requires Tradeweb or ICAP premium subscription.

### Commodity Options (Validated 2026-01-06) ✅

**Pattern**: `{ROOT}{strike}{month}{YY}` (same as CME futures options)

| Instrument | Example RIC | Description | Status | History |
|------------|-------------|-------------|--------|---------|
| WTI Crude | `CL700O26` | $70 Mar26 Put | ✅ | ✅ |
| WTI Crude | `CL750C26` | $75 Mar26 Call | ✅ | ✅ |
| Gold | `GC2600D26` | $2600 Apr26 Call | ✅ | ✅ |
| Gold | `GC2700P26` | $2700 Apr26 Put | ✅ | ✅ |

**Note**: Crude oil strike in RIC = strike * 10 (e.g., $70 = 700)

**Chains**: `0#CL+` (84), `0#GC+` (31), `0#NG+` (48)

### Options Chain RIC Patterns

| Type | Pattern | Example | Notes |
|------|---------|---------|-------|
| All options for contract | `0#{root}{M}{Y}*=` | `0#TYH5*=` | All TY Mar 2025 options |
| All calls | `0#{root}{M}{Y}C*=` | `0#TYH5C*=` | All TY Mar 2025 calls |
| All puts | `0#{root}{M}{Y}P*=` | `0#TYH5P*=` | All TY Mar 2025 puts |
| Option chain | `0#{root}=O` | `0#TYc1=O` | Front month options chain |

### Options Fields to Research

| Field | Description | Status |
|-------|-------------|--------|
| `TRDPRC_1` | Last traded price | ❓ |
| `BID` / `ASK` | Bid/ask prices | ❓ |
| `STRIKE_PRC` | Strike price | ❓ |
| `EXPIRY_DATE` | Expiration date | ❓ |
| `IMP_VOLT` | Implied volatility | ❓ |
| `DELTA` | Delta | ❓ |
| `GAMMA` | Gamma | ❓ |
| `THETA` | Theta | ❓ |
| `VEGA` | Vega | ❓ |
| `RHO` | Rho | ❓ |
| `OPINT_1` | Open interest | ❓ |
| `ACVOL_UNS` | Volume | ❓ |

### Options Validation Priority

1. **Bond Futures Options** (CME) - TY, US options (for bond basis hedging)
2. **STIR Futures Options** (CME) - SOFR options (rate vol exposure)
3. **Swaptions** - USD swaption volatility surface
4. **FX Options** - EUR/USD options (FX vol)
5. **Equity Index Options** - SPX, VIX (vol products)
6. **Commodity Options** - CL, GC (energy/metals)

---
