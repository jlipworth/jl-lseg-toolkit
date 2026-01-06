# Instruments Support List

Reference document for supported instruments and roadmap.

**Legend**: ✅ Validated | 🔄 Planned | ❓ Needs Research | ❌ Not Available

---

## Symbol Mapping: CME → LSEG

### Treasury Futures (Complete Curve)

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| ZT | TU | 2-Year T-Note Future |
| Z3N | Z3N | 3-Year T-Note Future |
| ZF | FV | 5-Year T-Note Future |
| ZN | TY | 10-Year T-Note Future |
| TN | TN | Ultra 10-Year T-Note |
| TWE | TWE | 20-Year T-Bond Future |
| ZB | US | 30-Year T-Bond Future |
| UB | UB | Ultra 30-Year T-Bond |

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

### US Treasury Futures (Complete Curve)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| 2Y T-Note | ZT | `TUc1` | ✅ | ✅ | ❓ | Continuous |
| 3Y T-Note | Z3N | `Z3Nc1` | 🔄 | ❓ | ❓ | Needs validation |
| 5Y T-Note | ZF | `FVc1` | 🔄 | ❓ | ❓ | Needs validation |
| 10Y T-Note | ZN | `TYc1` | ✅ | ✅ | ❓ | Continuous front month |
| Ultra 10Y | TN | `TNc1` | 🔄 | ❓ | ❓ | Needs validation |
| 20Y T-Bond | TWE | `TWEc1` | 🔄 | ❓ | ❓ | Needs validation |
| 30Y T-Bond | ZB | `USc1` | ✅ | ✅ | ❓ | Continuous |
| Ultra 30Y | UB | `UBc1` | 🔄 | ❓ | ❓ | Needs validation |

### European Bond Futures

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Euro-Bund 10Y | FGBL | `FGBLc1` | ✅ | ✅ | ❓ | German 10Y |
| Euro-Bobl 5Y | FGBM | `FGBMc1` | ✅ | ✅ | ❓ | German 5Y |
| Euro-Schatz 2Y | FGBS | `FGBSc1` | ✅ | ✅ | ❓ | German 2Y |
| Euro-Buxl 30Y | FGBX | `FGBXc1` | 🔄 | ❓ | ❓ | German 30Y |
| Euro-OAT 10Y | FOAT | `FOATc1` | 🔄 | ❓ | ❓ | French 10Y |
| Euro-BTP 10Y | FBTP | `FBTPc1` | 🔄 | ❓ | ❓ | Italian 10Y |
| UK Long Gilt | FLG | `FLGc1` | 🔄 | ❓ | ❓ | UK 10Y |
| UK Short Gilt | FSS | `FSSc1` | 🔄 | ❓ | ❓ | UK 2Y |

### Asian Bond Futures

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| JGB 10Y | JB | `JBc1` | ❌ | ❌ | ❌ | RIC not found - needs research |
| JGB Mini 10Y | JBM | `JMc1` | 🔄 | ❓ | ❓ | Needs validation |
| Australia 3Y | YT | `YTc1` | 🔄 | ❓ | ❓ | Needs validation |
| Australia 10Y | XM | `XMc1` | 🔄 | ❓ | ❓ | Needs validation |

### Canadian Bond Futures

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Canada 10Y | CGB | `CGBc1` | 🔄 | ❓ | ❓ | Needs validation |
| Canada 5Y | CGF | `CGFc1` | 🔄 | ❓ | ❓ | Needs validation |
| Canada 2Y | CGZ | `CGZc1` | 🔄 | ❓ | ❓ | Needs validation |

---

## STIR Futures (Short-Term Interest Rate)

### USD STIR

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| 3M SOFR | SR3 | `SRAc1` | 🔄 | ❓ | ❓ | CME 3-month SOFR |
| 1M SOFR | SR1 | `SR1c1` | 🔄 | ❓ | ❓ | CME 1-month SOFR |
| Fed Funds | FF | `FFc1` | 🔄 | ❓ | ❓ | CBOT 30-Day Fed Funds |

### EUR STIR

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| 3M Euribor | FEI | `FEIc1` | 🔄 | ❓ | ❓ | ICE Europe |

### GBP STIR

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| SONIA Future | FSS | `FSSc1` | 🔄 | ❓ | ❓ | ICE Europe |

---

## Stock Index Futures

### US Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| E-mini S&P 500 | ES | `ESc1` | 🔄 | ❓ | ❓ | CME |
| E-mini Nasdaq-100 | NQ | `NQc1` | 🔄 | ❓ | ❓ | CME |
| E-mini Russell 2000 | RTY | `RTYc1` | 🔄 | ❓ | ❓ | CME |
| E-mini Dow | YM | `YMc1` | 🔄 | ❓ | ❓ | CBOT |
| Micro E-mini S&P 500 | MES | `MESc1` | 🔄 | ❓ | ❓ | CME |
| Micro E-mini Nasdaq | MNQ | `MNQc1` | 🔄 | ❓ | ❓ | CME |

### European Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Euro Stoxx 50 | FESX | `STXEc1` | 🔄 | ❓ | ❓ | Eurex |
| DAX | FDAX | `FDXc1` | 🔄 | ❓ | ❓ | Eurex |
| FTSE 100 | Z | `FFIc1` | 🔄 | ❓ | ❓ | ICE Europe |
| CAC 40 | FCE | `FCEc1` | 🔄 | ❓ | ❓ | Euronext |

### Asian Indices

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Nikkei 225 (Osaka) | NK | `JNIc1` | 🔄 | ❓ | ❓ | OSE |
| Nikkei 225 (CME USD) | NKD | `NKDc1` | 🔄 | ❓ | ❓ | CME |
| Nikkei 225 (SGX) | SGN | `SSIc1` | 🔄 | ❓ | ❓ | SGX |
| Hang Seng | HSI | `HSIc1` | 🔄 | ❓ | ❓ | HKEX |
| SGX Nifty 50 | IN | `INc1` | 🔄 | ❓ | ❓ | SGX |
| KOSPI 200 | K200 | `KS200c1` | 🔄 | ❓ | ❓ | KRX |

---

## FX Spot

### Major Pairs

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| EUR/USD | EURUSD | `EUR=` | ✅ | ✅ | ❓ | |
| GBP/USD | GBPUSD | `GBP=` | ✅ | ✅ | ❓ | |
| USD/JPY | USDJPY | `JPY=` | ✅ | ✅ | ❓ | |
| USD/CHF | USDCHF | `CHF=` | ✅ | ✅ | ❓ | |
| AUD/USD | AUDUSD | `AUD=` | ✅ | ✅ | ❓ | |
| USD/CAD | USDCAD | `CAD=` | ✅ | ✅ | ❓ | |
| NZD/USD | NZDUSD | `NZD=` | 🔄 | ❓ | ❓ | Needs validation |

### Cross Rates

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| EUR/GBP | EURGBP | `EURGBP=` | ✅ | ✅ | ❓ | |
| EUR/JPY | EURJPY | `EURJPY=` | ✅ | ✅ | ❓ | |
| EUR/CHF | EURCHF | `EURCHF=` | 🔄 | ❓ | ❓ | |
| GBP/JPY | GBPJPY | `GBPJPY=` | 🔄 | ❓ | ❓ | |
| AUD/JPY | AUDJPY | `AUDJPY=` | 🔄 | ❓ | ❓ | |
| EUR/AUD | EURAUD | `EURAUD=` | 🔄 | ❓ | ❓ | |

### Emerging Markets

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| USD/MXN | USDMXN | `MXN=` | 🔄 | ❓ | ❓ | |
| USD/BRL | USDBRL | `BRL=` | 🔄 | ❓ | ❓ | |
| USD/ZAR | USDZAR | `ZAR=` | 🔄 | ❓ | ❓ | |
| USD/TRY | USDTRY | `TRY=` | 🔄 | ❓ | ❓ | |
| USD/INR | USDINR | `INR=` | 🔄 | ❓ | ❓ | |
| USD/CNH | USDCNH | `CNH=` | 🔄 | ❓ | ❓ | Offshore CNY |
| USD/SGD | USDSGD | `SGD=` | 🔄 | ❓ | ❓ | |
| USD/HKD | USDHKD | `HKD=` | 🔄 | ❓ | ❓ | |
| USD/KRW | USDKRW | `KRW=` | 🔄 | ❓ | ❓ | |

---

## FX Futures (CME)

| Pair | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------|--------|----------|--------|-------|----------|-------|
| EUR/USD | 6E | `UROc1` | 🔄 | ❓ | ❓ | CME Euro FX |
| GBP/USD | 6B | `BPc1` | 🔄 | ❓ | ❓ | CME British Pound |
| JPY/USD | 6J | `JYc1` | 🔄 | ❓ | ❓ | CME Japanese Yen |
| AUD/USD | 6A | `ADc1` | 🔄 | ❓ | ❓ | CME Australian Dollar |
| CAD/USD | 6C | `CDc1` | 🔄 | ❓ | ❓ | CME Canadian Dollar |
| CHF/USD | 6S | `SFc1` | 🔄 | ❓ | ❓ | CME Swiss Franc |

---

## FX Forwards

### EUR/USD Forwards

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1M | EURUSD1M | `EUR1M=` | ✅ | ✅ | |
| 3M | EURUSD3M | `EUR3M=` | ✅ | ✅ | |
| 6M | EURUSD6M | `EUR6M=` | ✅ | ✅ | |
| 1Y | EURUSD1Y | `EUR1Y=` | ✅ | ✅ | |

### GBP/USD Forwards

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1M | GBPUSD1M | `GBP1M=` | ✅ | ✅ | |
| 3M | GBPUSD3M | `GBP3M=` | 🔄 | ❓ | |
| 6M | GBPUSD6M | `GBP6M=` | 🔄 | ❓ | |
| 1Y | GBPUSD1Y | `GBP1Y=` | 🔄 | ❓ | |

### USD/JPY Forwards

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 1M | USDJPY1M | `JPY1M=` | ✅ | ✅ | |
| 3M | USDJPY3M | `JPY3M=` | 🔄 | ❓ | |
| 6M | USDJPY6M | `JPY6M=` | 🔄 | ❓ | |
| 1Y | USDJPY1Y | `JPY1Y=` | 🔄 | ❓ | |

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

### EUR ESTR OIS

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `EUR1MOIS=` | 🔄 | ❓ | |
| 3M | `EUR3MOIS=` | 🔄 | ❓ | |
| 6M | `EUR6MOIS=` | 🔄 | ❓ | |
| 1Y | `EUR1YOIS=` | 🔄 | ❓ | |
| 2Y | `EUR2YOIS=` | 🔄 | ❓ | |
| 5Y | `EUR5YOIS=` | 🔄 | ❓ | |
| 10Y | `EUR10YOIS=` | 🔄 | ❓ | |
| 30Y | `EUR30YOIS=` | 🔄 | ❓ | |

### GBP SONIA OIS

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `GBP1MOIS=ICAP` | 🔄 | ❓ | Different contributor |
| 3M | `GBP3MOIS=ICAP` | 🔄 | ❓ | |
| 6M | `GBP6MOIS=ICAP` | 🔄 | ❓ | |
| 1Y | `GBP1YOIS=ICAP` | 🔄 | ❓ | |
| 2Y | `GBP2YOIS=ICAP` | 🔄 | ❓ | |
| 5Y | `GBP5YOIS=ICAP` | 🔄 | ❓ | |
| 10Y | `GBP10YOIS=ICAP` | 🔄 | ❓ | |

### JPY TONA OIS

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1M | `JPY1MOIS=` | 🔄 | ❓ | |
| 3M | `JPY3MOIS=` | 🔄 | ❓ | |
| 1Y | `JPY1YOIS=` | 🔄 | ❓ | |
| 5Y | `JPY5YOIS=` | 🔄 | ❓ | |
| 10Y | `JPY10YOIS=` | 🔄 | ❓ | |

---

## Overnight Benchmark Rates

### USD - SOFR

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| SOFR Fixing | `USDSOFR=` | ✅ | ✅ | NY Fed secured overnight rate |
| SOFR 30-Day Avg | `SOFR1MAVG=` | 🔄 | ❓ | 30-day compounded average |
| Fed Funds Effective | `USONFFE=` | ✅ | ✅ | Fed Funds Composite |

### EUR - ESTR (€STR)

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| ESTR Fixing | `EUROSTR=` | 🔄 | ❓ | ECB overnight rate |
| EONIA (legacy) | `EONIA=` | 🔄 | ❓ | Replaced by ESTR |

### GBP - SONIA

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| SONIA Fixing | `SONIAOSR=` | 🔄 | ❓ | BoE administered rate |

### CHF - SARON

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| SARON Fixing | `/SARON.S` | 🔄 | ❓ | Uses TRDPRC_1 field |

### JPY - TONA

| Instrument | LSEG RIC | Status | Daily | Notes |
|------------|----------|--------|-------|-------|
| TONA Fixing | `JPYTONAO/N=` | 🔄 | ❓ | Tokyo Overnight Average |

---

## EURIBOR (Euro Interbank Offered Rate)

### EURIBOR Fixings

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1W | `EURIBOR1WD=` | 🔄 | ❓ | 1-week EURIBOR |
| 1M | `EURIBOR1MD=` | 🔄 | ❓ | 1-month EURIBOR |
| 3M | `EURIBOR3MD=` | 🔄 | ❓ | 3-month EURIBOR |
| 6M | `EURIBOR6MD=` | 🔄 | ❓ | 6-month EURIBOR |
| 12M | `EURIBOR1YD=` | 🔄 | ❓ | 12-month EURIBOR |

### EURIBOR Futures (ICE/Eurex)

| Instrument | Symbol | LSEG RIC | Status | Daily | Notes |
|------------|--------|----------|--------|-------|-------|
| 3M EURIBOR | FEI | `FEIc1` | 🔄 | ❓ | Continuous front month |
| Chain | - | `0#FEI:` | 🔄 | ❓ | All contracts |

---

## Interest Rate Swaps (IRS)

### USD IRS

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 2Y | `USD2YAB=` | 🔄 | ❓ | SOFR-based |
| 5Y | `USD5YAB=` | 🔄 | ❓ | |
| 10Y | `USD10YAB=` | 🔄 | ❓ | |
| 30Y | `USD30YAB=` | 🔄 | ❓ | |

### EUR IRS

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 2Y | `EUR2YAB=` | 🔄 | ❓ | ESTR-based |
| 5Y | `EUR5YAB=` | 🔄 | ❓ | |
| 10Y | `EUR10YAB=` | 🔄 | ❓ | |
| 30Y | `EUR30YAB=` | 🔄 | ❓ | |

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

### German Bunds

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 2Y | DE2Y | `DE2YT=RR` | ❌ | ❌ | Try =RRPS? |
| 5Y | DE5Y | `DE5YT=RR` | ❌ | ❌ | Try =RRPS? |
| 10Y | DE10Y | `DE10YT=RR` | ❌ | ❌ | Try =RRPS? |

### UK Gilts

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 10Y | GB10Y | `GB10YT=RR` | ❌ | ❌ | Try =RRPS? |

### Japan JGBs

| Tenor | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| 10Y | JP10Y | `JP10YT=RR` | ❌ | ❌ | Try =RRPS? |

---

## Commodity Futures

### Energy (NYMEX/ICE)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| WTI Crude | CL | `CLc1` | 🔄 | ❓ | ❓ | NYMEX |
| Brent Crude | BRN | `LCOc1` | 🔄 | ❓ | ❓ | ICE Europe |
| Natural Gas | NG | `NGc1` | 🔄 | ❓ | ❓ | NYMEX |
| RBOB Gasoline | RB | `RBc1` | 🔄 | ❓ | ❓ | NYMEX |
| Heating Oil | HO | `HOc1` | 🔄 | ❓ | ❓ | NYMEX |

### Metals (COMEX)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Gold | GC | `GCc1` | 🔄 | ❓ | ❓ | COMEX |
| Silver | SI | `SIc1` | 🔄 | ❓ | ❓ | COMEX |
| Copper | HG | `HGc1` | 🔄 | ❓ | ❓ | COMEX |
| Platinum | PL | `PLc1` | 🔄 | ❓ | ❓ | NYMEX |
| Palladium | PA | `PAc1` | 🔄 | ❓ | ❓ | NYMEX |

### Grains (CBOT)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Corn | ZC | `Cc1` | 🔄 | ❓ | ❓ | CBOT |
| Wheat (SRW) | ZW | `Wc1` | 🔄 | ❓ | ❓ | CBOT |
| Soybeans | ZS | `Sc1` | 🔄 | ❓ | ❓ | CBOT |
| Soybean Oil | ZL | `BOc1` | 🔄 | ❓ | ❓ | CBOT |
| Soybean Meal | ZM | `SMc1` | 🔄 | ❓ | ❓ | CBOT |
| KC HRW Wheat | KE | `KWc1` | 🔄 | ❓ | ❓ | CBOT |

### Softs (ICE US)

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| Coffee "C" | KC | `KCc1` | 🔄 | ❓ | ❓ | ICE US |
| Sugar No. 11 | SB | `SBc1` | 🔄 | ❓ | ❓ | ICE US |
| Cocoa | CC | `CCc1` | 🔄 | ❓ | ❓ | ICE US |
| Cotton No. 2 | CT | `CTc1` | 🔄 | ❓ | ❓ | ICE US |

---

## Equities

### US Stocks (Examples)

| Instrument | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|----------|--------|-------|----------|-------|
| Apple | `AAPL.O` | 🔄 | ❓ | ❓ | NASDAQ |
| Microsoft | `MSFT.O` | 🔄 | ❓ | ❓ | NASDAQ |
| Tesla | `TSLA.O` | 🔄 | ❓ | ❓ | NASDAQ |
| JPMorgan | `JPM.N` | 🔄 | ❓ | ❓ | NYSE |
| Berkshire | `BRKa.N` | 🔄 | ❓ | ❓ | NYSE |

### European Stocks (Examples)

| Instrument | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|----------|--------|-------|----------|-------|
| HSBC | `HSBA.L` | 🔄 | ❓ | ❓ | LSE |
| Shell | `SHEL.L` | 🔄 | ❓ | ❓ | LSE |
| Total | `TTEF.PA` | 🔄 | ❓ | ❓ | Euronext Paris |
| SAP | `SAPG.DE` | 🔄 | ❓ | ❓ | Xetra |
| Nestle | `NESN.S` | 🔄 | ❓ | ❓ | SIX |

---

## Options (RESEARCH NEEDED)

Options data requires systematic validation of RIC patterns across exchanges.

### Equity Index Options

| Instrument | Exchange | LSEG RIC Pattern | Status | Notes |
|------------|----------|------------------|--------|-------|
| SPX Options | CBOE | `SPX{M}{Y}{C/P}{strike}` | ❓ | S&P 500 Index options |
| VIX Options | CBOE | `VIX{M}{Y}{C/P}{strike}` | ❓ | VIX volatility options |
| NDX Options | CBOE | `NDX{M}{Y}{C/P}{strike}` | ❓ | Nasdaq-100 Index options |
| E-mini S&P Options | CME | `ES{M}{Y}{C/P}{strike}` | ❓ | Options on ES futures |
| E-mini Nasdaq Options | CME | `NQ{M}{Y}{C/P}{strike}` | ❓ | Options on NQ futures |
| Euro Stoxx 50 Options | Eurex | `OESX{M}{Y}{C/P}{strike}` | ❓ | Options on FESX futures |

### Bond Futures Options (CME/CBOT)

| Instrument | Symbol | LSEG RIC Pattern | Status | Notes |
|------------|--------|------------------|--------|-------|
| 2Y T-Note Options | OZT | `TU{M}{Y}{C/P}{strike}` | ❓ | Options on ZT futures |
| 5Y T-Note Options | OZF | `FV{M}{Y}{C/P}{strike}` | ❓ | Options on ZF futures |
| 10Y T-Note Options | OZN | `TY{M}{Y}{C/P}{strike}` | ❓ | Options on ZN futures |
| 30Y T-Bond Options | OZB | `US{M}{Y}{C/P}{strike}` | ❓ | Options on ZB futures |
| Ultra 10Y Options | OTN | `TN{M}{Y}{C/P}{strike}` | ❓ | Options on TN futures |
| Ultra 30Y Options | OUB | `UB{M}{Y}{C/P}{strike}` | ❓ | Options on UB futures |

### European Bond Futures Options (Eurex)

| Instrument | Symbol | LSEG RIC Pattern | Status | Notes |
|------------|--------|------------------|--------|-------|
| Bund Options | OGBL | `FGBL{M}{Y}{C/P}{strike}` | ❓ | Options on Bund futures |
| Bobl Options | OGBM | `FGBM{M}{Y}{C/P}{strike}` | ❓ | Options on Bobl futures |
| Schatz Options | OGBS | `FGBS{M}{Y}{C/P}{strike}` | ❓ | Options on Schatz futures |

### STIR Futures Options (Short-Term Interest Rate)

| Instrument | Exchange | LSEG RIC Pattern | Status | Notes |
|------------|----------|------------------|--------|-------|
| SOFR Options | CME | `SR3{M}{Y}{C/P}{strike}` | ❓ | Options on 3M SOFR futures |
| Fed Funds Options | CBOT | `FF{M}{Y}{C/P}{strike}` | ❓ | Options on FF futures |
| Euribor Options | Eurex/ICE | `FEI{M}{Y}{C/P}{strike}` | ❓ | Options on Euribor futures |
| SONIA Options | ICE | `FSS{M}{Y}{C/P}{strike}` | ❓ | Options on SONIA futures |

### FX Options

| Pair | Exchange | LSEG RIC Pattern | Status | Notes |
|------|----------|------------------|--------|-------|
| EUR/USD Options | CME | `URO{M}{Y}{C/P}{strike}` | ❓ | Options on 6E futures |
| GBP/USD Options | CME | `BP{M}{Y}{C/P}{strike}` | ❓ | Options on 6B futures |
| JPY/USD Options | CME | `JY{M}{Y}{C/P}{strike}` | ❓ | Options on 6J futures |
| EUR/USD OTC | OTC | `EUR{tenor}=` | ❓ | OTC FX options |

### Swaptions (Options on Interest Rate Swaps)

| Instrument | Description | LSEG RIC Pattern | Status | Notes |
|------------|-------------|------------------|--------|-------|
| USD Payer Swaption | Right to pay fixed | `USD{expiry}x{tenor}PAY=` | ❓ | e.g., 1Y into 10Y |
| USD Receiver Swaption | Right to receive fixed | `USD{expiry}x{tenor}REC=` | ❓ | e.g., 1Y into 10Y |
| EUR Payer Swaption | Right to pay fixed | `EUR{expiry}x{tenor}PAY=` | ❓ | Euro swaptions |
| EUR Receiver Swaption | Right to receive fixed | `EUR{expiry}x{tenor}REC=` | ❓ | Euro swaptions |
| Swaption Vol (ATM) | Implied volatility | `USD{expiry}x{tenor}SWPTNVOL=` | ❓ | ATM swaption vol |

**Swaption Tenors to Research:**
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

### Commodity Options

| Instrument | Exchange | LSEG RIC Pattern | Status | Notes |
|------------|----------|------------------|--------|-------|
| WTI Crude Options | NYMEX | `CL{M}{Y}{C/P}{strike}` | ❓ | Options on CL futures |
| Brent Options | ICE | `LCO{M}{Y}{C/P}{strike}` | ❓ | Options on Brent futures |
| Gold Options | COMEX | `GC{M}{Y}{C/P}{strike}` | ❓ | Options on GC futures |
| Nat Gas Options | NYMEX | `NG{M}{Y}{C/P}{strike}` | ❓ | Options on NG futures |
| Corn Options | CBOT | `C{M}{Y}{C/P}{strike}` | ❓ | Options on ZC futures |
| Soybean Options | CBOT | `S{M}{Y}{C/P}{strike}` | ❓ | Options on ZS futures |

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

## Credit

### CDS Indices

| Index | Symbol | LSEG RIC | Status | Daily | Notes |
|-------|--------|----------|--------|-------|-------|
| CDX NA IG 5Y | CDXNAIG5Y | `🔄` | 🔄 | ❓ | N.America Investment Grade |
| CDX NA HY 5Y | CDXNAHY5Y | `🔄` | 🔄 | ❓ | N.America High Yield |
| iTraxx Europe 5Y | ITRXEUR5Y | `🔄` | 🔄 | ❓ | European Investment Grade |
| iTraxx Crossover 5Y | ITRXXOV5Y | `🔄` | 🔄 | ❓ | European High Yield |

### Sovereign CDS

| Country | Symbol | LSEG RIC | Status | Daily | Notes |
|---------|--------|----------|--------|-------|-------|
| United States | USCDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |
| Germany | DECDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |
| UK | GBCDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |
| Japan | JPCDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |
| Italy | ITCDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |

### Corporate CDS (Examples)

| Issuer | Symbol | LSEG RIC | Status | Daily | Notes |
|--------|--------|----------|--------|-------|-------|
| JPMorgan | JPMCDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |
| Goldman Sachs | GSCDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |
| Apple | AAPLCDS5Y | `🔄` | 🔄 | ❓ | 5Y CDS spread |

### Credit Spreads

| Spread | Symbol | LSEG RIC | Status | Daily | Notes |
|--------|--------|----------|--------|-------|-------|
| US IG OAS | USIGOAS | `🔄` | 🔄 | ❓ | Investment Grade OAS |
| US HY OAS | USHYOAS | `🔄` | 🔄 | ❓ | High Yield OAS |

### Credit Ratings

| Source | Access Method | Status | Notes |
|--------|---------------|--------|-------|
| S&P | `🔄` | 🔄 | Via rd.get_data() fields |
| Moody's | `🔄` | 🔄 | Via rd.get_data() fields |
| Fitch | `🔄` | 🔄 | Via rd.get_data() fields |

**Note**: Credit RICs pending research - agent investigating patterns.

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
- **Other countries**: `=RR` suffix returns ACCESS DENIED, try `=RRPS`

### JGB Futures
The expected `JBc1` RIC for JGB 10Y futures returns "not found". Needs research for correct LSEG RIC.

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

1. **Swap Spreads**: Find RICs for swap spread time series
2. **Asset Swap Spreads**: Find fields for ASW on bonds
3. **STIR Futures**: SOFR futures (SFRc1), Euribor (FEIc1)
4. **Stock Index Futures**: ES, NQ, FESX, FDAX
5. **EUR/GBP OIS**: Validate OIS patterns for other currencies
6. **Commodity Futures**: CL, GC, NG
7. **FX Forwards**: Complete tenor coverage for major pairs
8. **Equities**: Basic validation of stock RICs
