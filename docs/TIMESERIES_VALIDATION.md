# LSEG Timeseries Data Validation Results

Validation run: 2026-01-06

## Summary

- **Total RICs tested:** 43
- **Working:** 25/43 (58%)
- **Failed:** 18/43 (42%)

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

### OIS ✓ (1/9)

| RIC | Description | Daily | Notes |
|-----|-------------|-------|-------|
| `USD1MOIS=` | USD SOFR 1M OIS | ✓ | Only working OIS pattern |

**Not Working:**
- `USDSOFR1M=`, `USDSOFR1Y=`, etc. - Wrong pattern
- `EUR1MOIS=` - No data
- `GBP1MOIS=ICAP` - Access denied

### Government Bond Yields ✓ (4/9)

| RIC | Description | Daily | Notes |
|-----|-------------|-------|-------|
| `DE10YT=RR` | German 10Y | ✓ | |
| `DE5YT=RR` | German 5Y | ✓ | |
| `DE2YT=RR` | German 2Y | ✓ | |
| `GB10YT=RR` | UK 10Y Gilt | ✓ | |

**Not Working (Permission Required):**
- `US10YT=RR`, `US5YT=RR`, `US2YT=RR`, `US30YT=RR` - US Treasury yields
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

### 6. US Treasury Yields Require Permissions
`US10YT=RR` and related RICs return "UserNotPermission" errors.

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
4. **OIS limited** - Only USD1MOIS= pattern works
5. **Use alternative for US yields** - Consider spot RICs or other patterns
