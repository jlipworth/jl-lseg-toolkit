# Treasury Data Sources for Bond Basis Analysis

This document describes external data sources for Treasury bond basis analysis.

## Treasury Direct / Fiscal Data API

### Endpoints

| API | URL | Use Case |
|-----|-----|----------|
| Fiscal Data | `api.fiscaldata.treasury.gov` | Historical auction data (recommended) |
| Treasury Direct | `treasurydirect.gov/TA_WS/` | Individual security lookup |

### Fiscal Data API - Auctions Query

**Base URL:** `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query`

**Key Fields:**
| Field | Description | Example |
|-------|-------------|---------|
| `cusip` | 9-character CUSIP | `91282CPJ4` |
| `int_rate` | Coupon rate (%) | `4.000000` |
| `issue_date` | Issue date | `2025-11-17` |
| `maturity_date` | Maturity date | `2035-11-15` |
| `auction_date` | Auction date | `2025-11-12` |
| `security_type` | Note, Bond, Bill | `Note` |
| `security_term` | Original term | `10-Year` |
| `original_security_term` | Original term (alternate) | `10-Year` |

**Example Query - All Notes:**
```python
import requests

url = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query'
params = {
    'filter': 'security_type:eq:Note',
    'fields': 'cusip,security_term,int_rate,issue_date,maturity_date,auction_date',
    'sort': '-auction_date',
    'page[size]': 1000,
    'page[number]': 1
}

resp = requests.get(url, params=params, timeout=30)
data = resp.json()['data']
```

**Data Availability:**
- Notes: 2,276 records (1979-present)
- 10-Year Notes: 488 records
- 5-Year Notes: 449 records
- 2-Year Notes: 683 records

### Treasury Direct API - Security Lookup

**Endpoint:** `https://www.treasurydirect.gov/TA_WS/securities/{CUSIP}/{ISSUE_DATE}`

**Example:**
```python
url = 'https://www.treasurydirect.gov/TA_WS/securities/91282CPJ4/2025-11-17'
resp = requests.get(url, params={'format': 'json'})
```

## CME Conversion Factors

CME publishes conversion factors for Treasury futures in Excel format.

**File Location:** `imports/treasury-futures-conversion-factor-look-up-tables.xls`

**Sheets:**
- `2-Year Note Table` (TU/ZT)
- `3-Year Note Table`
- `5-Year Note Table` (FV/ZF)
- `10-Year Note Table` (TY/ZN)
- `Classic Bond & Ultra Bond Table` (US/ZB/UB)

**Table Structure:**
- Rows: Coupon rates (0% to 20% in 0.125% increments)
- Columns: Years-Months to maturity (e.g., "6—6" = 6 years 6 months)
- Values: Conversion factors (4 decimal places)

**Usage:**
```python
from lseg_toolkit.timeseries.bond_basis import load_cme_cf_table, lookup_cf_from_table
from datetime import date

cf_table = load_cme_cf_table()
cf = lookup_cf_from_table(
    coupon=4.125,
    maturity_date=date(2032, 11, 15),
    first_delivery_date=date(2026, 3, 1),
    cf_table=cf_table
)
# Returns: 0.9003
```

## CME Delivery Date Specification

**Key Rule:** Eligibility for deliverable bonds is calculated from the **first day of the delivery month**.

### Quarterly Contract Months

| Code | Month | First Delivery Date |
|------|-------|---------------------|
| H | March | March 1 |
| M | June | June 1 |
| U | September | September 1 |
| Z | December | December 1 |

### Delivery Period

Per CME specifications:
- **First Delivery Date:** First business day of the contract month
- **Last Delivery Date:** Last business day of the contract month
- **First Notice Day:** Last business day of the month preceding the contract month
- **Last Trading Day:** Seventh business day preceding the last business day of the contract month

For bond eligibility calculations, use the **first day of the delivery month** (not the first business day).

### Iterating Through Contracts

```python
from lseg_toolkit.timeseries.bond_basis import (
    generate_contract_list,
    get_first_delivery_date,
    get_deliverable_basket,
)

# Generate all quarterly contracts from 2020 to 2025
contracts = generate_contract_list(2020, 2025)
# Returns: [('H', 2020, date(2020, 3, 1)), ('M', 2020, date(2020, 6, 1)), ...]

# Get basket for each contract
for month_code, year, first_delivery in contracts:
    basket = get_deliverable_basket("TY", first_delivery)
    print(f"TY{month_code}{year % 10}: {len(basket)} deliverable notes")

# Or use get_first_delivery_date directly
first_delivery = get_first_delivery_date("H", 2026)  # March 1, 2026
basket = get_deliverable_basket("TY", first_delivery)
```

## Reconstructing Historical Deliverable Baskets

LSEG does not provide historical deliverable baskets. Reconstruct using:

### Eligibility Rules by Contract

| Contract | Original Maturity | Remaining Maturity at Delivery |
|----------|-------------------|-------------------------------|
| 2-Year (TU/ZT) | ≤ 2y 3m | 1y 9m - 2y |
| 3-Year | ≤ 3y 3m | 2y 9m - 3y |
| 5-Year (FV/ZF) | ≤ 5y 3m | 4y 2m - 5y 3m |
| 10-Year (TY/ZN) | ≤ 10y | 6y 6m - 10y |
| Ultra 10-Year (TN) | = 10y (original issue) | 9y 5m - 10y |
| T-Bond (US/ZB) | ≥ 15y | 15y - 25y |
| Ultra T-Bond (UB) | ≥ 25y | ≥ 25y |

### Reconstruction Algorithm

```python
def get_deliverable_basket(
    futures_root: str,
    first_delivery_date: date,
    all_notes: list[dict]
) -> list[dict]:
    """
    Reconstruct deliverable basket for a futures contract.

    Args:
        futures_root: 'TY', 'FV', 'TU', etc.
        first_delivery_date: First delivery date of contract
        all_notes: All Treasury notes from Fiscal Data API

    Returns:
        List of eligible notes with CUSIP, coupon, maturity
    """
    # Eligibility rules for 10-Year (TY/ZN)
    if futures_root in ('TY', 'ZN'):
        min_remaining = 6.5 * 365  # 6 years 6 months
        max_remaining = 10 * 365   # 10 years
        max_original = 10 * 365    # 10 years original maturity
    # ... other contracts

    eligible = []
    for note in all_notes:
        issue = parse_date(note['issue_date'])
        maturity = parse_date(note['maturity_date'])

        # Check original maturity
        original_term = (maturity - issue).days
        if original_term > max_original:
            continue

        # Check remaining maturity at delivery
        remaining = (maturity - first_delivery_date).days
        if min_remaining <= remaining <= max_remaining:
            eligible.append(note)

    return eligible
```

## LSEG Data (Current Only)

| Data | RIC | Historical |
|------|-----|------------|
| Deliverable basket | `0#TYc1=DLV` | No |
| CTD ranking | `0#TYc1=CTD` | No |
| Bond prices | `{CUSIP}=` | Yes |
| Repo rates | `USONRP=`, `US1MRP=` | Yes (5+ years) |
| Futures prices | `TYc1`, `TYH6` | Yes (5+ years) |

## Sources

- [Treasury Fiscal Data API](https://fiscaldata.treasury.gov/api-documentation/)
- [Treasury Direct Web APIs](https://www.treasurydirect.gov/webapis/webapisecurities.htm)
- [CME Conversion Factor Tables](https://www.cmegroup.com/trading/interest-rates/us-treasury-futures-conversion-factor-lookup-tables.html)
- [CME Treasury Basics](https://www.cmegroup.com/trading/interest-rates/basics-of-us-treasury-futures.html)
