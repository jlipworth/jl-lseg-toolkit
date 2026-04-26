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
| EUR OIS | `EUR1YOIS=` ❌ | `EUREST{tenor}=` ✅ | Validated 2026-04-25: 1M, 2M, 3M, 6M, 9M, **1Y**, 18M, 2Y work. Use `1Y` not `12M` (bare RIC). 1W unavailable. |
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
