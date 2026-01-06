# Bond Basis and Deliverable Basket RIC Reference

This document contains LSEG RIC patterns and fields for Treasury futures bond basis analysis.

## Quick Reference

| Data | RIC Pattern | Example |
|------|-------------|---------|
| Deliverable basket | `0#[FUT]c1=DLV` | `0#TYc1=DLV` |
| CTD ranking | `0#[FUT]c1=CTD` | `0#TYc1=CTD` |
| Direct CTD bond | `[FUT]c1=CTD` | `TYc1=CTD` |
| CTD ranked 2-10 | `[FUT]c1=CTD[N]` | `TYc1=CTD2`, `TYc1=CTD3` |
| Invoice chain | `0#[FUT]=INV` | `0#TY=INV` (requires permissions) |

## Treasury Futures RIC Roots

| Contract | CME Symbol | LSEG Root | Continuous | Deliverable Chain |
|----------|------------|-----------|------------|-------------------|
| 2-Year T-Note | ZT | TU | TUc1 | 0#TUc1=DLV |
| 5-Year T-Note | ZF | FV | FVc1 | 0#FVc1=DLV |
| 10-Year T-Note | ZN | TY | TYc1 | 0#TYc1=DLV |
| Ultra 10-Year | TN | TN | TNc1 | 0#TNc1=DLV |
| T-Bond | ZB | US | USc1 | 0#USc1=DLV |
| Ultra T-Bond | UB | UB | UBc1 | 0#UBc1=DLV |

## Available Fields on CTD RICs

Fields confirmed working on `TYc1=CTD`:

| Field | Description | Example Value |
|-------|-------------|---------------|
| `DSPLY_NAME` | Bond description | "UST 3 3/4 N/32" |
| `NET_BASIS` | Net basis (32nds) | -0.002 |
| `CARRY_COST` | Carry cost | -0.042 |
| `REPO_RATE` | Implied repo rate | 3.696 |
| `DURATION` | Macaulay duration | 6.115 |
| `MOD_DURTN` | Modified duration | 5.997 |
| `BPV` | Basis point value | 5.957 |

## Available Fields on Deliverable Bonds

Fields confirmed working on bond RICs (e.g., `91282CFV8=`):

| Field | Description | Example Value |
|-------|-------------|---------------|
| `DSPLY_NAME` | Bond description | "UST 4 1/8 N/32" |
| `BID` | Bid price | 101.2422 |
| `ASK` | Ask price | 101.2734 |
| `MID_YLD_1` | Mid yield | 3.9134 |
| `ACCR_INT` | Accrued interest | 0.5925 |
| `MOD_DURTN` | Modified duration | 5.8984 |
| `DURATION` | Macaulay duration | 6.0138 |
| `BPV` | Basis point value | 6.0075 |

## Chain Navigation Fields

Found in `GN_TXT16_2` on CTD RICs:

| Field | Value | Description |
|-------|-------|-------------|
| `GN_TXT16_2` | `0#TY=INV` | Invoice price chain |
| `LONGLINK1` | `0#TYc1=CTD` | Link to CTD chain |
| `LONGLINK2` | `0#TYc1=DLV` | Link to deliverable chain |

## Discrete Contract RICs

| Format | Example | Description |
|--------|---------|-------------|
| `[ROOT][MONTH][2-DIGIT-YEAR]` | `TYH26` | Mar 2026 10Y T-Note |
| `[ROOT][MONTH][YEAR]^[DECADE]` | `TYH1^2` | Mar 2021 (expired) - may not work |

**Important:** Use 2-digit year format (e.g., `TYH26` not `TYH6`)

Month codes: F(Jan), G(Feb), H(Mar), J(Apr), K(May), M(Jun), N(Jul), Q(Aug), U(Sep), V(Oct), X(Nov), Z(Dec)

Treasury futures typically use: H(Mar), M(Jun), U(Sep), Z(Dec)

### Contract Chain

Use `0#TY:` to list all active contracts:

```python
df = rd.get_data("0#TY:", fields=["DSPLY_NAME", "SETTLE", "EXPIR_DATE"])
# Returns: /TYH26, /TYM26, /TYU26, etc.
```

### Historical Data

Historical data for continuous contracts is available via `get_history`:

```python
df = rd.get_history(
    "TYc1",
    fields=["SETTLE", "OPINT_1"],
    start="2024-01-01",
    end="2024-12-31",
    interval="daily"
)
```

**Note:** Expired discrete contracts (e.g., `TYH24`) may not be accessible via `get_data`.
The continuous RIC (`TYc1`) provides historical data that spans contract rolls.

## Conversion Factors

**Note:** Conversion factors are NOT directly available via the standard LSEG Data Library API (rd.get_data).

### What We Tested

| Approach | Result |
|----------|--------|
| `CF` field on bond RIC | Not available |
| `CNVRSN_FCTR` field | Not available |
| `CONV_FACTOR` field | Not available |
| IPA bond.Definition with `ConversionFactor` | Returns None |
| Invoice chain `0#TY=INV` | Access Denied (requires permissions) |
| Contributor-specific RICs (TBEA, BGCP) | Access Denied |

### Where CF Might Be Visible

If you see CF in LSEG Workspace, it may be from:
1. **Bond Futures Page UI** - calculated/displayed in the interface
2. **Invoice Price Chain** - `0#TY=INV` (requires specific permissions)
3. **Premium Data Feed** - contributor-specific RICs

### How to Obtain Conversion Factors

1. **CME Group Website**: [Conversion Factor Lookup Tables](https://www.cmegroup.com/trading/interest-rates/us-treasury-futures-conversion-factor-lookup-tables.html)
2. **CME FTP**: Daily conversion factor files
3. **Calculate manually**: Using CME formula (6% yield to maturity assumption)

### CME Conversion Factor Formula

The CF is the price at which $1 par would trade if it yielded exactly 6%:

```
CF = (c/2) * [1 - (1+y/2)^(-n)] / (y/2) + (1+y/2)^(-n) - accrued_adjustment

Where:
  c = coupon rate (decimal, e.g., 0.04125 for 4.125%)
  y = 0.03 (6% annual / 2 for semiannual)
  n = number of semiannual periods (z / 6)
  z = months to maturity, rounded DOWN to nearest quarter (3 months)
  accrued_adjustment = (c/2) * (6-v)/6 where v = z % 6
```

**Key insight**: CME rounds maturity DOWN to the nearest quarter (not round to nearest).

Example: 4.125% Nov 2032 bond, Mar 2026 first delivery
- Months to maturity: ~80.5 months
- Rounded DOWN: 78 months (6 years 6 months)
- CF = **0.9003** (matches CME lookup table)

## Bond Basis Calculation

### LSEG's Methodology (Verified)

LSEG uses specific price conventions:

```
Invoice = Futures BID × Conversion Factor
Gross Basis = Bond ASK - Invoice
Net Basis = Gross Basis + Carry Cost
```

**Sign Convention:**
- CARRY_COST is **negative** when you earn (coupon > financing)
- CARRY_COST is **positive** when you pay (financing > coupon)
- Net Basis = Gross + Carry (not Gross - Carry)

**Prices Used:**
- **Bond**: ASK price (worst execution for buyer)
- **Futures**: BID price (worst execution for seller)
- **CF**: Conversion Factor from CME

### Standard Formulas (for reference)

```
Gross Basis = Cash Price - (Futures Price × CF)
Carry = Coupon Income - Financing Cost
Net Basis = Gross Basis - Carry
```

**Carry Calculation:**
```
Financing Cost = Dirty Price × Repo Rate × Days/360
Coupon Income = (Coupon/2) × Days/182.5
Carry = Coupon Income - Financing Cost
```

### Key RICs for Carry

| Instrument | RIC | Description |
|------------|-----|-------------|
| O/N Treasury Repo | `USONRP=` | Overnight financing rate |
| 1W Treasury Repo | `US1WRP=` | 1-week term repo |
| 1M Treasury Repo | `US1MRP=` | 1-month term repo |
| 2M Treasury Repo | `US2MRP=` | 2-month term repo |
| 3M Treasury Repo | `US3MRP=` | 3-month term repo |
| SOFR | `USDSOFR=` | Secured Overnight Financing Rate |

### Implied Repo vs Actual Repo

- **REPO_RATE** on CTD RICs = Implied Repo Rate (IRR)
  - The rate at which basis trade breaks even
  - Derived from current prices, not a market rate
- **Actual Repo** = Market financing rate (from RICs above)
  - The rate you actually pay to finance the position
  - Net Basis opportunity exists when IRR ≠ Actual Repo

## Example: Fetching Bond Basis Data

```python
import lseg.data as rd

rd.open_session()

# 1. Get deliverable basket
basket = rd.get_data("0#TYc1=DLV", fields=["DSPLY_NAME"])
bond_rics = basket["Instrument"].tolist()

# 2. Get CTD with basis analytics
ctd_fields = ["DSPLY_NAME", "NET_BASIS", "CARRY_COST", "REPO_RATE", "BPV"]
ctd = rd.get_data("0#TYc1=CTD", fields=ctd_fields)

# 3. Get bond prices
bond_fields = ["DSPLY_NAME", "BID", "ASK", "MID_YLD_1", "ACCR_INT", "MOD_DURTN"]
bonds = rd.get_data(bond_rics, fields=bond_fields)

# 4. Get futures settle
futures = rd.get_data("TYc1", fields=["SETTLE", "EXPIR_DATE"])

rd.close_session()
```

## Historical Contracts

To access historical/expired contracts, use the decade suffix:

```python
# Current front month
rd.get_data("TYc1", fields=["SETTLE"])

# Specific contract (Mar 2026)
rd.get_data("TYH6", fields=["SETTLE"])

# Expired contract (Mar 2021)
rd.get_history("TYH1^2", start="2021-01-01", end="2021-03-19")
```

## Related RIC Patterns

### Repo Rates (for Carry Calculation)
| Instrument | RIC | Description |
|------------|-----|-------------|
| SOFR | `USDSOFR=` | Secured Overnight Financing Rate |
| Fed Funds | `USONFFE=` | Fed Funds Effective |
| SOFR 30-Day Avg | `SOFR1MAVG=` | 30-day compounded SOFR |

### Treasury Benchmarks
| Tenor | RIC | Description |
|-------|-----|-------------|
| 2Y | `US2YT=RRPS` | 2-Year benchmark |
| 5Y | `US5YT=RRPS` | 5-Year benchmark |
| 10Y | `US10YT=RRPS` | 10-Year benchmark |
| 30Y | `US30YT=RRPS` | 30-Year benchmark |

## European Bond Futures (Confirmed Working)

| Contract | RIC | Deliverable Chain |
|----------|-----|-------------------|
| Euro-Bund | FGBLc1 | 0#FGBLc1=DLV |
| Euro-Bobl | FGBMc1 | 0#FGBMc1=DLV |
| Euro-Schatz | FGBSc1 | 0#FGBSc1=DLV |

## Data Availability Notes

1. **CTD Analytics**: NET_BASIS, CARRY_COST, REPO_RATE available on CTD RICs
2. **Invoice Chain**: Requires additional permissions (Access Denied on standard access)
3. **Conversion Factors**: Not available via standard fields - use CME source
4. **Historical CTD**: May require specific expired contract RICs

## API vs Workspace Data

**Important**: The LSEG Data Library API may return cached/delayed values compared to LSEG Workspace. During testing, we observed:
- API CARRY_COST: -0.101
- Workspace CARRY_COST: -0.06 (live)

For time-sensitive calculations, verify API values against Workspace or use streaming data.

## Sources

- LSEG Developer Community
- CME Group Treasury Futures Documentation
- LSEG Workspace Field Browser (DIB app)
