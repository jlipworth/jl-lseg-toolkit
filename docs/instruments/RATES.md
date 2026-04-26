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

### EUR ESTR OIS (Validated 2026-04-25)

**Pattern**: `EUREST{tenor}=` — `EUR{tenor}OIS=` does **not** work for EUR.

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1W | `EUREST1W=` | ❌ | — | DataRetrievalError on 30-day probe |
| 1M | `EUREST1M=` | ✅ | ✅ | 22 rows over 30 days |
| 2M | `EUREST2M=` | ✅ | ✅ | 22 rows over 30 days |
| 3M | `EUREST3M=` | ✅ | ✅ | 22 rows over 30 days |
| 6M | `EUREST6M=` | ✅ | ✅ | 22 rows over 30 days |
| 9M | `EUREST9M=` | ✅ | ✅ | 22 rows over 30 days |
| 12M | `EUREST12M=` | ❌ | — | DataRetrievalError; use IRS 1Y instead |
| 18M | `EUREST18M=` | ✅ | ✅ | 22 rows over 30 days |
| 2Y | `EUREST2Y=` | ✅ | ✅ | 22 rows over 30 days |

`EUR_OIS_TENORS` is wired to the 7 working tenors (`1M, 2M, 3M, 6M, 9M, 18M, 2Y`).
The scheduler's `ois_eur_daily` job is enabled by default.

**1Y proxy:** linearly interpolate between `EUREST9M=` and `EUREST18M=` — both are
ESTR-OIS so the curve is consistent. **Do not** substitute `EURIRS1Y=`: that's a
EURIBOR-based IRS and carries OIS/EURIBOR basis. For tenors longer than 2Y where
ESTR-OIS isn't available, the [EUR IRS section](#eur-irs-validated-2026-01-06) is
acceptable as a different curve (with the basis caveat).

Re-run `uv run python dev_scripts/validate_eurest_ois.py` after any change to the
tenor list or to revalidate against a fresh LSEG session.

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
