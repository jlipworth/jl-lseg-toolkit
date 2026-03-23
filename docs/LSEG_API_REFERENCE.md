# LSEG API Reference

Detailed API patterns, field reference, and index information for the LSEG toolkit.

## RIC Format (Reuters Instrument Codes)

LSEG uses **RIC codes** to identify securities. Understanding the format helps when working with tickers:

| Suffix | Exchange | Examples |
|--------|----------|----------|
| `.O` | NASDAQ | `AAPL.O`, `MSFT.O`, `GOOGL.O` |
| `.N` | NYSE | `JPM.N`, `WMT.N`, `IBM.N` |
| `.L` | London | `SHEL.L`, `HSBA.L`, `BP.L` |
| `.DE` | Frankfurt | `SAP.DE`, `SIE.DE`, `BMW.DE` |
| `.PA` | Paris | `OR.PA`, `AIR.PA`, `BNP.PA` |
| `.T` | Tokyo | `7203.T` (Toyota), `6758.T` (Sony) |
| `.HK` | Hong Kong | `0005.HK`, `0700.HK` |
| `.TO` | Toronto | `RY.TO`, `TD.TO`, `ENB.TO` |

**Important:**
- `get_index_constituents()` returns RICs with suffixes already included (e.g., `['AAPL.O', 'MSFT.O', ...]`)
- All other `LsegClient` methods expect RICs with suffixes
- You never need to manually add suffixes when using this toolkit's API

## API Call Best Practices

**Rule #1: ALWAYS Batch API Calls - NEVER Loop Over Individual Tickers**

```python
# BAD - One API call per ticker (25x slower!)
for ticker in tickers:
    df = rd.get_data(universe=[ticker], fields=fields)

# GOOD - Single batch API call
df = rd.get_data(universe=tickers, fields=fields)
```

**Performance Impact:**
- 137 individual calls: **50.63 seconds**
- Batched calls: **14.73 seconds** (71% faster, 3.4x speedup)

**Anti-Patterns:**
```python
# NEVER DO THIS
for ticker in tickers:
    data = rd.get_data(universe=[ticker], ...)

for _, row in df.iterrows():
    data = rd.get_data(universe=[row["Instrument"]], ...)

results = [rd.get_data(universe=[t], ...) for t in tickers]
```

**Acceptable Patterns:**
```python
# BEST - One call for all tickers
df = rd.get_data(universe=tickers, fields=fields)

# GOOD - Batch by group when different parameters needed
from collections import defaultdict
tickers_by_date = defaultdict(list)
for ticker, date in ticker_date_pairs:
    tickers_by_date[date].append(ticker)

for date, ticker_list in tickers_by_date.items():
    df = rd.get_data(universe=ticker_list, fields=fields, parameters={"SDate": date})
```

## Common API Patterns

**Index Constituents:**
```python
rics_df = rd.get_data(universe='.SPX', fields=['TR.IndexConstituentRIC'])
rics = rics_df['Constituent RIC'].dropna().unique().tolist()

caps_df = rd.get_data(universe=rics, fields=['TR.CompanyMarketCap'])
filtered = caps_df[caps_df['Company Market Cap'] >= 100_000_000_000]
```

**Earnings Events:**
```python
# All earnings times are GMT/UTC
df = rd.get_data(
    universe=['AAPL.O', 'MSFT.O'],
    fields=['TR.EventStartDate', 'TR.EventStartTime', 'TR.EventType'],
    parameters={'SDate': '2025-10-27', 'EDate': '2025-11-03'}
)
df = df[df['Company Event Type'] == 'EarningsReleases']
```

**Equity Screener:**
```python
# Don't wrap in SCREEN() - API does this automatically
screener_expr = (
    f"U(IN(Equity(active,public,primary))), "
    f"IN(TR.HQCountryCode,'US'), "
    f"BETWEEN(TR.CompanyMarketCap,2000000000,20000000000)"
)
screener_obj = rd.discovery.Screener(expression=screener_expr)
rics = screener_obj.get_data()['Instrument'].tolist()
```

## Available Indices (13 Verified)

| Code | Name | Region | Companies |
|------|------|--------|-----------|
| SPX | S&P 500 | US | 500 |
| SPCY | S&P SmallCap 600 | US | 600 |
| NDX | Nasdaq 100 | US | 100 |
| DJI | Dow Jones | US | 30 |
| STOXX | STOXX Europe 600 | Europe | 600 |
| STOXX50E | EURO STOXX 50 | Europe | 50 |
| FTSE | FTSE 100 | UK | 100 |
| GDAXI | DAX | Germany | 40 |
| FCHI | CAC 40 | France | 40 |
| AEX | AEX | Netherlands | 25 |
| N225 | Nikkei 225 | Japan | 225 |
| HSI | Hang Seng | Hong Kong | ~88 |
| GSPTSE | S&P/TSX Composite | Canada | ~214 |

**Note**: Russell indices (1000, 2000, 3000) not available via LSEG API.

## Key LSEG Fields (47 Validated)

**Company Data:**
- `TR.CommonName`, `TR.TRBCEconomicSector`, `TR.PriceClose`, `TR.CompanyMarketCap`
- `TR.IndexConstituentRIC` - Index constituents

**Earnings:**
- `TR.EventStartDate`, `TR.EventStartTime`, `TR.EventStartDateTime` (GMT/UTC)
- `TR.EventType`, `TR.EventTitle`

**Valuation (LTM):**
- `TR.PE`, `TR.EVToEBITDA`, `TR.PriceToBVPerShare`

**Consensus Estimates** (supports NTM, FY1, FY2, FQ1, FQ2):
- `TR.RevenueMean(Period=NTM)`, `TR.EBITDAMean(Period=NTM)`, `TR.EPSMean(Period=NTM)`
- `TR.RevenueMean(Period=FQ1).periodenddate` - Period end date for fiscal labels

**Financials** (snapshot-compatible):
- `TR.TotalDebt`, `TR.CashAndSTInvestments`, `TR.FreeCashFlow`
- `TR.CashFromOperatingActivities`, `TR.CapitalExpenditures`
- **Calculated**: Net Debt = Total Debt - Cash; EV = Market Cap + Net Debt; FCF = OCF - CapEx

**Performance:**
- `TR.TotalReturn1Mo`, `TR.TotalReturn3Mo`, `TR.TotalReturn6Mo` - Short-term returns
- `TR.TotalReturnYTD`, `TR.TotalReturn1Yr`, `TR.TotalReturn3Yr`, `TR.TotalReturn5Yr`
- `TR.TotalReturn` (with SDate/EDate for 2Y returns)
- `TR.IPODate`, `TR.DividendYield`

**Analyst:**
- `TR.IVPriceToIntrinsicValue`, `TR.PriceTargetMean/Median/High/Low`

**Important Notes:**
- All earnings times in GMT/UTC (use timezone conversion)
- Must use hardcoded field strings, not f-strings (LSEG uppercases and breaks parentheses)
- Some fields don't support historical snapshots (calculate from components instead)

## API Behavior Notes

**Field Naming Quirks:**
- `COUPN_RATE` works, `CPN_RATE` returns NA (use the longer form)
- `MATUR_DATE` works for maturity dates
- `ACCR_INT` for accrued interest
- `TRDPRC_1` for last trade price, `PRIMACT_1` for primary activity (rates)

**API vs Workspace Data:**
- The API may return cached/delayed values compared to LSEG Workspace
- For time-sensitive data, verify against Workspace or use streaming
- Observed lag: API showed stale CARRY_COST while Workspace showed current values

**Chain RICs:**
- Use `0#` prefix for chains: `0#TYc1=DLV`, `0#TYc1=CTD`
- Chains return DataFrame with `Instrument` column containing constituent RICs
- CTD chain ranked by implied repo (best delivery first)

**Discovery Search:**
- `rd.discovery.search(query="...")` finds RICs by keyword
- Useful for discovering RIC patterns: e.g., searching "Treasury repo" found `USONRP=`, `US1WRP=`, etc.

## Time Series Data (rd.get_history)

### Bond Futures RIC Mapping (CME → LSEG)

The timeseries module maps CME symbols to LSEG RICs for continuous contracts:

**US Treasury Futures:**

| CME Symbol | LSEG RIC | Contract | Month Codes |
|------------|----------|----------|-------------|
| ZT | TU | 2-Year T-Note | H, M, U, Z (quarterly) |
| Z3N | Z3N | 3-Year T-Note | H, M, U, Z (quarterly) |
| ZF | FV | 5-Year T-Note | H, M, U, Z (quarterly) |
| ZN | TY | 10-Year T-Note | H, M, U, Z (quarterly) |
| TN | TN | Ultra 10-Year | H, M, U, Z (quarterly) |
| TWE | TWE | 20-Year T-Bond | H, M, U, Z (quarterly) |
| ZB | US | 30-Year T-Bond | H, M, U, Z (quarterly) |
| UB | UB | Ultra 30-Year | H, M, U, Z (quarterly) |

**European Bond Futures:**

| CME Symbol | LSEG RIC | Contract |
|------------|----------|----------|
| FGBL | FGBL | Euro-Bund 10Y |
| FGBM | FGBM | Euro-Bobl 5Y |
| FGBS | FGBS | Euro-Schatz 2Y |
| FGBX | FGBX | Euro-Buxl 30Y |
| FLG | FLG | UK Long Gilt |

**RIC Patterns:**
- Continuous contracts: `{root}c1` (front), `{root}c2` (second), etc.
- Discrete contracts: `{root}{month}{year}` (e.g., `TYH5` = 10Y Note Mar 2025)
- Month codes: H=Mar, M=Jun, U=Sep, Z=Dec

**Example Usage:**
```python
# Continuous front month (LSEG stitches contracts automatically)
df = rd.get_history(universe=['TYc1'], fields=['SETTLE'], start='2024-01-01')

# Specific contract
df = rd.get_history(universe=['TYH5'], fields=['SETTLE'], start='2024-01-01')
```

### FX Spot RICs

| Pair Symbol | LSEG RIC | Description |
|-------------|----------|-------------|
| EURUSD | EUR= | Euro vs US Dollar |
| GBPUSD | GBP= | British Pound vs USD |
| USDJPY | JPY= | USD vs Japanese Yen |
| USDCHF | CHF= | USD vs Swiss Franc |
| AUDUSD | AUD= | Australian Dollar vs USD |
| USDCAD | CAD= | USD vs Canadian Dollar |
| NZDUSD | NZD= | New Zealand Dollar vs USD |
| EURGBP | EURGBP= | Euro vs British Pound |
| EURJPY | EURJPY= | Euro vs Japanese Yen |
| EURCHF | EURCHF= | Euro vs Swiss Franc |
| GBPJPY | GBPJPY= | British Pound vs Yen |

**Fields for FX:**
- `BID`, `ASK`: Bid/ask prices
- `BID_HIGH_1`, `BID_LOW_1`: Daily high/low on bid side

### OIS Curve RICs

**USD OIS (SOFR-based):**

Pattern: `USD{tenor}OIS=`

| Tenor | RIC | Description |
|-------|-----|-------------|
| 1M | USD1MOIS= | 1-month SOFR OIS |
| 2M | USD2MOIS= | 2-month SOFR OIS |
| 3M | USD3MOIS= | 3-month SOFR OIS |
| 6M | USD6MOIS= | 6-month SOFR OIS |
| 1Y | USD1YOIS= | 1-year SOFR OIS |
| 2Y | USD2YOIS= | 2-year SOFR OIS |
| 5Y | USD5YOIS= | 5-year SOFR OIS |
| 10Y | USD10YOIS= | 10-year SOFR OIS |
| 30Y | USD30YOIS= | 30-year SOFR OIS |

Available tenors: 1M, 2M, 3M, 4M, 5M, 6M, 9M, 1Y, 18M, 2Y, 3Y, 4Y, 5Y, 6Y, 7Y, 8Y, 9Y, 10Y, 12Y, 15Y, 20Y, 25Y, 30Y

### Treasury Yield Curve RICs

**US Treasury Yields:**

Pattern: `US{tenor}T=RRPS`

History note: recent `=RRPS` history can leave `MID_YLD_1` null while still
populating `B_YLD_1` / `A_YLD_1` plus `OPEN_YLD` / `HIGH_YLD` / `LOW_YLD`.
The toolkit now derives a usable mid-yield from those history fields when
needed.

| Tenor | RIC | Description |
|-------|-----|-------------|
| 1M | US1MT=RRPS | 1-month T-Bill yield |
| 3M | US3MT=RRPS | 3-month T-Bill yield |
| 6M | US6MT=RRPS | 6-month T-Bill yield |
| 1Y | US1YT=RRPS | 1-year yield |
| 2Y | US2YT=RRPS | 2-year T-Note yield |
| 3Y | US3YT=RRPS | 3-year T-Note yield |
| 5Y | US5YT=RRPS | 5-year T-Note yield |
| 7Y | US7YT=RRPS | 7-year T-Note yield |
| 10Y | US10YT=RRPS | 10-year T-Note yield |
| 20Y | US20YT=RRPS | 20-year T-Bond yield |
| 30Y | US30YT=RRPS | 30-year T-Bond yield |

Available tenors: 1M, 2M, 3M, 4M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y

### FRA RICs

**USD FRAs (Forward Rate Agreements):**

Pattern: `USD{tenor}F=`

| Tenor | RIC | Description |
|-------|-----|-------------|
| 1X4 | USD1X4F= | 1-month forward 3-month rate |
| 2X5 | USD2X5F= | 2-month forward 3-month rate |
| 3X6 | USD3X6F= | 3-month forward 3-month rate |
| 6X9 | USD6X9F= | 6-month forward 3-month rate |

### Supported Intervals

Valid `interval` parameter values for `rd.get_history()`:

| Interval | String | Retention Period | Use Case |
|----------|--------|------------------|----------|
| Tick | `"tick"` | ~30 days | High-frequency research |
| 1-Minute | `"1min"` | ~90 days | Intraday analysis |
| 5-Minute | `"5min"` | ~90 days | Intraday analysis |
| 10-Minute | `"10min"` | ~90 days | Intraday analysis |
| 30-Minute | `"30min"` | ~90 days | Intraday analysis |
| Hourly | `"hourly"` | ~90 days | Intraday patterns |
| Daily | `"daily"` | Full history | Standard analysis |
| Weekly | `"weekly"` | Full history | Long-term trends |
| Monthly | `"monthly"` | Full history | Macro analysis |

**Important:**
- 15-minute interval is **NOT supported** by LSEG API
- Intraday data (tick through hourly) has ~90-day retention
- Daily/weekly/monthly data has full historical coverage

**Example:**
```python
# Daily data (full history)
df = rd.get_history(universe=['TYc1'], interval='daily', start='2020-01-01')

# Intraday hourly (limited to ~90 days)
df = rd.get_history(universe=['EUR='], interval='hourly', start='2024-10-01', end='2024-12-31')
```

### Time Series Fields

**Futures OHLCV:**
- `OPEN_PRC`: Opening price
- `HIGH_1`: Daily high
- `LOW_1`: Daily low
- `TRDPRC_1`: Last traded price (close)
- `SETTLE`: Settlement price
- `ACVOL_UNS`: Volume (unsigned)
- `OPINT_1`: Open interest

**FX Fields:**
- `BID`, `ASK`: Bid/ask quotes
- `BID_HIGH_1`, `BID_LOW_1`: High/low on bid side

**Rates (OIS, Yields, FRAs):**
- `BID`, `ASK`: Bid/ask quotes
- `PRIMACT_1`, `HST_CLOSE`: common mid/rate history fields
- `MID_YLD_1`: primary yield field when populated
- `B_YLD_1`, `A_YLD_1`: bid/ask yield fields, useful fallback for US Treasury history
- `OPEN_YLD`, `HIGH_YLD`, `LOW_YLD`: intraperiod yield stats

## RIC Reference Guides

Detailed RIC documentation for specific asset classes:

| Guide | Coverage |
|-------|----------|
| [BOND_BASIS_RICS.md](ric-guides/BOND_BASIS_RICS.md) | Treasury futures deliverables, conversion factors |
| [CREDIT_DATA_RICS.md](ric-guides/CREDIT_DATA_RICS.md) | CDS indices (CDX IG/HY), sovereign CDS |
| [REPO_RATES_RICS.md](ric-guides/REPO_RATES_RICS.md) | US repo rates, SOFR, overnight rates |
| [TREASURY_DATA_SOURCES.md](ric-guides/TREASURY_DATA_SOURCES.md) | Treasury auction data, TreasuryDirect API |

For the complete validated instrument list (200+ RICs), see [INSTRUMENTS.md](INSTRUMENTS.md).
