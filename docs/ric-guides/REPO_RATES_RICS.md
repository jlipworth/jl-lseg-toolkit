# Repo Rates and Overnight Rates RIC Reference

This document contains LSEG RIC patterns for repo rates, overnight financing rates, and related money market instruments.

## US Repo Rates and SOFR

| Instrument | LSEG RIC | Description |
|------------|----------|-------------|
| **SOFR** | `USDSOFR=` | Secured Overnight Financing Rate (NY Fed) |
| SOFR 30-Day Avg | `SOFR1MAVG=` | 30-day compounded average SOFR |

### Treasury Bond Repo Rates (Confirmed Working)

| Instrument | LSEG RIC | Description |
|------------|----------|-------------|
| O/N Treasury Repo | `USONRP=` | Overnight Treasury Bond Repo |
| 1W Treasury Repo | `US1WRP=` | 1 Week Treasury Bond Repo |
| 2W Treasury Repo | `US2WRP=` | 2 Week Treasury Bond Repo |
| 3W Treasury Repo | `US3WRP=` | 3 Week Treasury Bond Repo |
| 1M Treasury Repo | `US1MRP=` | 1 Month Treasury Bond Repo |
| 2M Treasury Repo | `US2MRP=` | 2 Month Treasury Bond Repo |
| 3M Treasury Repo | `US3MRP=` | 3 Month Treasury Bond Repo |
| 6M Treasury Repo | `US6MRP=` | 6 Month Treasury Bond Repo |

### Other Rates (May Require Permissions)

| Instrument | LSEG RIC | Description |
|------------|----------|-------------|
| Fed Funds Effective | `USONFFE=` | Fed Funds Composite (not available in testing) |
| Tri-Party GC Rate | `TGCR=` | Treasury repo tri-party rate (not available) |
| Broad GC Rate | `BGCR=` | Treasury repo broad rate (not available) |

### SOFR Futures

| Instrument | RIC Pattern | Example |
|------------|-------------|---------|
| 1-Month SOFR Futures | `SR1[M][Y]` | SR1F24 (Feb 2024) |
| 3-Month SOFR Futures | `SR3[M][Y]` | SR3H5 (Mar 2025) |
| SOFR Futures Chain | `0#SR1:` | All 1-month contracts |
| SOFR Futures Chain | `0#SR3:` | All 3-month contracts |

### USD IBOR Cash Fallbacks (SOFR-based)

| Tenor | LSEG RIC |
|-------|----------|
| 1-Month | `USDCFIFCADA1M=` |
| 3-Month | `USDCFIFCADB3M=` |
| 6-Month | `USDCFIFCADB6M=` |
| 12-Month | `USDCFIFCADB1Y=` |

## European Rates (ESTR)

| Instrument | LSEG RIC | Description |
|------------|----------|-------------|
| **Euro Short-Term Rate** | `EUROSTR=` | ECB published overnight rate |
| EONIA (legacy) | `EONIA=` | Replaced by ESTR |

## UK Rates (SONIA)

| Instrument | LSEG RIC | Description |
|------------|----------|-------------|
| **SONIA** | `SONIAOSR=` | Bank of England administered rate |

## Other Overnight Rates

| Instrument | LSEG RIC | Description |
|------------|----------|-------------|
| Swiss SARON | `/SARON.S` | Uses TRDPRC_1 field |
| Canadian CORRA | `CORRA=` | Canadian Overnight Repo Rate Average |
| Bank of Canada | `CABOCR=ECI` | Requires ECI permissions |

## OIS (Overnight Index Swaps)

| Instrument | LSEG RIC | Description |
|------------|----------|-------------|
| USD OIS Chain | `USDOIS=` or `1#USDOIS=` | Query OIS rates |
| USD 1M OIS | `USD1MOIS` | 1-month tenor |
| USD 3M OIS | `USD3MOIS` | 3-month tenor |
| USD 5Y OIS | `USD5YOIS=TREU` | Longer tenors may have different field structure |

## Forward Rate Agreements (FRAs)

FRA RICs are contributed rates from market makers:

| Currency | Pattern | Example |
|----------|---------|---------|
| USD FRA | `USD[start]X[end]FRA=` | `USD3X6FRA=` |
| EUR FRA | `EUR[start]X[end]FRA=` | `EUR3X6FRA=` |
| GBP FRA | `GBP[start]X[end]FRA=` | `GBP3X6FRA=` |

Common FRA tenors: 1x4, 3x6, 6x9, 6x12, 9x12

## STIR Futures (Exchange-traded alternatives to OTC FRAs)

### EURIBOR Futures

| Instrument | RIC Pattern | Example |
|------------|-------------|---------|
| 3-Month EURIBOR | `FEI[M][Y]` | FEIH5 (Mar 2025) |
| Chain | `0#FEI:` | All contracts |

### SONIA Futures

| Instrument | RIC Pattern |
|------------|-------------|
| 3-Month SONIA | `SON[M][Y]` |

## Key Fields

| Field | Description | Used For |
|-------|-------------|----------|
| `PRIMACT_1` | Primary activity/value | SONIAOSR=, EUROSTR= |
| `VALUE_DT1` | Fixing date | Date of rate fixing |
| `VALUE_TS1` | Fixing timestamp | Time of rate fixing |
| `TRDPRC_1` | Trade price | /SARON.S |
| `BID` / `ASK` | Bid/Ask prices | Contributed rates |

## Speed Guides

Use these in Eikon/Workspace to explore available instruments:

| Speed Guide | Purpose |
|-------------|---------|
| `FWD/1` | Forward-related instruments |
| `MONEY/1` | Money market instruments |
| `RATES/1` | Interest rate benchmarks |
| `0#[CCY]MM=` | Money market chain by currency |

## Data Availability Notes

1. **Permissions**: Many benchmark rates require specific data permissions
2. **Field Differences**: Longer-tenor OIS may have different field structures
3. **Chain RICs**: Use `0#` prefix for all contracts in a series
4. **FRA Data**: Contributed by banks, may require specific entitlements

## Example Usage

```python
import lseg.data as rd

rd.open_session()

# Get SOFR
sofr = rd.get_data("USDSOFR=", fields=["TRDPRC_1", "VALUE_DT1"])

# Get OIS rates
ois = rd.get_data(
    ["USD1MOIS", "USD3MOIS", "USD1YOIS"],
    fields=["BID", "ASK", "MID"]
)

# Get historical SOFR
sofr_hist = rd.get_history(
    "USDSOFR=",
    start="2024-01-01",
    end="2024-12-31",
    interval="daily"
)

rd.close_session()
```
