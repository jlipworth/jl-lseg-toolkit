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
