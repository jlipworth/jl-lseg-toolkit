# Credit Data RIC Reference

This document contains LSEG RIC patterns for credit default swaps (CDS), credit ratings, and credit spreads.

## Credit Default Swaps (CDS)

### Single-Name Corporate CDS

| Instrument | RIC Pattern | Example |
|------------|-------------|---------|
| 5Y USD CDS | `[TICKER]5YUSAX=R` | `MSFT5YUSAX=R` |
| 5Y USD CDS (alt) | `[TICKER]5YUSAX=MG` | `AMZN5YUSAX=MG` |
| 1Y USD CDS | `[TICKER]1YUSAC=R` | `AXP1YUSAC=R` |

**RIC Structure:**
- `[TICKER]` - Company ticker (MSFT, AMZN, JPM, etc.)
- `[TENOR]` - 1Y, 2Y, 3Y, 5Y, 7Y, 10Y
- `US` - Currency (USD)
- `A` - Seniority indicator
- `X` or `C` - Documentation clause (XR=No Restructuring, CR=Restructuring)
- `=R`, `=MG`, `=MP` - Data source suffix

### Datastream Mnemonics

| Format | Example | Description |
|--------|---------|-------------|
| `[ENTITY]$[CODE]` | `AEN0$AC` | Aegon N.V. Senior CDS |
| `[ENTITY]$[CODE]` | `BAC5$AR` | Bank of America CDS |

Available tenors: 6M, 1Y, 2Y, 3Y, 4Y, 5Y, 7Y, 10Y, 20Y, 30Y

### Sovereign CDS

Use Search API with `IsSovereign eq true` filter:

```python
response = rd.discovery.search(
    view=rd.content.search.Views.CDS_QUOTES,
    filter="IsSovereign eq true"
)
```

## CDS Indices

### iTraxx Europe

| Index | RIC Pattern | Example |
|-------|-------------|---------|
| iTraxx Europe | `ITEEU[TENOR]Y[SERIES]=` | `ITEEU5Y35=` |
| iTraxx Europe 7Y S35 | `ITEEU7Y35=` | Series 35, 7Y |

### CDX (via UBS Indices)

| Index | RIC | Description |
|-------|-----|-------------|
| CDX EM 5Y Long | `.UISYME5E` | Emerging Markets |
| CDX IG 5Y Long | `.UISYMI5E` | Investment Grade |
| CDX IG 10Y Long | `.UISYMI1E` | Investment Grade 10Y |
| CDX HY 5Y Long | `.UISYMH5E` | High Yield |

### CDS Index Constituent Fields

| Field | Description |
|-------|-------------|
| `TR.CDSConstWeight` | Index component weight |
| `TR.CDSConstFITIID` | Component identifier |
| `TR.CDSConstOrgName` | Organization name |
| `TR.CDSConstCUSIP` | CUSIP identifier |
| `TR.CDSConstRED6` | RED6 identifier |

## Credit Ratings

### Bond Rating Fields

| Field | Description | Rating Agency |
|-------|-------------|---------------|
| `TR.FiSPRating` | S&P Bond Rating | S&P |
| `TR.FIMoodysRating` | Moody's Bond Rating | Moody's |
| `TR.GR.Rating(BondRatingSrc=MDY)` | Moody's with source | Moody's |
| `TR.GR.Rating(BondRatingSrc=FTC)` | Fitch with source | Fitch |
| `TR.GR.Rating(BondRatingSrc=SPI)` | S&P with source | S&P |

### Issuer Rating Fields

| Field | Description |
|-------|-------------|
| `TR.IssuerRating` | Generic issuer rating |
| `TR.IssuerRating.RatingSourceDescription` | Rating source description |
| `TR.FiIssuerFitchLongRating` | Fitch long-term issuer rating |
| `TR.FiIssuerMoodysLongRating` | Moody's long-term issuer rating |
| `TR.FiIssuerSPLongRating` | S&P long-term issuer rating |

**Issuer Rating Sources Parameter:**
```python
{'IssuerRatingSrc': 'MIS,DIS,FIS,SPI'}  # Moody's, DBRS, Fitch, S&P
```

### Implied Ratings

| Field | Description |
|-------|-------------|
| `TR.CreditRatioImpliedRating` | Credit SmartRatios Implied Rating |
| `TR.CreditComboImpliedRating` | Credit Combined Implied Rating |

## Credit Spreads

### Option-Adjusted Spread (OAS) Fields

| Field | Description |
|-------|-------------|
| `OAS_BID` | Real-time OAS bid (FID 3712) |
| `TR.OPTIONADJUSTEDSPREADBID` | End-of-day OAS snapshot |
| `TR.FiOptionAdjustedSpread` | OAS from REPS Valuation |
| `TR.OASAnalytics` | Adfin-based OAS calculation (recommended) |

### CDS Spread Fields

| Field | Description |
|-------|-------------|
| `PARMIDSPREAD` | CDS par mid spread |

## Example Usage

```python
import lseg.data as rd

rd.open_session()

# Get CDS index constituents
df = rd.get_data("ITEEU7Y35=", fields=[
    "TR.CDSConstWeight",
    "TR.CDSConstFITIID",
    "TR.CDSConstOrgName",
    "TR.CDSConstCUSIP",
    "TR.CDSConstRED6"
])

# Get credit ratings
df = rd.get_data("AAPL.O", fields=[
    "TR.FiSPRating",
    "TR.FIMoodysRating"
])

# Search for CDS instruments
response = rd.discovery.search(
    view="CDS_QUOTES",
    filter="IsSovereign eq true"
)

rd.close_session()
```

## Workspace Applications

| Application | Purpose |
|-------------|---------|
| CDS/SINGLE Quote | Look up CDS RIC nomenclature |
| Advanced Search - Credit Default Swaps | Search for CDS RICs |
| Data Item Browser (DIB) | Find available fields |

## Data Availability Notes

1. **CDS Limitations:**
   - Return Index (RI) datatype not available for CDS
   - ISIN codes not available for CDS instruments
   - Industry/Country classification not available in CDS category

2. **Historical Data:**
   - Rating history may be limited for certain fields
   - Use `SDate` and `EDate` parameters carefully

3. **Coverage:**
   - LSEG provides end-of-day pricing for 4,000+ CDS curves globally
   - Over 1,500 entities in Datastream

4. **S&P Ratings:**
   - May require a direct license with S&P
