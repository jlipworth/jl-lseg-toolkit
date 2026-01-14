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
