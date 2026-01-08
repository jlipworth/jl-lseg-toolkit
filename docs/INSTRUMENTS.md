# Instruments Support List

Reference document for supported instruments and roadmap.

**Legend**: ✅ Validated | 🔄 Planned | ❓ Needs Research | ❌ Not Available

---

## Data Granularity & Historical Depth (Validated 2026-01-06)

### Time Intervals Available

| Interval | Status | Notes |
|----------|--------|-------|
| Tick | ✅ | Most liquid instruments |
| Minute (1min) | ✅ | ~60 days lookback (50,000 bars) |
| 5min | ✅ | ~257 days lookback |
| 10min | ✅ | ~365 days lookback |
| 30min | ✅ | ~365 days lookback |
| 60min/Hourly | ✅ | ~365 days lookback |
| Daily | ✅ | Full history (5-36 years) |
| Weekly | ✅ | Full history |
| Monthly | ✅ | Full history |
| Quarterly | ✅ | Full history |
| Yearly | ✅ | Full history |

**Important**: Use `count` parameter for intraday data, not `start`/`end` dates:
```python
# ✅ Correct - use count for intraday
df = rd.get_history('TYc1', interval='minute', count=1000)

# ❌ Wrong - date range returns empty for intraday
df = rd.get_history('TYc1', interval='minute', start='2024-01-01', end='2024-01-02')
```

**Query Limits**: Maximum 50,000 bars per request. For longer history, split into multiple queries:
```python
# For >50,000 bars, paginate backwards from most recent
batch1 = rd.get_history(ric, interval='minute', count=50000)
# Then use batch1.index[0] as end point for next batch
```

### Intraday RIC Pattern Notes

Some instruments require specific RIC suffixes for intraday data:

| Asset Class | Daily RIC | Intraday RIC | Notes |
|-------------|-----------|--------------|-------|
| US Treasury Yields | `US10YT=RR` | `US10YT=RRPS` | Use `=RRPS` suffix |
| EUR OIS | `EUR1YOIS=` ❌ | `EUREST1Y=` | Use `EUREST{tenor}=` pattern |
| Other OIS | `USD1YOIS=` | Same | Default pattern works |

### Intraday Support by Asset Class

| Asset Class | Tick | Minute | Notes |
|-------------|------|--------|-------|
| **Bond Futures** | ✅ 100% | ✅ 100% | All US/EU/Asia futures |
| **Index Futures** | ✅ 100% | ✅ 100% | ES, NQ, STXE, FDX, etc. |
| **FX Spot** | ✅ 100% | ✅ 100% | G10 + EM (KRW=, INR=, BRL= confirmed) |
| **Commodities** | ✅ 100% | ✅ 100% | Energy, Metals, Grains |
| **Precious Metals Spot** | ✅ 100% | ✅ 100% | XAU=, XAG= |
| **Crypto** | ✅ 100% | ✅ 100% | BTC= |
| **Currency Index** | ✅ 100% | ✅ 100% | .DXY, DXYc1 |
| **VIX** | ✅ 100% | ✅ 100% | .VIX (index), VXc1 (futures) |
| **STIR Futures** | ✅ 100% | ✅ 100% | SOFR, FF, Euribor |
| **FX Forwards** | ✅ 100% | ✅ 100% | All tenors |
| **FX Volatility** | ❌ | ❌ | Daily only (EURUSDATMVOL1M=) |
| **Govt Yields** | ✅ 100% | ✅ 100% | US: use `=RRPS` suffix (not `=RR`) |
| **OIS Rates** | ✅ 100% | ✅ 100% | All G10 currencies work |
| **IRS (Swaps)** | ✅ 100% | ✅ 100% | USDIRS10Y=, EURIRS10Y=, etc. |
| **FRAs** | ✅ 100% | ✅ 100% | USD1X4F=, USD3X6F= |
| **Money Market** | ✅ 100% | ✅ 100% | USD1MD=, USD3MD= |
| **Repo Rates** | ✅ 100% | ✅ 100% | USONRP=, US3MRP= |
| **Equities** | ✅ 100% | ✅ 100% | US, UK, EU, Asia |
| **ETFs** | ✅ 100% | ✅ 100% | SPY.P, QQQ.O |
| **Equity Indices** | ✅ 100% | ✅ 100% | .SPX, .DJI, .FTSE, .GDAXI |
| **Calendar Spreads** | ✅ 100% | ✅ 100% | CLc1-CLc2 syntax works |
| **Overnight Fixings** | ❌ | ❌ | SOFR, ESTR, SONIA - daily only |
| **EURIBOR Fixings** | ❌ | ❌ | EURIBOR3MD= - daily only |
| **CDS Indices** | ❌ | ❌ | IBOXIG05=MP - daily only |
| **Options** | ❌ | ❌ | Individual options - daily only |
| **Swaptions** | ❌ | ❌ | USDSWPTN1Y5YATM= - daily only |
| **Caps/Floors** | ❌ | ❌ | Interest rate caps - daily only |
| **Corporate Bonds** | ❌ | ❌ | Individual bonds - daily only |
| **OAS/Spreads** | ❌ | ❌ | Credit spreads - daily only |
| **NDFs (Contracts)** | ❌ | ❌ | NDF contracts - use FX spot instead |

### Historical Data Depth

**Daily Data (Full History)**:

| Asset Class | Example RIC | History Start | Years | Rows |
|-------------|-------------|---------------|-------|------|
| **Bond Futures** | `TYc1` | 1990-01-02 | 36 | 9,091 |
| **Index Futures** | `ESc1` | 1997-09-09 | 28 | 7,136 |
| **FX Spot** | `EUR=` | 1990-01-02 | 36 | 9,384 |
| **Commodities** | `CLc1` | 1990-01-02 | 36 | 9,085 |
| **Currency Index** | `.DXY` | 1990-01-02 | 36 | 9,324 |
| **Govt Yields** | `DE10YT=RR` | 1990-01-02 | 36 | 9,541 |
| **OIS Rates** | `USD1YOIS=` | 2001-08-09 | 24 | 6,268 |
| **SOFR Fixing** | `USDSOFR=` | 2014-08-22 | 11 | 2,834 |

**Intraday Data Depth**:

| Interval | Max Bars | Approx Lookback |
|----------|----------|-----------------|
| Minute | 50,000 | ~60 days |
| 5min | 50,000 | ~257 days |
| 30min | 12,500 | ~365 days |
| 60min | 6,400 | ~365 days |

### Real-Time Snapshots

Real-time snapshot data (bid/ask/last with timestamps) is available via `rd.get_data()`:

```python
df = rd.get_data('TYc1', fields=['BID', 'ASK', 'TRDPRC_1', 'TRDTIM_1'])
```

### Timezone Convention (Validated 2026-01-07)

**All LSEG timestamps are in UTC** (timezone-naive). The API returns `DatetimeIndex` without timezone info, but all times are UTC.

#### Verification

| Exchange | Local Hours | UTC Hours | Data Matches |
|----------|-------------|-----------|--------------|
| **NYSE/NASDAQ** | 9:30-16:00 ET | 14:30-21:00 | ✅ Hours 14-21 in data |
| **LSE** | 8:00-16:30 GMT | 08:00-16:30 | ✅ Hours 8-17 in data |
| **Tokyo (TSE)** | 9:00-15:00 JST | 00:00-06:00 | ✅ Hours 0-6 in data |
| **Xetra (DAX)** | 9:00-17:30 CET | 08:00-16:30 | ✅ Hours 8-16 in data |
| **CME Globex** | 17:00-16:00 CT | 23:00-22:00 | ✅ 23hr coverage |

#### Working with Timezones

```python
import pytz

# LSEG data comes as timezone-naive UTC
df = rd.get_history('AAPL.O', interval='minute', count=100)

# Localize to UTC (makes timezone-aware)
df.index = df.index.tz_localize('UTC')

# Convert to local timezone
df.index = df.index.tz_convert('America/New_York')
```

#### Daily Data

Daily data uses midnight timestamps (00:00:00) representing the **trade date**:
- For equities: the exchange trading day
- For futures: the pit session date
- For FX/rates: the fixing date
- Settlement date (T+n) is not reflected in the timestamp

#### Extended Hours Data

For US equities, intraday data includes pre-market and after-hours trading:
- Pre-market: 04:00-09:30 ET (09:00-14:30 UTC)
- Regular: 09:30-16:00 ET (14:30-21:00 UTC)
- After-hours: 16:00-20:00 ET (21:00-01:00 UTC)

#### Storage Recommendations

| Storage | Format | Notes |
|---------|--------|-------|
| **Database** | Store as UTC | Use `TIMESTAMP` type |
| **Parquet** | Store as UTC | Use `timestamp[us, tz=UTC]` |
| **Display** | Convert to local | Apply timezone on query |

---

## Symbol Mapping: CME → LSEG

### Treasury Futures (Complete Curve) - All 8 Validated

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| ZT | TU | 2-Year T-Note Future |
| Z3N | YR | 3-Year T-Note Future |
| ZF | FV | 5-Year T-Note Future |
| ZN | TY | 10-Year T-Note Future |
| TN | TN | Ultra 10-Year T-Note |
| TWE | ZP | 20-Year T-Bond Future |
| ZB | US | 30-Year T-Bond Future |
| UB | AUL | Ultra 30-Year T-Bond |

### Index Futures

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| ES | ES | E-mini S&P 500 |
| NQ | NQ | E-mini Nasdaq-100 |
| RTY | RTY | E-mini Russell 2000 |
| YM | YM | E-mini Dow |

### FX Futures

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| 6E | URO | Euro FX Future |
| 6B | BP | British Pound Future |
| 6J | JY | Japanese Yen Future |
| 6A | AD | Australian Dollar Future |
| 6C | CD | Canadian Dollar Future |
| 6S | SF | Swiss Franc Future |

### Grains

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| ZC | C | Corn |
| ZW | W | Wheat (SRW) |
| ZS | S | Soybeans |

**RIC Suffixes**:
- `c1` = Front month continuous (e.g., `TYc1`)
- `c2` = Second month continuous
- `H5` = March 2025 discrete contract
- `^2` = Expired contract decade marker (needs validation)

**Month Codes**: F(Jan), G(Feb), H(Mar), J(Apr), K(May), M(Jun), N(Jul), Q(Aug), U(Sep), V(Oct), X(Nov), Z(Dec)

---

## Bond Futures

### US Treasury Futures (Complete Curve) - Validated 2026-01-06

**All 8 US Treasury futures validated: 8/8 working**

| Instrument | CME Symbol | LSEG RIC | Status | Daily | Notes |
|------------|------------|----------|--------|-------|-------|
| 2Y T-Note  | ZT | `TUc1` | ✅ | ✅ | 252 rows |
| 3Y T-Note  | Z3N | `YRc1` | ✅ | ✅ | 252 rows |
| 5Y T-Note  | ZF | `FVc1` | ✅ | ✅ | 252 rows |
| 10Y T-Note | ZN | `TYc1` | ✅ | ✅ | 252 rows |
| Ultra 10Y  | TN | `TNc1` | ✅ | ✅ | 252 rows |
| 20Y T-Bond | TWE | `ZPc1` | ✅ | ✅ | 252 rows |
| 30Y T-Bond | ZB | `USc1` | ✅ | ✅ | 252 rows |
| Ultra 30Y  | UB | `AULc1` | ✅ | ✅ | 252 rows |

**Key CME → LSEG Mapping Corrections:**
- 3Y T-Note: CME `Z3N` → LSEG `YRc1` (not `Z3Nc1`)
- 20Y T-Bond: CME `TWE` → LSEG `ZPc1` (not `TWEc1`)
- Ultra 30Y: CME `UB` → LSEG `AULc1` (not `UBc1`)

### European Bond Futures (Validated 2026-01-06)

**11/12 European bond futures validated**

| Instrument     | Symbol | LSEG RIC | Status | Daily | Notes |
|----------------|--------|----------|--------|-------|-------|
| **German (Eurex)** | | | | | |
| Euro-Schatz 2Y | FGBS   | `FGBSc1` | ✅ | ✅ | 254 rows |
| Euro-Bobl 5Y   | FGBM   | `FGBMc1` | ✅ | ✅ | 254 rows |
| Euro-Bund 10Y  | FGBL   | `FGBLc1` | ✅ | ✅ | 254 rows |
| Euro-Buxl 30Y  | FGBX   | `FGBXc1` | ✅ | ✅ | 254 rows |
| **French** | | | | | |
| Euro-OAT 10Y   | FOAT   | `FOATc1` | ✅ | ✅ | 254 rows |
| **Italian** | | | | | |
| Euro-BTP 10Y   | FBTP   | `FBTPc1` | ✅ | ✅ | 254 rows |
| Euro-BTP Short | FBTS   | `FBTSc1` | ✅ | ✅ | 254 rows |
| **Spanish** | | | | | |
| Euro-BONO 10Y  | FBON   | `FBONc1` | ✅ | ✅ | 254 rows |
| **Swiss** | | | | | |
| Swiss Conf     | CONF   | `CONFc1` | ✅ | ✅ | 254 rows |
| **UK (ICE)** | | | | | |
| UK Long Gilt   | FLG    | `FLGc1`  | ✅ | ✅ | 258 rows |
| UK Short Gilt  | FSG    | `FSGc1`  | ❌ | ❌ | Not found |
| UK Medium Gilt | FMG    | `FMGc1`  | ❌ | ❌ | Not found |

### Asian Bond Futures (Validated 2026-01-06)

| Instrument    | Symbol | LSEG RIC | Status | Daily | Intraday | Notes                    |
|---------------|--------|----------|--------|-------|----------|--------------------------|
| JGB 10Y       | JGB    | `JGBc1`  | ✅     | ✅    | ✅       | Osaka Exchange, 246 rows |

### Australian Bond Futures (Validated 2026-01-06)

**Pattern**: `YT{T/C}c1` (not `YTc1` or `XTc1` as documented elsewhere)

| Instrument    | Symbol | LSEG RIC | Status | Daily | Intraday | Notes                    |
|---------------|--------|----------|--------|-------|----------|--------------------------|
| Australia 3Y  | YTT    | `YTTc1`  | ✅     | ✅    | ✅       | ASX, 257 rows           |
| Australia 10Y | YTC    | `YTCc1`  | ✅     | ✅    | ✅       | ASX, 257 rows           |
| Chain 3Y      | -      | `0#YTT:` | ✅     | -     | -        | All contracts           |
| Chain 10Y     | -      | `0#YTC:` | ✅     | -     | -        | All contracts           |

### Canadian Bond Futures (Validated 2026-01-06)

**All 3 Canadian bond futures validated: 3/3 working**

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes            |
|------------|--------|----------|--------|-------|----------|------------------|
| Canada 10Y | CGB    | `CGBc1`  | ✅     | ✅    | ✅       | Montreal Exchange |
| Canada 5Y  | CGF    | `CGFc1`  | ✅     | ✅    | ✅       | Montreal Exchange |
| Canada 2Y  | CGZ    | `CGZc1`  | ✅     | ✅    | ✅       | Montreal Exchange |

---

## STIR Futures (Short-Term Interest Rate)

### CME Symbol → LSEG RIC Mapping

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| SR3 | SRA | 3-Month SOFR Futures |
| SR1 | SOFR | 1-Month SOFR Futures |
| ZQ | FF | 30-Day Fed Funds Futures |

### USD STIR

| Instrument | CME | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|-----|----------|--------|-------|----------|-------|
| 3M SOFR | SR3 | `SRAc1` | ✅ | ✅ | ❓ | CME SR3 → LSEG SRA |
| 3M SOFR Chain | - | `0#SRA:` | ✅ | - | - | All contracts |
| 1M SOFR | SR1 | `SOFRc1` | ⛔ | - | - | Access Denied (permissions) |
| 1M SOFR Chain | - | `0#SOFR:` | ✅ | ⛔ | - | Snapshot only, no history |
| Fed Funds | ZQ | `FFc1` | ✅ | ✅ | ❓ | CME ZQ → LSEG FF |
| Fed Funds Chain | - | `0#FF:` | ✅ | - | - | All contracts |

### EUR STIR

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| 3M Euribor | FEI | `FEIc1` | ✅ | ✅ | ❓ | ICE/Eurex |
| Euribor Chain | - | `0#FEI:` | ✅ | - | - | All contracts |

### GBP STIR

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| SONIA Future | - | `SONc1` | ✅ | ✅ | ❓ | ICE Europe |

---

## Stock Index Futures (Validated 2026-01-07)

### US Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| E-mini S&P 500 | ES | `ESc1` | ✅ | ✅ | ✅ | CME, 255 rows |
| E-mini Nasdaq-100 | NQ | `NQc1` | ✅ | ✅ | ✅ | CME, 255 rows |
| E-mini Russell 2000 | RTY | `RTYc1` | ✅ | ✅ | ✅ | CME, 255 rows |
| E-mini Dow | YM | `YMc1` | ✅ | ✅ | ✅ | CBOT, 255 rows |
| VIX Futures | VX | `VXc1` | ✅ | ✅ | ✅ | CFE, 250 rows |

### Canadian Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| S&P/TSX 60 | SXF | `SXFc1` | ✅ | ✅ | ✅ | TMX, 251 rows |

### European Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Euro Stoxx 50 | FESX | `STXEc1` | ✅ | ✅ | ✅ | Eurex, 262 rows |
| STOXX Europe 600 | FXXP | `FXXPc1` | ✅ | ✅ | ✅ | Eurex, 253 rows |
| DAX | FDAX | `FDXc1` | ✅ | ✅ | ✅ | Eurex, 262 rows |
| FTSE 100 | Z | `FFIc1` | ✅ | ✅ | ✅ | ICE, 260 rows |
| FTSE MIB | FMIB | `FMIBc1` | ✅ | ✅ | ✅ | Eurex, 237 rows |
| CAC 40 | FCE | `FCEc1` | ✅ | ✅ | ✅ | Euronext, 262 rows |
| SMI (Swiss) | FSMI | `FSMIc1` | ✅ | ✅ | ✅ | Eurex, 254 rows |
| AEX (Dutch) | FTI | `AEXc1` | ✅ | ✅ | ✅ | Euronext, 262 rows |

### Asian Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Nikkei 225 (Osaka) | JNI | `JNIc1` | ✅ | ✅ | ✅ | OSE, 246 rows |
| Nikkei 225 (CME Yen) | NIY | `NIYc1` | ✅ | ✅ | ✅ | CME, 256 rows |
| Hang Seng | HSI | `HSIc1` | ✅ | ✅ | ✅ | HKEX, 247 rows |
| Hang Seng China Enterprises | HCEI | `HCEIc1` | ✅ | ✅ | ✅ | HKEX, 247 rows |
| KOSPI 200 | KS | `KSc1` | ✅ | ✅ | ✅ | KRX, 247 rows |
| TAIEX (Taiwan) | TX | `TXc1` | ✅ | ✅ | ✅ | TAIFEX, 249 rows |
| ASX 200 Mini | YAP | `YAPc1` | ✅ | ✅ | ✅ | ASX, 255 rows |
| SGX Nifty 50 | SSN | `SSNc1` | ✅ | ✅ | ✅ | SGX, 243 rows |

### Latin American Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Bovespa | IND | `INDc1` | ✅ | ✅ | ✅ | B3, 250 rows |
| Mini Bovespa | WSP | `WSPc1` | ✅ | ✅ | ✅ | B3, 250 rows |
| IPC Mexico | IPC | `IPCc1` | ✅ | ✅ | ✅ | BMV, 251 rows |

### Missing Futures

No futures found for:
- IBEX 35 (Spain) - no LSEG RIC found
- TOPIX (Japan) - no continuous contract found
- CSI 300 (China) - requires China data package
- S&P MidCap 400 - no LSEG RIC found

---

## Equity Indices (Spot) (Validated 2026-01-07)

**34/36 indices validated for daily data, 35/36 for intraday**

### US Indices

| Index | LSEG RIC | Status | Daily | Intraday | Last Value |
|-------|----------|--------|-------|----------|------------|
| S&P 500 | `.SPX` | ✅ | ✅ | ✅ | 6944.82 |
| Nasdaq 100 | `.NDX` | ✅ | ✅ | ✅ | 25639.71 |
| Dow Jones Industrial | `.DJI` | ✅ | ✅ | ✅ | 49462.08 |
| Russell 2000 | `.RUT` | ✅ | ✅ | ✅ | 2582.90 |
| Russell 1000 | `.RUI` | ✅ | ✅ | ✅ | 3793.33 |
| Russell 3000 | `.RUA` | ✅ | ✅ | ✅ | 3949.82 |
| Nasdaq Composite | `.IXIC` | ✅ | ✅ | ✅ | 23547.17 |
| CBOE VIX | `.VIX` | ✅ | ✅ | ✅ | 14.75 |
| Nasdaq Volatility | `.VXN` | ❌ | ❌ | ❌ | No data |
| S&P MidCap 400 | `.SP400` | ✅ | ✅ | ✅ | 3443.43 |

### Canadian Indices

| Index | LSEG RIC | Status | Daily | Intraday | Last Value |
|-------|----------|--------|-------|----------|------------|
| S&P/TSX Composite (old) | `.SPTSE` | ✅ | ✅ | ✅ | 1895.85 |
| S&P/TSX Composite | `.GSPTSE` | ✅ | ✅ | ✅ | 32407.02 |

### European Indices

| Index | LSEG RIC | Status | Daily | Intraday | Last Value |
|-------|----------|--------|-------|----------|------------|
| FTSE 100 | `.FTSE` | ✅ | ✅ | ✅ | 10048.21 |
| DAX | `.GDAXI` | ✅ | ✅ | ✅ | 25122.26 |
| CAC 40 | `.FCHI` | ✅ | ✅ | ✅ | 8233.92 |
| FTSE MIB | `.FTMIB` | ✅ | ✅ | ✅ | 45558.68 |
| AEX | `.AEX` | ✅ | ✅ | ✅ | 979.15 |
| IBEX 35 | `.IBEX` | ✅ | ✅ | ✅ | 17596.40 |
| STOXX Europe 600 | `.STOXX` | ✅ | ✅ | ✅ | 604.99 |
| Euro STOXX 50 | `.STOXX50E` | ✅ | ✅ | ✅ | 5923.57 |

### Asian Indices

| Index | LSEG RIC | Status | Daily | Intraday | Last Value |
|-------|----------|--------|-------|----------|------------|
| Nikkei 225 | `.N225` | ✅ | ✅ | ✅ | 51961.98 |
| TOPIX | `.TOPX` | ✅ | ✅ | ✅ | 3511.34 |
| CSI 300 | `.CSI000300` | ✅ | ✅ | ✅ | 4776.67 |
| Hang Seng | `.HSI` | ✅ | ✅ | ✅ | 26458.95 |
| KOSPI | `.KS11` | ✅ | ✅ | ✅ | 4551.06 |
| ASX 200 | `.AXJO` | ✅ | ✅ | ✅ | 8695.60 |

### Latin American Indices

| Index | LSEG RIC | Status | Daily | Intraday | Last Value |
|-------|----------|--------|-------|----------|------------|
| Bovespa | `.BVSP` | ✅ | ✅ | ✅ | 163663.88 |
| IPC Mexico | `.MXX` | ✅ | ✅ | ✅ | 65022.24 |
| S&P IPSA Chile | `.SPIPSA` | ✅ | ✅ | ✅ | 10927.79 |
| MERVAL Argentina | `.MERV` | ✅ | ✅ | ✅ | 3112376.81 |
| IBC Venezuela | `.IBC` | ✅ | ✅ | ✅ | 3896.77 |
| COLCAP Colombia | `.COLCAP` | ✅ | ✅ | ✅ | 2175.89 |

### Other Global Indices

| Index | LSEG RIC | Status | Daily | Intraday | Last Value |
|-------|----------|--------|-------|----------|------------|
| Nifty 50 | `.NSEI` | ✅ | ✅ | ✅ | 26140.75 |
| PSI Portugal | `.SPBL25PT` | ⚠️ | ❌ | ✅ | Intraday only |
| S&P Emerging Markets | `.SPCY` | ✅ | ✅ | ✅ | 1523.02 |
| MSCI World USD | `.dMIWD00000PUS` | ✅ | ✅ | ✅ | 1035.15 |

### Volatility Indices (VIX Family)

**8/18 volatility indices validated**

| Index | LSEG RIC | Status | Last Value | Notes |
|-------|----------|--------|------------|-------|
| CBOE VIX (S&P 500) | `.VIX` | ✅ | 14.75 | Primary VIX |
| VXD (Dow Jones) | `.VXD` | ✅ | 14.42 | DJIA volatility |
| VVIX (VIX of VIX) | `.VVIX` | ✅ | 89.01 | VIX volatility |
| VIX 9-Day | `.VIX9D` | ✅ | 12.13 | Short-term VIX |
| VIX 3-Month | `.VIX3M` | ✅ | 18.15 | |
| VIX 6-Month | `.VIX6M` | ✅ | 20.78 | |
| VIX 1-Year | `.VIX1Y` | ✅ | 22.38 | |
| VSTOXX | `.V2TX` | ✅ | 15.35 | European VIX |
| VXN (Nasdaq 100) | `.VXN` | ❌ | - | No data |
| RVX (Russell 2000) | `.RVX` | ❌ | - | No data |
| CBOE SKEW | `.SKEW` | ❌ | - | No data |
| Oil VIX | `.OVX` | ❌ | - | No data |
| Gold VIX | `.GVZ` | ❌ | - | No data |
| Euro VIX | `.EVZ` | ❌ | - | No data |
| Treasury VIX | `.TYVIX` | ❌ | - | No data |
| VDAX-NEW | `.V1X` | ❌ | - | No data |
| VFTSE | `.VFTSE` | ❌ | - | No data |

### Notes

- Several CBOE volatility indices (VXN, RVX, OVX, GVZ) return no data - may require additional permissions
- `.SPBL25PT` (Portugal PSI) has intraday but no daily - use `.PSI20` instead
- For index futures, see the Stock Index Futures section above
- For VIX futures, use `VXc1` (continuous front month)

---

## FX Spot

### Major Pairs

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| EUR/USD | EURUSD | `EUR=` | ✅ | ✅ | ✅ | |
| GBP/USD | GBPUSD | `GBP=` | ✅ | ✅ | ✅ | |
| USD/JPY | USDJPY | `JPY=` | ✅ | ✅ | ✅ | |
| USD/CHF | USDCHF | `CHF=` | ✅ | ✅ | ✅ | |
| AUD/USD | AUDUSD | `AUD=` | ✅ | ✅ | ✅ | |
| USD/CAD | USDCAD | `CAD=` | ✅ | ✅ | ✅ | |
| NZD/USD | NZDUSD | `NZD=` | ✅ | ✅ | ✅ | |

### Scandinavian & Minor G10 (Validated 2026-01-06)

| Pair | LSEG RIC | Status | Notes |
|------|----------|--------|-------|
| USD/SEK | `SEK=` | ✅ | |
| USD/NOK | `NOK=` | ✅ | |
| USD/DKK | `DKK=` | ✅ | |
| EUR/SEK | `EURSEK=` | ✅ | |
| EUR/NOK | `EURNOK=` | ✅ | |
| EUR/DKK | `EURDKK=` | ✅ | |

### Cross Rates (Validated 2026-01-06)

**17/18 FX cross pairs validated**

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| EUR/GBP | EURGBP | `EURGBP=` | ✅ | ✅ | ✅ | |
| EUR/JPY | EURJPY | `EURJPY=` | ✅ | ✅ | ✅ | |
| EUR/CHF | EURCHF | `EURCHF=` | ✅ | ✅ | ✅ | |
| EUR/AUD | EURAUD | `EURAUD=` | ✅ | ✅ | ✅ | |
| EUR/CAD | EURCAD | `EURCAD=` | ✅ | ✅ | ✅ | |
| EUR/NZD | EURNZD | `EURNZD=` | ✅ | ✅ | ✅ | |
| EUR/SEK | EURSEK | `EURSEK=` | ✅ | ✅ | ✅ | |
| EUR/NOK | EURNOK | `EURNOK=` | ✅ | ✅ | ✅ | |
| GBP/JPY | GBPJPY | `GBPJPY=` | ✅ | ✅ | ✅ | |
| GBP/CHF | GBPCHF | `GBPCHF=` | ✅ | ✅ | ✅ | |
| GBP/AUD | GBPAUD | `GBPAUD=` | ✅ | ✅ | ✅ | |
| AUD/JPY | AUDJPY | `AUDJPY=` | ✅ | ✅ | ✅ | |
| AUD/NZD | AUDNZD | `AUDNZD=` | ✅ | ✅ | ✅ | |
| AUD/CAD | AUDCAD | `AUDCAD=` | ✅ | ✅ | ✅ | |
| NZD/JPY | NZDJPY | `NZDJPY=` | ✅ | ✅ | ✅ | |
| CAD/JPY | CADJPY | `CADJPY=` | ✅ | ✅ | ✅ | |
| CHF/JPY | CHFJPY | `CHFJPY=` | ✅ | ✅ | ✅ | |

### Emerging Markets (Validated 2026-01-06)

**All 18 EM FX spot pairs validated: 18/18 working**

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| USD/MXN | USDMXN | `MXN=` | ✅ | ✅ | ✅ | |
| USD/BRL | USDBRL | `BRL=` | ✅ | ✅ | ✅ | |
| USD/ZAR | USDZAR | `ZAR=` | ✅ | ✅ | ✅ | |
| USD/TRY | USDTRY | `TRY=` | ✅ | ✅ | ✅ | |
| USD/INR | USDINR | `INR=` | ✅ | ✅ | ✅ | |
| USD/CNH | USDCNH | `CNH=` | ✅ | ✅ | ✅ | Offshore CNY |
| USD/SGD | USDSGD | `SGD=` | ✅ | ✅ | ✅ | |
| USD/HKD | USDHKD | `HKD=` | ✅ | ✅ | ✅ | |
| USD/KRW | USDKRW | `KRW=` | ✅ | ✅ | ✅ | |
| USD/PLN | USDPLN | `PLN=` | ✅ | ✅ | ✅ | |
| USD/CZK | USDCZK | `CZK=` | ✅ | ✅ | ✅ | |
| USD/HUF | USDHUF | `HUF=` | ✅ | ✅ | ✅ | |
| USD/RUB | USDRUB | `RUB=` | ✅ | ✅ | ✅ | |
| USD/THB | USDTHB | `THB=` | ✅ | ✅ | ✅ | |
| USD/TWD | USDTWD | `TWD=` | ✅ | ✅ | ✅ | |
| USD/IDR | USDIDR | `IDR=` | ✅ | ✅ | ✅ | |
| USD/PHP | USDPHP | `PHP=` | ✅ | ✅ | ✅ | |
| USD/MYR | USDMYR | `MYR=` | ✅ | ✅ | ✅ | |

### Additional EM FX Spot (Validated 2026-01-06)

**All 35 additional EM currencies validated: 35/35 working**

| Region | Currencies | Status |
|--------|------------|--------|
| **CEEMEA** | RON=, BGN=, HRK=, RSD=, UAH= | ✅ All 5 |
| **Middle East** | AED=, SAR=, QAR=, KWD=, BHD=, OMR=, JOD=, ILS=, EGP= | ✅ All 9 |
| **Asia** | VND=, PKR=, BDT=, LKR=, NPR=, MMK=, KHR=, LAK= | ✅ All 8 |
| **Latin America** | CLP=, COP=, PEN=, ARS=, UYU=, DOP= | ✅ All 6 |
| **Africa** | NGN=, KES=, GHS=, TZS=, UGX=, MAD=, TND= | ✅ All 7 |

---

## NDFs (Non-Deliverable Forwards) - Validated 2026-01-06

**Pattern**: `{CCY}{tenor}NDF=` - 26/29 tested working

| Currency | Tenors | Example RIC | Status |
|----------|--------|-------------|--------|
| CNY (China) | 1M, 3M, 6M, 1Y | `CNY1MNDF=` | ✅ |
| KRW (Korea) | 1M, 3M, 6M, 1Y | `KRW1MNDF=` | ✅ |
| INR (India) | 1M, 3M, 6M, 1Y | `INR1MNDF=` | ✅ |
| TWD (Taiwan) | 1M, 3M, 6M, 1Y | `TWD1MNDF=` | ✅ |
| BRL (Brazil) | 1M, 3M, 6M, 1Y | `BRL1MNDF=` | ✅ |
| IDR (Indonesia) | 1M, 3M, 1Y | `IDR1MNDF=` | ✅ |
| PHP (Philippines) | 1M, 3M, 1Y | `PHP1MNDF=` | ✅ |

---

## FX Futures (CME) - Validated 2026-01-06

**All 9 major FX futures validated: 9/9 working**

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| EUR/USD | 6E | `UROc1` | ✅ | ✅ | ✅ | CME Euro FX, 256 rows |
| GBP/USD | 6B | `BPc1` | ✅ | ✅ | ✅ | CME British Pound, 256 rows |
| JPY/USD | 6J | `JYc1` | ✅ | ✅ | ✅ | CME Japanese Yen, 256 rows |
| AUD/USD | 6A | `ADc1` | ✅ | ✅ | ✅ | CME Australian Dollar, 256 rows |
| CAD/USD | 6C | `CDc1` | ✅ | ✅ | ✅ | CME Canadian Dollar, 256 rows |
| CHF/USD | 6S | `SFc1` | ✅ | ✅ | ✅ | CME Swiss Franc, 256 rows |
| MXN/USD | 6M | `MPc1` | ✅ | ✅ | ✅ | CME Mexican Peso, 256 rows |
| NZD/USD | 6N | `NEc1` | ✅ | ✅ | ✅ | CME New Zealand Dollar, 256 rows |
| BRL/USD | 6L | `BRc1` | ✅ | ✅ | ✅ | CME Brazilian Real, 256 rows |

---

## VIX Futures (Validated 2026-01-06)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| VIX Front | VX | `VXc1` | ✅ | ✅ | ✅ | CBOE VIX Futures |
| VIX 2nd | VX | `VXc2` | ✅ | ✅ | ✅ | 2nd month |
| VIX 3rd | VX | `VXc3` | ✅ | ✅ | ✅ | 3rd month |
| VIX Chain | - | `0#VX:` | ✅ | - | - | 14 contracts available |

---

## FX Forwards (Validated 2026-01-06)

**Pattern**: `{CCY}{tenor}=` for major pairs - 10/11 tenors working per pair

**Available Tenors**: ON, TN, SN, SW, 1M, 2M, 3M, 6M, 9M, 1Y, 2Y (SN not available)

### EUR/USD Forwards

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| ON | `EURON=` | ✅ | ✅ | Overnight |
| TN | `EURTN=` | ✅ | ✅ | Tom/Next |
| SW | `EURSW=` | ✅ | ✅ | Spot Week |
| 1M | `EUR1M=` | ✅ | ✅ | |
| 2M | `EUR2M=` | ✅ | ✅ | |
| 3M | `EUR3M=` | ✅ | ✅ | |
| 6M | `EUR6M=` | ✅ | ✅ | |
| 9M | `EUR9M=` | ✅ | ✅ | |
| 1Y | `EUR1Y=` | ✅ | ✅ | |
| 2Y | `EUR2Y=` | ✅ | ✅ | |

### GBP/USD Forwards

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| ON-2Y | `GBP{tenor}=` | ✅ | ✅ | All 10 tenors work |

### USD/JPY Forwards

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| ON-2Y | `JPY{tenor}=` | ✅ | ✅ | All 10 tenors work |

### USD/CHF Forwards

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| ON-2Y | `CHF{tenor}=` | ✅ | ✅ | All 10 tenors work |

### AUD/USD Forwards

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| ON-2Y | `AUD{tenor}=` | ✅ | ✅ | All 10 tenors work |

### USD/CAD Forwards

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| ON-2Y | `CAD{tenor}=` | ✅ | ✅ | All 10 tenors work |

### EM FX Forwards (Validated 2026-01-06)

**11/12 EM currencies have full forward curve (1M, 3M, 6M, 1Y)**

| Currency | Pattern | Status | Notes |
|----------|---------|--------|-------|
| MXN | `MXN{tenor}=` | ✅ | All 4 tenors |
| ZAR | `ZAR{tenor}=` | ✅ | All 4 tenors |
| TRY | `TRY{tenor}=` | ✅ | All 4 tenors |
| INR | `INR{tenor}=` | ✅ | All 4 tenors |
| CNH | `CNH{tenor}=` | ✅ | All 4 tenors |
| KRW | `KRW{tenor}=` | ✅ | All 4 tenors |
| SGD | `SGD{tenor}=` | ✅ | All 4 tenors |
| HKD | `HKD{tenor}=` | ✅ | All 4 tenors |
| PLN | `PLN{tenor}=` | ✅ | All 4 tenors |
| CZK | `CZK{tenor}=` | ✅ | All 4 tenors |
| HUF | `HUF{tenor}=` | ✅ | All 4 tenors |
| BRL | Use NDFs | - | Use `BRL{tenor}NDF=` |

### Additional G10 Forwards (Validated 2026-01-06)

**Pattern**: `{CCY}{tenor}=` - Also works for Scandinavian currencies

| Currency | Working Tenors | Status |
|----------|----------------|--------|
| SEK | 2W, 1M, 2M, 3M, 6M, 9M, 1Y, 2Y | ✅ 8/8 |
| NOK | 2W, 1M, 2M, 3M, 6M, 9M, 1Y, 2Y | ✅ 8/8 |
| NZD | 2W, 1M, 2M, 3M, 6M, 9M, 1Y, 2Y | ✅ 8/8 |

**Total G10 Forward Swap Points**: 72 RICs (9 currencies × 8 tenors)

### FX Forward Outrights (Validated 2026-01-06)

**Pattern**: `{CCY}{tenor}V=` - Outright forward rate (spot + forward points)

| Currency | Working Tenors | Example | Status |
|----------|----------------|---------|--------|
| EUR | 1M, 3M, 6M, 1Y | `EUR3MV=` | ✅ 4/4 |
| JPY | 1M, 3M, 6M, 1Y | `JPY3MV=` | ✅ 4/4 |
| GBP | 1M, 3M, 6M, 1Y | `GBP3MV=` | ✅ 4/4 |

**Total Forward Outrights**: 12 RICs (3 currencies × 4 tenors)

### FX Cross Forwards (Validated 2026-01-06)

**Pattern**: `{CCY1}{CCY2}FWD=` - Forward points for EUR and GBP crosses

| Cross Pair | LSEG RIC | Status | Notes |
|------------|----------|--------|-------|
| EUR/GBP | `EURGBPFWD=` | ✅ | EUR/GBP forward points |
| EUR/JPY | `EURJPYFWD=` | ✅ | EUR/JPY forward points |
| EUR/CHF | `EURCHFFWD=` | ✅ | EUR/CHF forward points |
| EUR/AUD | `EURAUDFWD=` | ✅ | EUR/AUD forward points |
| EUR/CAD | `EURCADFWD=` | ✅ | EUR/CAD forward points |
| EUR/SEK | `EURSEKFWD=` | ✅ | EUR/SEK forward points |
| EUR/NOK | `EURNOKFWD=` | ✅ | EUR/NOK forward points |
| EUR/NZD | `EURNZDFWD=` | ✅ | EUR/NZD forward points |
| EUR/DKK | `EURDKKFWD=` | ✅ | EUR/DKK forward points |
| EUR/PLN | `EURPLNFWD=` | ✅ | EUR/PLN forward points |
| GBP/JPY | `GBPJPYFWD=` | ✅ | GBP/JPY forward points |
| GBP/CHF | `GBPCHFFWD=` | ✅ | GBP/CHF forward points |
| GBP/AUD | `GBPAUDFWD=` | ✅ | GBP/AUD forward points |
| GBP/CAD | `GBPCADFWD=` | ✅ | GBP/CAD forward points |

**Total Cross Forwards**: 14/14 working

---

## FX Implied Volatility (Validated 2026-01-06)

**Pattern**: `{CCY}{tenor}O=` - ATM implied volatility with full historical data (262 rows)

### G10 ATM Vol - Standard Tenors

| Pair | 1M | 3M | 6M | 1Y | Status |
|------|----|----|----|----|--------|
| EUR/USD | `EUR1MO=` | `EUR3MO=` | `EUR6MO=` | `EUR1YO=` | ✅ |
| USD/JPY | `JPY1MO=` | `JPY3MO=` | `JPY6MO=` | `JPY1YO=` | ✅ |
| GBP/USD | `GBP1MO=` | `GBP3MO=` | `GBP6MO=` | `GBP1YO=` | ✅ |
| USD/CHF | `CHF1MO=` | `CHF3MO=` | - | `CHF1YO=` | ✅ |
| AUD/USD | `AUD1MO=` | `AUD3MO=` | - | `AUD1YO=` | ✅ |
| USD/CAD | `CAD1MO=` | `CAD3MO=` | - | `CAD1YO=` | ✅ |
| NZD/USD | `NZD1MO=` | `NZD3MO=` | - | `NZD1YO=` | ✅ |

### G10 ATM Vol - Extended Tenors (Validated 2026-01-06)

**Additional tenors validated: 2W, 2M, 9M, 2Y, 3Y, 5Y**

| Pair | 2W | 2M | 9M | 2Y | 3Y | 5Y |
|------|----|----|----|----|----|----|
| EUR/USD | `EUR2WO=` | `EUR2MO=` | `EUR9MO=` | `EUR2YO=` | `EUR3YO=` | `EUR5YO=` |
| USD/JPY | `JPY2WO=` | `JPY2MO=` | `JPY9MO=` | `JPY2YO=` | `JPY3YO=` | `JPY5YO=` |
| GBP/USD | - | `GBP2MO=` | `GBP9MO=` | `GBP2YO=` | `GBP3YO=` | `GBP5YO=` |
| AUD/USD | - | `AUD2MO=` | `AUD9MO=` | `AUD2YO=` | `AUD3YO=` | `AUD5YO=` |
| USD/CHF | - | `CHF2MO=` | `CHF9MO=` | `CHF2YO=` | `CHF3YO=` | `CHF5YO=` |

**Note**: Full G10 vol surface available from 2W to 5Y for EUR and JPY; 2M-5Y for others.

### Cross Vol

| Pair | 1M | 3M | Status |
|------|----|----|--------|
| EUR/JPY | `EURJPY1MO=` | `EURJPY3MO=` | ✅ |
| EUR/GBP | `EURGBP1MO=` | `EURGBP3MO=` | ✅ |
| EUR/CHF | `EURCHF1MO=` | `EURCHF3MO=` | ✅ |
| EUR/AUD | `EURAUD1MO=` | - | ✅ |
| EUR/CAD | `EURCAD1MO=` | - | ✅ |
| GBP/JPY | `GBPJPY1MO=` | `GBPJPY3MO=` | ✅ |
| AUD/JPY | `AUDJPY1MO=` | `AUDJPY3MO=` | ✅ |
| GBP/CHF | `GBPCHF1MO=` | - | ✅ |
| AUD/NZD | `AUDNZD1MO=` | - | ✅ |
| AUD/CAD | `AUDCAD1MO=` | - | ✅ |

### EM Vol

| Pair | 1M | 3M | Status |
|------|----|----|--------|
| USD/MXN | `MXN1MO=` | `MXN3MO=` | ✅ |
| USD/ZAR | `ZAR1MO=` | `ZAR3MO=` | ✅ |
| USD/TRY | `TRY1MO=` | `TRY3MO=` | ✅ |
| USD/BRL | `BRL1MO=` | `BRL3MO=` | ✅ |
| USD/INR | `INR1MO=` | - | ✅ |
| USD/CNH | `CNH1MO=` | - | ✅ |
| USD/KRW | `KRW1MO=` | - | ✅ |
| EUR/PLN | `PLN1MO=` | - | ✅ |
| EUR/CZK | `CZK1MO=` | - | ✅ |
| EUR/HUF | `HUF1MO=` | - | ✅ |

### Risk Reversals & Butterflies

**Status**: ⛔ Access Denied (premium data)

| Pattern | Example | Status |
|---------|---------|--------|
| 25D Risk Reversal | `EURRR25=` | ⛔ Access Denied |
| 25D Butterfly | `EURBF25=` | ⛔ Access Denied |

---

## Currency Indices (Validated 2026-01-06)

### US Dollar Index (DXY)

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| DXY Spot | `.DXY` | ✅ | ✅ | 260 rows, OHLC |
| DXY Front Future | `DXc1` | ✅ | ✅ | 259 rows, ICE |
| DXY 2nd Future | `DXc2` | ✅ | ✅ | ICE |
| DXY 3rd Future | `DXc3` | ✅ | ⚠️ | Limited volume |
| DXY Chain | `0#DX:` | ✅ | - | All contracts |

### DXY Options (Validated 2026-01-06)

**Pattern**: `1DX{strike}{month}{YY}` where month codes: A=Jan call, M=Jan put, etc.

| Strike | Call | Put | Status |
|--------|------|-----|--------|
| 98 | `1DX9800A26` | `1DX9800M26` | ✅ |
| 99 | `1DX9900A26` | `1DX9900M26` | ✅ |
| 100 | `1DX10000A26` | `1DX10000M26` | ✅ |
| Chain | `0#1DXM6+` | - | ✅ |

### Other Currency Indices

| Index | LSEG RIC | Status | Notes |
|-------|----------|--------|-------|
| Euro Index | `EURX=` | ✅ | Snapshot only |
| Yen Index | `JPYX=` | ✅ | Snapshot only |

---

## FX Cross Futures (CME) - Validated 2026-01-06

| Cross | LSEG RIC | Status | Notes |
|-------|----------|--------|-------|
| EUR/GBP | `RPc1` | ✅ | EUR/BP future |
| EUR/JPY | `RYc1` | ✅ | EUR/JY future |
| EUR/CHF | `RFc1` | ✅ | EUR/SF future |
| CNH | `CNHc1` | ✅ | KOFEX CNH |
| KRW | `KRWc1` | ✅ | KOFEX USD/KRW |

---

## OIS (Overnight Index Swaps)

### USD SOFR OIS

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `USD1MOIS=` | ✅ | ✅ | |
| 2M | `USD2MOIS=` | ✅ | ✅ | |
| 3M | `USD3MOIS=` | ✅ | ✅ | |
| 4M | `USD4MOIS=` | ✅ | ✅ | |
| 5M | `USD5MOIS=` | ✅ | ✅ | |
| 6M | `USD6MOIS=` | ✅ | ✅ | |
| 9M | `USD9MOIS=` | ✅ | ✅ | |
| 1Y | `USD1YOIS=` | ✅ | ✅ | |
| 18M | `USD18MOIS=` | ✅ | ✅ | |
| 2Y | `USD2YOIS=` | ✅ | ✅ | |
| 3Y | `USD3YOIS=` | ✅ | ✅ | |
| 4Y | `USD4YOIS=` | ✅ | ✅ | |
| 5Y | `USD5YOIS=` | ✅ | ✅ | |
| 6Y | `USD6YOIS=` | ✅ | ✅ | |
| 7Y | `USD7YOIS=` | ✅ | ✅ | |
| 8Y | `USD8YOIS=` | ✅ | ✅ | |
| 9Y | `USD9YOIS=` | ✅ | ✅ | |
| 10Y | `USD10YOIS=` | ✅ | ✅ | |
| 12Y | `USD12YOIS=` | ✅ | ✅ | |
| 15Y | `USD15YOIS=` | ✅ | ✅ | |
| 20Y | `USD20YOIS=` | ✅ | ✅ | |
| 25Y | `USD25YOIS=` | ✅ | ✅ | |
| 30Y | `USD30YOIS=` | ✅ | ✅ | |

### EUR - Use IRS Instead of OIS

**Note**: EUR OIS pattern (`EUR{tenor}OIS=`) does not work. Use `EURIRS{tenor}=` instead.
See [EUR IRS section](#eur-irs-validated-2026-01-06) for full curve (17/17 tenors validated, 1Y-50Y).

### GBP SONIA OIS (Validated 2026-01-06)

**Pattern**: `GBP{tenor}OIS=` (bare pattern works, no contributor suffix needed)

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `GBP1MOIS=` | ✅ | ✅ | 262 rows |
| 2M | `GBP2MOIS=` | ✅ | ✅ | 262 rows |
| 3M | `GBP3MOIS=` | ✅ | ✅ | 262 rows |
| 6M | `GBP6MOIS=` | ✅ | ✅ | 262 rows |
| 9M | `GBP9MOIS=` | ✅ | ✅ | 262 rows |
| 1Y | `GBP1YOIS=` | ✅ | ✅ | 262 rows |
| 2Y | `GBP2YOIS=` | ✅ | ✅ | 262 rows |
| 3Y | `GBP3YOIS=` | ✅ | ✅ | 262 rows |
| 5Y | `GBP5YOIS=` | ✅ | ✅ | 262 rows |
| 7Y | `GBP7YOIS=` | ✅ | ✅ | 262 rows |
| 10Y | `GBP10YOIS=` | ✅ | ✅ | 262 rows |
| 15Y | `GBP15YOIS=` | ✅ | ✅ | 262 rows |
| 20Y | `GBP20YOIS=` | ✅ | ✅ | 262 rows |
| 30Y | `GBP30YOIS=` | ✅ | ✅ | 262 rows |

### JPY OIS (Validated 2026-01-06)

**Pattern**: `JPY{tenor}OIS=`

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `JPY1MOIS=` | ✅ | ✅ | 262 rows |
| 3M | `JPY3MOIS=` | ✅ | ✅ | 262 rows |
| 6M | `JPY6MOIS=` | ✅ | ✅ | 262 rows |
| 1Y | `JPY1YOIS=` | ✅ | ✅ | 262 rows |
| 2Y | `JPY2YOIS=` | ✅ | ✅ | 262 rows |
| 5Y | `JPY5YOIS=` | ✅ | ✅ | 262 rows |
| 10Y | `JPY10YOIS=` | ✅ | ✅ | 262 rows |
| 30Y | `JPY30YOIS=` | ✅ | ✅ | 262 rows |

### CHF SARON OIS (Validated 2026-01-06)

**Pattern**: `CHF{tenor}OIS=`

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `CHF1MOIS=` | ✅ | ✅ | 262 rows |
| 3M | `CHF3MOIS=` | ✅ | ✅ | 262 rows |
| 6M | `CHF6MOIS=` | ✅ | ✅ | 262 rows |
| 1Y | `CHF1YOIS=` | ✅ | ✅ | 262 rows |
| 2Y | `CHF2YOIS=` | ✅ | ✅ | 262 rows |
| 5Y | `CHF5YOIS=` | ✅ | ✅ | 262 rows |
| 10Y | `CHF10YOIS=` | ✅ | ✅ | 262 rows |
| 30Y | `CHF30YOIS=` | ✅ | ✅ | 262 rows |

### CAD CORRA OIS (Validated 2026-01-06)

**Pattern**: `CAD{tenor}OIS=`

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `CAD1MOIS=` | ✅ | ✅ | 262 rows |
| 3M | `CAD3MOIS=` | ✅ | ✅ | 262 rows |
| 6M | `CAD6MOIS=` | ✅ | ✅ | 262 rows |
| 1Y | `CAD1YOIS=` | ✅ | ✅ | 262 rows |
| 2Y | `CAD2YOIS=` | ✅ | ✅ | 262 rows |
| 5Y | `CAD5YOIS=` | ✅ | ✅ | 262 rows |
| 10Y | `CAD10YOIS=` | ✅ | ✅ | 262 rows |
| 30Y | `CAD30YOIS=` | ✅ | ✅ | 262 rows |

### AUD OIS (Validated 2026-01-06)

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M-30Y | `AUD{tenor}OIS=` | ✅ | ✅ | 8/8 tenors work |

### NZD OIS (Validated 2026-01-06)

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M-30Y | `NZD{tenor}OIS=` | ✅ | ✅ | 7/8 tenors (no 10Y) |

---

## Overnight Benchmark Rates (Validated 2026-01-06)

### USD - SOFR

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| SOFR Fixing | `USDSOFR=` | ✅ | ✅ | NY Fed secured overnight rate |
| SOFR 30-Day Avg | `SOFR1MAVG=` | ✅ | ✅ | 30-day compounded average |
| Fed Funds Effective | `USONFFE=` | ✅ | ✅ | Fed Funds Composite |

### EUR - ESTR (€STR)

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| ESTR Fixing | `EUROSTR=` | ✅ | ✅ | ECB overnight rate |
| EONIA (legacy) | `EONIA=` | ⛔ | ⛔ | Discontinued - use ESTR |

### GBP - SONIA

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| SONIA Fixing | `SONIAOSR=` | ⛔ | ⛔ | Access Denied (premium) |
| SONIA Alternative | `GBPOND=` | ✅ | ✅ | GBP O/N deposit rate |

### CHF - SARON

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| SARON Fixing | `/SARON.S` | ✅ | ✅ | Uses TRDPRC_1 field |
| SARON Alternative | `SARON=` | ✅ | ✅ | Alternative RIC |

### JPY - TONA

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| TONA Fixing | `JPYTONAO/N=` | ⛔ | ⛔ | Access Denied |
| JPY O/N Deposit | `JPYOND=` | ✅ | ✅ | Alternative |

### CAD - CORRA

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| CORRA Fixing | `CADCORRA=` | ✅ | ✅ | Canadian overnight rate |

---

## EURIBOR (Euro Interbank Offered Rate) - Validated 2026-01-06

### EURIBOR Fixings

**4/5 EURIBOR tenors validated**

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1W | `EURIBOR1WD=` | ❌ | ❌ | Not found |
| 1M | `EURIBOR1MD=` | ✅ | ✅ | 1-month EURIBOR |
| 3M | `EURIBOR3MD=` | ✅ | ✅ | 3-month EURIBOR |
| 6M | `EURIBOR6MD=` | ✅ | ✅ | 6-month EURIBOR |
| 12M | `EURIBOR1YD=` | ✅ | ✅ | 12-month EURIBOR |

### EURIBOR Futures (ICE/Eurex)

| Instrument | Symbol | LSEG RIC | Status | Daily | Notes |
|------------|--------|----------|--------|-------|-------|
| 3M EURIBOR | FEI | `FEIc1` | ✅ | ✅ | Continuous front month |
| Chain | - | `0#FEI:` | ✅ | - | All contracts |

---

## Treasury Repo Rates (Validated 2026-01-06)

**5 US repo tenors validated**

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| O/N | `USONRP=` | ✅ | ✅ | Overnight Treasury Repo |
| 1W | `US1WRP=` | ✅ | ✅ | 1-week Repo |
| 2W | `US2WRP=` | ✅ | ✅ | 2-week Repo |
| 1M | `US1MRP=` | ✅ | ✅ | 1-month Repo |
| 3M | `US3MRP=` | ✅ | ✅ | 3-month Repo |

---

## Interest Rate Swaps (IRS)

### USD IRS (Validated 2026-01-06)

**Pattern**: `USDIRS{tenor}=` - All 10 standard tenors validated

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1Y | `USDIRS1Y=` | ✅ | ✅ | 262 rows |
| 2Y | `USDIRS2Y=` | ✅ | ✅ | 262 rows |
| 3Y | `USDIRS3Y=` | ✅ | ✅ | 262 rows |
| 4Y | `USDIRS4Y=` | ✅ | ✅ | 262 rows |
| 5Y | `USDIRS5Y=` | ✅ | ✅ | 262 rows |
| 7Y | `USDIRS7Y=` | ✅ | ✅ | 262 rows |
| 10Y | `USDIRS10Y=` | ✅ | ✅ | 262 rows |
| 15Y | `USDIRS15Y=` | ✅ | ✅ | 262 rows |
| 20Y | `USDIRS20Y=` | ✅ | ✅ | 262 rows |
| 30Y | `USDIRS30Y=` | ✅ | ✅ | 262 rows |

### EUR IRS (Validated 2026-01-06)

**Pattern**: `EURIRS{tenor}=` - Full curve 1Y-50Y

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1Y | `EURIRS1Y=` | ✅ | ✅ | 262 rows |
| 2Y | `EURIRS2Y=` | ✅ | ✅ | 262 rows |
| 3Y | `EURIRS3Y=` | ✅ | ✅ | 262 rows |
| 4Y | `EURIRS4Y=` | ✅ | ✅ | 262 rows |
| 5Y | `EURIRS5Y=` | ✅ | ✅ | 262 rows |
| 6Y | `EURIRS6Y=` | ✅ | ✅ | 262 rows |
| 7Y | `EURIRS7Y=` | ✅ | ✅ | 262 rows |
| 8Y | `EURIRS8Y=` | ✅ | ✅ | 262 rows |
| 9Y | `EURIRS9Y=` | ✅ | ✅ | 262 rows |
| 10Y | `EURIRS10Y=` | ✅ | ✅ | 262 rows |
| 15Y | `EURIRS15Y=` | ✅ | ✅ | 262 rows |
| 20Y | `EURIRS20Y=` | ✅ | ✅ | 262 rows |
| 25Y | `EURIRS25Y=` | ✅ | ✅ | 262 rows |
| 30Y | `EURIRS30Y=` | ✅ | ✅ | 262 rows |
| 40Y | `EURIRS40Y=` | ✅ | ✅ | 262 rows |
| 50Y | `EURIRS50Y=` | ✅ | ✅ | 262 rows |

### JPY IRS (Validated 2026-01-06)

**Pattern**: `JPYIRS{tenor}=`

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1Y | `JPYIRS1Y=` | ✅ | ✅ | 262 rows |
| 2Y | `JPYIRS2Y=` | ✅ | ✅ | 262 rows |
| 3Y | `JPYIRS3Y=` | ✅ | ✅ | 262 rows |
| 5Y | `JPYIRS5Y=` | ✅ | ✅ | 262 rows |
| 7Y | `JPYIRS7Y=` | ✅ | ✅ | 262 rows |
| 10Y | `JPYIRS10Y=` | ✅ | ✅ | 262 rows |
| 15Y | `JPYIRS15Y=` | ✅ | ✅ | 262 rows |
| 20Y | `JPYIRS20Y=` | ✅ | ✅ | 262 rows |
| 30Y | `JPYIRS30Y=` | ✅ | ✅ | 262 rows |

### CHF IRS (Validated 2026-01-06)

**Pattern**: `CHFIRS{tenor}=`

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1Y | `CHFIRS1Y=` | ✅ | ✅ | 262 rows |
| 2Y | `CHFIRS2Y=` | ✅ | ✅ | 262 rows |
| 3Y | `CHFIRS3Y=` | ✅ | ✅ | 262 rows |
| 5Y | `CHFIRS5Y=` | ✅ | ✅ | 262 rows |
| 7Y | `CHFIRS7Y=` | ✅ | ✅ | 262 rows |
| 10Y | `CHFIRS10Y=` | ✅ | ✅ | 262 rows |
| 15Y | `CHFIRS15Y=` | ✅ | ✅ | 262 rows |
| 20Y | `CHFIRS20Y=` | ✅ | ✅ | 262 rows |
| 30Y | `CHFIRS30Y=` | ✅ | ✅ | 262 rows |

### GBP IRS (Validated 2026-01-06)

**Pattern**: `GBPSB6L{tenor}=` (GBP Swap vs 6-month SONIA) - 17/17 tenors validated

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1Y | `GBPSB6L1Y=` | ✅ | ✅ | 262 rows |
| 2Y | `GBPSB6L2Y=` | ✅ | ✅ | 262 rows |
| 3Y | `GBPSB6L3Y=` | ✅ | ✅ | 262 rows |
| 4Y | `GBPSB6L4Y=` | ✅ | ✅ | 262 rows |
| 5Y | `GBPSB6L5Y=` | ✅ | ✅ | 262 rows |
| 6Y | `GBPSB6L6Y=` | ✅ | ✅ | 262 rows |
| 7Y | `GBPSB6L7Y=` | ✅ | ✅ | 262 rows |
| 8Y | `GBPSB6L8Y=` | ✅ | ✅ | 262 rows |
| 9Y | `GBPSB6L9Y=` | ✅ | ✅ | 262 rows |
| 10Y | `GBPSB6L10Y=` | ✅ | ✅ | 262 rows |
| 12Y | `GBPSB6L12Y=` | ✅ | ✅ | 262 rows |
| 15Y | `GBPSB6L15Y=` | ✅ | ✅ | 262 rows |
| 20Y | `GBPSB6L20Y=` | ✅ | ✅ | 262 rows |
| 25Y | `GBPSB6L25Y=` | ✅ | ✅ | 262 rows |
| 30Y | `GBPSB6L30Y=` | ✅ | ✅ | 262 rows |
| 40Y | `GBPSB6L40Y=` | ✅ | ✅ | 262 rows |
| 50Y | `GBPSB6L50Y=` | ✅ | ✅ | 262 rows |

### CAD/AUD/NZD IRS (Validated 2026-01-06)

**Pattern**: `{ccy}IRS{tenor}=`

| Currency | Available Tenors | Notes |
|----------|-----------------|-------|
| CAD | 1Y-30Y | 8/9 tenors work |
| AUD | 1Y-30Y | 8/9 tenors work |
| NZD | 1Y-30Y | 7/9 tenors work |

---

## FRAs (Forward Rate Agreements)

### USD FRAs

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1x4 | USD1X4 | `USD1X4F=` | ✅ | ✅ | 1M vs 4M |
| 2x5 | USD2X5 | `USD2X5F=` | ✅ | ✅ | 2M vs 5M |
| 3x6 | USD3X6 | `USD3X6F=` | ✅ | ✅ | 3M vs 6M |
| 4x7 | USD4X7 | `USD4X7F=` | ✅ | ✅ | 4M vs 7M |
| 5x8 | USD5X8 | `USD5X8F=` | ✅ | ✅ | 5M vs 8M |
| 6x9 | USD6X9 | `USD6X9F=` | ✅ | ✅ | 6M vs 9M |
| 1x7 | USD1X7 | `USD1X7F=` | ✅ | ✅ | 1M vs 7M |
| 2x8 | USD2X8 | `USD2X8F=` | ✅ | ✅ | 2M vs 8M |
| 3x9 | USD3X9 | `USD3X9F=` | ✅ | ✅ | 3M vs 9M |

---

## Money Market Deposits

### USD Deposits

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| O/N | USDON | `USDOND=` | ✅ | ✅ | Overnight |
| T/N | USDTN | `USDTND=` | ✅ | ✅ | Tom/Next |
| S/W | USDSW | `USDSWD=` | ✅ | ✅ | Spot/Week |
| 1M | USD1M | `USD1MD=` | ✅ | ✅ | 1 Month |
| 3M | USD3M | `USD3MD=` | ✅ | ✅ | 3 Month |
| 6M | USD6M | `USD6MD=` | ✅ | ✅ | 6 Month |
| 9M | USD9M | `USD9MD=` | ✅ | ✅ | 9 Month |
| 1Y | USD1Y | `USD1YD=` | ✅ | ✅ | 1 Year |

---

## Government Bond Yields

### US Treasury Yield Curve (Full)

**Use `=RRPS` suffix** (not `=RR` which returns ACCESS DENIED)

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1M | UST1M | `US1MT=RRPS` | ✅ | ✅ | T-Bill |
| 2M | UST2M | `US2MT=RRPS` | ✅ | ✅ | T-Bill |
| 3M | UST3M | `US3MT=RRPS` | ✅ | ✅ | T-Bill |
| 4M | UST4M | `US4MT=RRPS` | ✅ | ✅ | T-Bill |
| 6M | UST6M | `US6MT=RRPS` | ✅ | ✅ | T-Bill |
| 1Y | UST1Y | `US1YT=RRPS` | ✅ | ✅ | T-Note |
| 2Y | UST2Y | `US2YT=RRPS` | ✅ | ✅ | T-Note |
| 3Y | UST3Y | `US3YT=RRPS` | ✅ | ✅ | T-Note |
| 5Y | UST5Y | `US5YT=RRPS` | ✅ | ✅ | T-Note |
| 7Y | UST7Y | `US7YT=RRPS` | ✅ | ✅ | T-Note |
| 10Y | UST10Y | `US10YT=RRPS` | ✅ | ✅ | T-Note |
| 20Y | UST20Y | `US20YT=RRPS` | ✅ | ✅ | T-Bond |
| 30Y | UST30Y | `US30YT=RRPS` | ✅ | ✅ | T-Bond |

### German Bunds - Full Curve (Validated 2026-01-06)

**Pattern**: `DE{tenor}T=RR` - 9 tenors validated

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1Y | DE1Y | `DE1YT=RR` | ✅ | ✅ | 256 rows |
| 2Y | DE2Y | `DE2YT=RR` | ✅ | ✅ | 256 rows |
| 3Y | DE3Y | `DE3YT=RR` | ✅ | ✅ | 256 rows |
| 5Y | DE5Y | `DE5YT=RR` | ✅ | ✅ | 256 rows |
| 7Y | DE7Y | `DE7YT=RR` | ✅ | ✅ | 256 rows |
| 10Y | DE10Y | `DE10YT=RR` | ✅ | ✅ | 256 rows |
| 15Y | DE15Y | `DE15YT=RR` | ✅ | ✅ | 256 rows |
| 20Y | DE20Y | `DE20YT=RR` | ✅ | ✅ | 256 rows |
| 30Y | DE30Y | `DE30YT=RR` | ✅ | ✅ | 256 rows |

### UK Gilts - Full Curve (Validated 2026-01-06)

**Pattern**: `GB{tenor}T=RR` - 9 tenors validated

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1Y | GB1Y | `GB1YT=RR` | ✅ | ✅ | 252 rows |
| 2Y | GB2Y | `GB2YT=RR` | ✅ | ✅ | 252 rows |
| 3Y | GB3Y | `GB3YT=RR` | ✅ | ✅ | 252 rows |
| 5Y | GB5Y | `GB5YT=RR` | ✅ | ✅ | 252 rows |
| 7Y | GB7Y | `GB7YT=RR` | ✅ | ✅ | 252 rows |
| 10Y | GB10Y | `GB10YT=RR` | ✅ | ✅ | 252 rows |
| 15Y | GB15Y | `GB15YT=RR` | ✅ | ✅ | 252 rows |
| 20Y | GB20Y | `GB20YT=RR` | ✅ | ✅ | 252 rows |
| 30Y | GB30Y | `GB30YT=RR` | ✅ | ✅ | 252 rows |

### French OATs - Full Curve (Validated 2026-01-06)

**Pattern**: `FR{tenor}T=RR` - 9 tenors validated

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1Y | FR1Y | `FR1YT=RR` | ✅ | ✅ | 256 rows |
| 2Y | FR2Y | `FR2YT=RR` | ✅ | ✅ | 256 rows |
| 3Y | FR3Y | `FR3YT=RR` | ✅ | ✅ | 256 rows |
| 5Y | FR5Y | `FR5YT=RR` | ✅ | ✅ | 256 rows |
| 7Y | FR7Y | `FR7YT=RR` | ✅ | ✅ | 256 rows |
| 10Y | FR10Y | `FR10YT=RR` | ✅ | ✅ | 256 rows |
| 15Y | FR15Y | `FR15YT=RR` | ✅ | ✅ | 256 rows |
| 20Y | FR20Y | `FR20YT=RR` | ✅ | ✅ | 256 rows |
| 30Y | FR30Y | `FR30YT=RR` | ✅ | ✅ | 256 rows |

### Italian BTPs - Full Curve (Validated 2026-01-06)

**Pattern**: `IT{tenor}T=RR` - 9 tenors validated

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1Y | IT1Y | `IT1YT=RR` | ✅ | ✅ | 255 rows |
| 2Y | IT2Y | `IT2YT=RR` | ✅ | ✅ | 255 rows |
| 3Y | IT3Y | `IT3YT=RR` | ✅ | ✅ | 256 rows |
| 5Y | IT5Y | `IT5YT=RR` | ✅ | ✅ | 256 rows |
| 7Y | IT7Y | `IT7YT=RR` | ✅ | ✅ | 256 rows |
| 10Y | IT10Y | `IT10YT=RR` | ✅ | ✅ | 256 rows |
| 15Y | IT15Y | `IT15YT=RR` | ✅ | ✅ | 256 rows |
| 20Y | IT20Y | `IT20YT=RR` | ✅ | ✅ | 256 rows |
| 30Y | IT30Y | `IT30YT=RR` | ✅ | ✅ | 256 rows |

### Canadian Government - Full Curve (Validated 2026-01-06)

**Pattern**: `CA{tenor}T=RR` - 8 tenors validated

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1Y | CA1Y | `CA1YT=RR` | ✅ | ✅ | 250 rows |
| 2Y | CA2Y | `CA2YT=RR` | ✅ | ✅ | 250 rows |
| 3Y | CA3Y | `CA3YT=RR` | ✅ | ✅ | 250 rows |
| 5Y | CA5Y | `CA5YT=RR` | ✅ | ✅ | 250 rows |
| 7Y | CA7Y | `CA7YT=RR` | ✅ | ✅ | 250 rows |
| 10Y | CA10Y | `CA10YT=RR` | ✅ | ✅ | 250 rows |
| 20Y | CA20Y | `CA20YT=RR` | ✅ | ✅ | 249 rows |
| 30Y | CA30Y | `CA30YT=RR` | ✅ | ✅ | 249 rows |

### Japan JGBs (Validated 2026-01-06)

**Pattern**: `JP{tenor}T=RR` - **Requires JGB data package (access_denied)**

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 2Y | JP2Y | `JP2YT=RR` | ⛔ | ⛔ | Access Denied |
| 5Y | JP5Y | `JP5YT=RR` | ⛔ | ⛔ | Access Denied |
| 10Y | JP10Y | `JP10YT=RR` | ⛔ | ⛔ | Access Denied |
| 30Y | JP30Y | `JP30YT=RR` | ⛔ | ⛔ | Access Denied |

**Note**: JGB yields require additional LSEG permissions (JGB data package). The RIC pattern exists but returns "access_denied" in basic tier. JGB futures (`JGBc1`) and JPY OIS/IRS **do work**.

### Eurozone Sovereigns (Validated 2026-01-06)

**Pattern**: `{CC}{tenor}T=RR` where CC = 2-letter country code

| Country | 2Y | 5Y | 10Y | 30Y | Status |
|---------|----|----|-----|-----|--------|
| Germany (DE) | `DE2YT=RR` | `DE5YT=RR` | `DE10YT=RR` | `DE30YT=RR` | ✅ All tenors |
| France (FR) | `FR2YT=RR` | `FR5YT=RR` | `FR10YT=RR` | `FR30YT=RR` | ✅ All tenors |
| Italy (IT) | `IT2YT=RR` | `IT5YT=RR` | `IT10YT=RR` | `IT30YT=RR` | ✅ All tenors |
| Spain (ES) | `ES2YT=RR` | `ES5YT=RR` | `ES10YT=RR` | `ES30YT=RR` | ✅ All tenors |
| Netherlands (NL) | `NL2YT=RR` | `NL5YT=RR` | `NL10YT=RR` | `NL30YT=RR` | ✅ All tenors |
| Belgium (BE) | `BE2YT=RR` | `BE5YT=RR` | `BE10YT=RR` | `BE30YT=RR` | ✅ All tenors |
| Austria (AT) | `AT2YT=RR` | `AT5YT=RR` | `AT10YT=RR` | `AT30YT=RR` | ✅ All tenors |
| Portugal (PT) | `PT2YT=RR` | `PT5YT=RR` | `PT10YT=RR` | `PT30YT=RR` | ✅ All tenors |
| Ireland (IE) | `IE2YT=RR` | `IE5YT=RR` | `IE10YT=RR` | `IE30YT=RR` | ✅ All tenors |
| Greece (GR) | `GR2YT=RR` | `GR5YT=RR` | `GR10YT=RR` | `GR30YT=RR` | ✅ All tenors |
| Finland (FI) | `FI2YT=RR` | `FI5YT=RR` | `FI10YT=RR` | `FI30YT=RR` | ✅ All tenors |

### Australian Government (Validated 2026-01-06)

**Pattern**: `AU{tenor}T=RR` - 6 tenors validated

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 2Y | AU2Y | `AU2YT=RR` | ✅ | ✅ | 254 rows |
| 3Y | AU3Y | `AU3YT=RR` | ✅ | ✅ | 254 rows |
| 5Y | AU5Y | `AU5YT=RR` | ✅ | ✅ | 254 rows |
| 10Y | AU10Y | `AU10YT=RR` | ✅ | ✅ | 254 rows |
| 15Y | AU15Y | `AU15YT=RR` | ✅ | ✅ | 254 rows |
| 30Y | AU30Y | `AU30YT=RR` | ✅ | ✅ | 254 rows |

### Swiss Confederation (Validated 2026-01-06)

**Pattern**: `CH{tenor}T=RR` - 4 tenors validated

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 2Y | CH2Y | `CH2YT=RR` | ✅ | ✅ | 250 rows |
| 5Y | CH5Y | `CH5YT=RR` | ✅ | ✅ | 250 rows |
| 10Y | CH10Y | `CH10YT=RR` | ✅ | ✅ | 250 rows |
| 30Y | CH30Y | `CH30YT=RR` | ✅ | ✅ | 250 rows |

---

## Commodity Futures (Validated 2026-01-06)

**All 24 commodity futures validated: 24/24 working**

### Energy (NYMEX/ICE)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| WTI Crude | CL | `CLc1` | ✅ | ✅ | ✅ | NYMEX, 256 rows |
| Brent Crude | BRN | `LCOc1` | ✅ | ✅ | ✅ | ICE Europe, 261 rows |
| Natural Gas | NG | `NGc1` | ✅ | ✅ | ✅ | NYMEX, 252 rows |
| RBOB Gasoline | RB | `RBc1` | ✅ | ✅ | ✅ | NYMEX, 254 rows |
| Heating Oil | HO | `HOc1` | ✅ | ✅ | ✅ | NYMEX, 253 rows |
| Gasoil ICE | LGO | `LGOc1` | ✅ | ✅ | ✅ | ICE Europe, 262 rows |

### Metals (COMEX/NYMEX)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Gold | GC | `GCc1` | ✅ | ✅ | ✅ | COMEX, 256 rows |
| Silver | SI | `SIc1` | ✅ | ✅ | ✅ | COMEX, 256 rows |
| Copper | HG | `HGc1` | ✅ | ✅ | ✅ | COMEX, 255 rows |
| Platinum | PL | `PLc1` | ✅ | ✅ | ✅ | NYMEX, 256 rows |
| Palladium | PA | `PAc1` | ✅ | ✅ | ✅ | NYMEX, 256 rows |

### Grains (CBOT)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Corn | ZC | `Cc1` | ✅ | ✅ | ✅ | CBOT, 257 rows |
| Wheat (SRW) | ZW | `Wc1` | ✅ | ✅ | ✅ | CBOT, 255 rows |
| Soybeans | ZS | `Sc1` | ✅ | ✅ | ✅ | CBOT, 256 rows |
| Soybean Oil | ZL | `BOc1` | ✅ | ✅ | ✅ | CBOT, 257 rows |
| Soybean Meal | ZM | `SMc1` | ✅ | ✅ | ✅ | CBOT, 256 rows |
| KC HRW Wheat | KE | `KWc1` | ✅ | ✅ | ✅ | CBOT, 253 rows |

### Softs (ICE US)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Coffee "C" | KC | `KCc1` | ✅ | ✅ | ✅ | ICE US, 257 rows |
| Sugar No. 11 | SB | `SBc1` | ✅ | ✅ | ✅ | ICE US, 254 rows |
| Cocoa | CC | `CCc1` | ✅ | ✅ | ✅ | ICE US, 256 rows |
| Cotton No. 2 | CT | `CTc1` | ✅ | ✅ | ✅ | ICE US, 255 rows |

### Livestock (CME)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Live Cattle | LE | `LCc1` | ✅ | ✅ | ✅ | CME, 255 rows |
| Feeder Cattle | GF | `FCc1` | ✅ | ✅ | ✅ | CME, 255 rows |
| Lean Hogs | HE | `LHc1` | ✅ | ✅ | ✅ | CME, 255 rows |

---

## Equities (Validated 2026-01-06)

### RIC Patterns by Exchange

| Exchange | Pattern | Example |
|----------|---------|---------|
| NASDAQ | `{ticker}.O` | `AAPL.O` |
| NYSE | `{ticker}.N` | `JPM.N` |
| LSE | `{ticker}.L` | `HSBA.L` |
| Xetra | `{ticker}n.DE` | `DTEGn.DE` |
| Euronext Paris | `{ticker}.PA` | `LVMH.PA` |
| Tokyo | `{code}.T` | `7203.T` |
| Hong Kong | `{code}.HK` | `0700.HK` |

### US Stocks

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| Apple | `AAPL.O` | ✅ | ✅ | 252 rows, OHLCV + VWAP |
| Microsoft | `MSFT.O` | ✅ | ✅ | NASDAQ |
| Alphabet | `GOOGL.O` | ✅ | ✅ | NASDAQ |
| Amazon | `AMZN.O` | ✅ | ✅ | NASDAQ |
| JPMorgan | `JPM.N` | ✅ | ✅ | NYSE |
| Goldman Sachs | `GS.N` | ✅ | ✅ | NYSE |
| Berkshire | `BRKa.N` | ✅ | ✅ | NYSE |
| Exxon | `XOM.N` | ✅ | ✅ | NYSE |

**Stock History Fields:** `TRDPRC_1`, `HIGH_1`, `LOW_1`, `OPEN_PRC`, `ACVOL_UNS`, `BID`, `ASK`, `VWAP`, `TRNOVR_UNS`, `NUM_MOVES`

### European Stocks

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| HSBC | `HSBA.L` | ✅ | ✅ | LSE |
| Shell | `SHEL.L` | ✅ | ✅ | LSE |
| BP | `BP.L` | ✅ | ✅ | LSE |
| Deutsche Telekom | `DTEGn.DE` | ✅ | ✅ | Xetra |
| LVMH | `LVMH.PA` | ✅ | ✅ | Euronext Paris |

### Asian Stocks

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| Toyota | `7203.T` | ✅ | ✅ | Tokyo |
| SoftBank | `9984.T` | ✅ | ✅ | Tokyo |
| Sony | `6758.T` | ✅ | ✅ | Tokyo |
| Tencent | `0700.HK` | ✅ | ✅ | Hong Kong |
| Alibaba | `9988.HK` | ✅ | ✅ | Hong Kong |

### Stock Indices (Cash)

| Index | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| S&P 500 | `.SPX` | ✅ | ✅ | 6944.82 |
| Dow Jones | `.DJI` | ✅ | ✅ | |
| NASDAQ Composite | `.IXIC` | ✅ | ✅ | |
| FTSE 100 | `.FTSE` | ✅ | ✅ | |
| DAX | `.GDAXI` | ✅ | ✅ | |
| CAC 40 | `.FCHI` | ✅ | ✅ | |
| Nikkei 225 | `.N225` | ✅ | ✅ | |
| Hang Seng | `.HSI` | ✅ | ✅ | |
| Euro Stoxx 50 | `.STOXX50E` | ✅ | ✅ | |

### Individual Corporate Bonds (Validated 2026-01-06)

**Pattern**: `{CUSIP}=` (CUSIP-based RICs work!)

| Bond | LSEG RIC | Status | Daily | Notes |
|------|----------|--------|-------|-------|
| Apple 3.85% 2029 | `037833EB2=` | ✅ | ✅ | 261 rows |
| Apple 2.45% 2026 | `037833BY5=` | ✅ | ✅ | CUSIP-based |
| MSFT bonds | `{MSFT CUSIP}=` | ✅ | ✅ | Search to find CUSIP |
| JPM bonds | `{JPM CUSIP}=` | ✅ | ✅ | Search to find CUSIP |

**To Find Corporate Bond RICs:**
```python
# Use LSEG search to find bond CUSIPs
rd.discovery.search(query="Apple corporate bond", top=10, select="RIC,DocumentTitle")
# Returns RICs like: 037833EB2=, 037833BY5=, etc.
```

**Corporate Bond Historical Fields:**
| Category | Fields |
|----------|--------|
| **Yields** | `B_YLD_1`, `A_YLD_1`, `MID_YLD_1`, `YLDTOMAT`, `HIGH_YLD`, `LOW_YLD`, `OPEN_YLD` |
| **Prices** | `BID`, `ASK`, `MID_PRICE`, `DIRTY_PRC`, `CLEAN_PRC` |
| **Spreads** | `AST_SWPSPD`, `BMK_SPD`, `ZSPREAD`, `OAS_BID`, `OIS_SPREAD`, `TED_SPREAD`, `INT_GV_SPD` |
| **Risk** | `CONVEXITY`, `MOD_DURTN`, `BPV` |
| **Accrued** | `ACCR_INT` |

### Credit/Bond Indices (Validated 2026-01-06)

| Index | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| CSI Credit Bond 0-1Y | `.CSI931709` | ✅ | ✅ | 242 rows, OHLCV |
| CSI Credit Bond 1-3Y | `.CSI931710` | ✅ | ✅ | OHLCV available |
| ICE US Treasury 20+Y | `.IDCOT20TR` | ✅ | ✅ | 252 rows, OHLC |
| ICE US Treasury 7-10Y | `.IDCOT7TR` | ✅ | ✅ | OHLC available |
| CDX/Cboe IG Volatility | `.VIXIG` | ✅ | ⛔ | Name only (no price data) |
| iTraxx/Cboe Europe Vol | `.VIXIE` | ✅ | ⛔ | Name only (no price data) |

### NOT Working (with current subscription)

| Category | Tried | Result |
|----------|-------|--------|
| Bloomberg/ICE indices | `.LUACTRUU`, `BAMLC0A0CM` | Not found |
| OAS spread indices | `USIGOAS=`, `USHYOAS=` | Not found |
| Municipal bonds | `USMUNI=`, `.LMBITR` | Not found |
| Agency bonds | `FNMA=`, `FHLMC=` | Not found |
| MBS indices | `.LUMSTRUU`, `USMBS=` | Not found |
| Single-name CDS | `AAPL5YCDS=` | Not found |

**Note**: Individual corporate bonds are accessible via CUSIP-based RICs. Use LSEG search to find specific bond CUSIPs.

---

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

## Credit (Validated 2026-01-06)

### CDX Indices (North America)

**Pattern**: `CDX{IG|HY}{tenor}=` - Working with rich historical data

| Index | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| CDX IG 1Y | `CDXIG1Y=` | ✅ | ✅ | 228 rows |
| CDX IG 3Y | `CDXIG3Y=` | ✅ | ✅ | Investment Grade |
| CDX IG 5Y | `CDXIG5Y=` | ✅ | ✅ | Main benchmark |
| CDX IG 7Y | `CDXIG7Y=` | ✅ | ✅ | |
| CDX IG 10Y | `CDXIG10Y=` | ✅ | ✅ | |
| CDX HY 3Y | `CDXHY3Y=` | ✅ | ✅ | High Yield |
| CDX HY 5Y | `CDXHY5Y=` | ✅ | ✅ | Main benchmark |
| CDX HY 7Y | `CDXHY7Y=` | ✅ | ✅ | |
| CDX HY 10Y | `CDXHY10Y=` | ✅ | ✅ | |

**CDX Fields Available:**
- `MID_SPREAD`, `BID_SPREAD`, `ASK_SPREAD` - spread quotes (bp)
- `OPEN_PRC`, `HIGH_1`, `LOW_1`, `BID`, `ASK` - price/OHLC
- `DEFLT_PROB` - implied default probability
- `CDS_DV01` - spread DV01
- `RECOV_RATE` - recovery rate assumption (typically 40%)
- `ZSPREAD`, `SWAP_SPRD`, `CDS_BASIS` - relative value metrics

### iTraxx Indices (Europe)

| Index | LSEG RIC | Status | Notes |
|-------|----------|--------|-------|
| iTraxx Europe 5Y | `?` | ❌ | Pattern not found |
| iTraxx Crossover 5Y | `?` | ❌ | Pattern not found |

**Note**: iTraxx RIC patterns not identified. May require different naming convention or data tier.

### Sovereign CDS (Validated 2026-01-06)

**Pattern**: `{CC}GVCUSD5Y=` (CDS-derived 5Y USD point)

**All 17 sovereigns validated with historical data (260 rows)**

| Country | LSEG RIC | Status | Daily | Notes |
|---------|----------|--------|-------|-------|
| **G7** | | | | |
| United States | `USGVCUSD5Y=` | ✅ | ✅ | US Treasury |
| Germany | `DEGVCUSD5Y=` | ✅ | ✅ | |
| United Kingdom | `GBGVCUSD5Y=` | ✅ | ✅ | |
| France | `FRGVCUSD5Y=` | ✅ | ✅ | |
| Japan | `JPGVCUSD5Y=` | ✅ | ✅ | |
| **Eurozone** | | | | |
| Italy | `ITGVCUSD5Y=` | ✅ | ✅ | |
| Spain | `ESGVCUSD5Y=` | ✅ | ✅ | |
| Portugal | `PTGVCUSD5Y=` | ✅ | ✅ | |
| Greece | `GRGVCUSD5Y=` | ✅ | ✅ | |
| Ireland | `IEGVCUSD5Y=` | ✅ | ✅ | |
| **Emerging Markets** | | | | |
| Brazil | `BRGVCUSD5Y=` | ✅ | ✅ | |
| Mexico | `MXGVCUSD5Y=` | ✅ | ✅ | |
| South Africa | `ZAGVCUSD5Y=` | ✅ | ✅ | |
| Turkey | `TRGVCUSD5Y=` | ✅ | ✅ | |
| China | `CNGVCUSD5Y=` | ✅ | ✅ | |
| Russia | `RUGVCUSD5Y=` | ✅ | ✅ | |
| Saudi Arabia | `SAGVCUSD5Y=` | ✅ | ✅ | |

**Historical Fields**: `HIGH_PYLD`, `OPEN_PYLD`, `LOW_PYLD`, `ZERO_YLD1`, `PAR_YLD1`, `AST_SWPSPD`

---

## OAS & Spread Analytics (Validated 2026-01-06)

### Corporate Bond Spreads ✅

OAS and spread fields are available on individual corporate bonds with full historical data.

**Working Fields on Corporate Bonds:**

| Field | Description | Example Value |
|-------|-------------|---------------|
| `OAS_BID` | Option-Adjusted Spread (bid) | 3.24 bp |
| `AST_SWPSPD` | Asset Swap Spread | 0.48 |
| `SWAP_SPRD` | Swap Spread | 25.15 bp |
| `BMK_SPD` | Benchmark Spread (vs Treasury) | 24.29 bp |
| `INT_GV_SPD` | Interpolated Govt Spread | 20.52 |
| `ZSPREAD` | Z-Spread | 20.20 bp |

**Historical Data**: Full year available (262 rows for 2024)

```python
# Example: Get OAS history for Apple bond
rd.get_history('037833EB2=',
    fields=['OAS_BID', 'ZSPREAD', 'AST_SWPSPD', 'BMK_SPD'],
    start='2024-01-01', end='2024-12-31')
```

### Credit Spread Indices

| Index | LSEG RIC | Status | Notes |
|-------|----------|--------|-------|
| S&P 500 Bond AA IG OAS | `.SP5SI2AO` | ✅ | Snapshot only, no history |
| S&P 500 Bond A IG OAS | `.SP5SI1AO` | ✅ | Snapshot only |
| S&P 500 Bond AAA IG OAS | `.SP5SI3AO` | ✅ | Snapshot only |
| S&P 500 Bond 10+ Yr IG OAS | `.SP5SI10O` | ✅ | Snapshot only |
| BBVA US/EU IG Credit Spread | `.BBXTUICU` | ⛔ | Access Denied |

**Note**: S&P Bond indices exist but lack price/history data in current tier.

---

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

Conversion factors must be calculated or obtained from CME. See `docs/BOND_BASIS_RICS.md`.

**Historical CF Considerations:**
- Current era (2020s): Low coupons (3-5%) → CFs typically 0.85-0.95
- Historical era (1980s-90s): High coupons (8%+) → CFs could be > 1.0
- When fetching historical basis data, must use the CF that was in effect at that time
- CME publishes historical CF lookup tables by contract delivery month
- The coupon rate of deliverable bonds changes the CF significantly

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
