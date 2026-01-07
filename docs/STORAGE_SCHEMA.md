# DuckDB Storage Schema Design

**Status**: DRAFT - Needs Review

## Overview

Different asset classes have fundamentally different data shapes. This schema normalizes by **data shape** rather than asset class.

## Data Shape Classification

| Data Shape | Asset Classes | Example RICs |
|------------|--------------|--------------|
| **OHLCV** | Futures, Equities, ETFs, Commodities, Indices | TYc1, AAPL.O, CLc1, .SPX |
| **Quote** | FX Spot, FX Forwards, OIS, IRS, FRA | EUR=, USD1YOIS=, USDIRS10Y= |
| **Bond Quote** | Govt Yields (price + yield + analytics) | US10YT=RRPS, DE10YT=RR |
| **Fixing** | Overnight rates (SOFR, ESTR, SONIA, EURIBOR) | USDSOFR=, EURIBOR3MD= |

---

## Open Questions

### Q1: Govt Bond Data - Separate Table?

Govt bonds return rich data including:
- **Price OHLC**: BID, ASK, MID_PRICE, OPEN_BID, BID_HIGH_1, BID_LOW_1
- **Yield OHLC**: B_YLD_1, A_YLD_1, MID_YLD_1, HIGH_YLD, LOW_YLD, OPEN_YLD
- **Analytics**: MOD_DURTN, CONVEXITY, BPV, ZSPREAD, OAS_BID, AST_SWPSPD

Options:
1. **Separate `bond_daily` table** - Store all bond-specific fields
2. **Use `quote_daily` + analytics columns** - Add bond columns to quote table
3. **Use `quote_daily` + separate `bond_analytics` table** - Normalize analytics

**Recommendation**: Option 1 - bonds are unique enough to warrant their own table.

### Q2: Intraday Quote Table

Should we have a separate `quote_intraday` table, or use `ohlcv_intraday` for everything?

Options:
1. **Separate tables** - `ohlcv_intraday` + `quote_intraday` (type safety)
2. **Single table** - All intraday in one table with NULLs

**Recommendation**: Option 1 for consistency with daily tables.

### Q3: Regional FX Session Data

LSEG returns Asia/Europe/America session OHLC for FX:
- ASIAOP_BID, ASIAHI_BID, ASIALO_BID, ASIACL_BID
- EUROP_BID, EURHI_BID, EURLO_BID, EURCL_BID
- AMEROP_BID, AMERHI_BID, AMERLO_BID, AMERCL_BID

Options:
1. **Store regional data** - 12 extra columns per row
2. **Skip regional data** - Just store daily bid/ask/mid
3. **Separate table** - `fx_session_data` for regional breakdown

**Recommendation**: Option 2 for now, can add later if needed.

### Q4: Value Date vs Trade Date

For FX forwards and swaps, LSEG provides:
- `VALUE_DT1` - Value date
- `MATUR_DATE` - Maturity date
- `START_DT` - Start date

Options:
1. **Index by trade date only** - Derive settlement as needed
2. **Store value/maturity dates** - Extra columns in detail tables

**Recommendation**: Store in detail tables, index by trade date.

---

### OHLCV Data (Exchange-Traded)

Fields from LSEG:
- `OPEN_PRC` → open
- `HIGH_1` → high
- `LOW_1` → low
- `TRDPRC_1` → close (last trade price)
- `SETTLE` → settle (official settlement, futures only)
- `ACVOL_UNS` → volume
- `OPINT_1` → open_interest (futures only)
- `VWAP` → vwap

### Quote Data (Dealer-Quoted)

Fields from LSEG:
- `BID` → bid
- `ASK` → ask
- `MID_PRICE` → mid
- `OPEN_BID` → open_bid
- `BID_HIGH_1` → bid_high
- `BID_LOW_1` → bid_low
- `OPEN_ASK` → open_ask
- `ASK_HIGH_1` → ask_high
- `ASK_LOW_1` → ask_low

### Fixing Data (Single Daily Value)

Fields from LSEG:
- `FIXING_1` or `PRIMACT_1` → value

---

## Schema Definition

### Instruments (Master Table)

```sql
CREATE TABLE instruments (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    asset_class VARCHAR NOT NULL,
    data_shape VARCHAR NOT NULL,  -- 'ohlcv', 'quote', 'fixing'
    lseg_ric VARCHAR NOT NULL,
    exchange VARCHAR,
    currency VARCHAR,
    description VARCHAR,
    -- Metadata
    created_at TIMESTAMP DEFAULT current_timestamp,
    updated_at TIMESTAMP DEFAULT current_timestamp
);

CREATE INDEX idx_instruments_symbol ON instruments(symbol);
CREATE INDEX idx_instruments_asset_class ON instruments(asset_class);
CREATE INDEX idx_instruments_data_shape ON instruments(data_shape);
```

**Asset Classes** (asset_class enum):
- `bond_futures`, `index_futures`, `commodity_futures`, `stir_futures`
- `equity`, `etf`
- `fx_spot`, `fx_forward`, `fx_ndf`
- `ois`, `irs`, `fra`, `money_market`
- `govt_yield`
- `overnight_fixing`
- `index`

**Data Shapes** (data_shape enum):
- `ohlcv` - exchange-traded instruments
- `quote` - dealer-quoted instruments
- `fixing` - daily benchmark fixings

### Instrument Detail Tables

```sql
-- Futures contract details
CREATE TABLE futures_details (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    underlying VARCHAR NOT NULL,
    expiry_date DATE,
    contract_month VARCHAR,      -- 'H5', 'M5', 'U5', 'Z5'
    continuous_type VARCHAR,     -- 'discrete', 'front', 'back'
    tick_size DOUBLE,
    point_value DOUBLE,
    exchange VARCHAR
);

-- FX instrument details
CREATE TABLE fx_details (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    base_currency VARCHAR NOT NULL,
    quote_currency VARCHAR NOT NULL,
    pip_size DOUBLE DEFAULT 0.0001,
    tenor VARCHAR               -- NULL for spot, '1W', '1M', etc for forwards
);

-- Rate instrument details (OIS, IRS, FRA)
CREATE TABLE rate_details (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    currency VARCHAR NOT NULL,
    tenor VARCHAR NOT NULL,
    reference_rate VARCHAR,     -- 'SOFR', 'ESTR', 'SONIA', etc
    day_count VARCHAR,          -- 'ACT/360', 'ACT/365', '30/360'
    payment_frequency VARCHAR,  -- 'annual', 'semi-annual', 'quarterly'
    start_tenor VARCHAR         -- For FRAs: '3M' in '3x6'
);

-- Government yield details
CREATE TABLE govt_yield_details (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    country VARCHAR NOT NULL,   -- 'US', 'DE', 'GB', 'JP'
    tenor VARCHAR NOT NULL,     -- '2Y', '10Y', '30Y'
    bond_type VARCHAR           -- 'nominal', 'inflation_linked'
);

-- Overnight fixing details
CREATE TABLE fixing_details (
    instrument_id INTEGER PRIMARY KEY REFERENCES instruments(id),
    rate_name VARCHAR NOT NULL, -- 'SOFR', 'ESTR', 'SONIA', 'EURIBOR'
    tenor VARCHAR,              -- NULL for overnight, '3M' for EURIBOR3M
    fixing_time VARCHAR,        -- '08:00 NY', '11:00 London'
    administrator VARCHAR       -- 'Fed', 'ECB', 'BoE'
);
```

### Time Series Tables

```sql
-- OHLCV data (futures, equities, commodities, indices)
CREATE TABLE ohlcv_daily (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    settle DOUBLE,              -- Futures settlement price
    volume BIGINT,
    open_interest BIGINT,
    vwap DOUBLE,
    -- For continuous contracts
    adjustment_factor DOUBLE DEFAULT 1.0,
    source_contract VARCHAR,
    PRIMARY KEY (instrument_id, date)
);

CREATE INDEX idx_ohlcv_daily_date ON ohlcv_daily(instrument_id, date DESC);

-- Quote data (FX, OIS, IRS, FRA, govt yields)
CREATE TABLE quote_daily (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    bid DOUBLE,
    ask DOUBLE,
    mid DOUBLE NOT NULL,
    -- OHLC for bid side (common in FX/rates)
    open_bid DOUBLE,
    bid_high DOUBLE,
    bid_low DOUBLE,
    -- OHLC for ask side
    open_ask DOUBLE,
    ask_high DOUBLE,
    ask_low DOUBLE,
    PRIMARY KEY (instrument_id, date)
);

CREATE INDEX idx_quote_daily_date ON quote_daily(instrument_id, date DESC);

-- Fixing data (SOFR, ESTR, SONIA, EURIBOR)
CREATE TABLE fixing_daily (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,         -- Fixing date (not publication date)
    value DOUBLE NOT NULL,
    volume DOUBLE,              -- For SOFR, transaction volume
    PRIMARY KEY (instrument_id, date)
);

CREATE INDEX idx_fixing_daily_date ON fixing_daily(instrument_id, date DESC);

-- Intraday OHLCV (futures, equities, commodities)
CREATE TABLE ohlcv_intraday (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    timestamp TIMESTAMP NOT NULL,
    granularity VARCHAR NOT NULL,  -- 'minute', '5min', '30min', 'hourly'
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    volume BIGINT,
    PRIMARY KEY (instrument_id, timestamp, granularity)
);

CREATE INDEX idx_ohlcv_intraday_ts ON ohlcv_intraday(instrument_id, timestamp DESC);

-- Intraday quote data (FX, rates)
CREATE TABLE quote_intraday (
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    timestamp TIMESTAMP NOT NULL,
    granularity VARCHAR NOT NULL,
    bid DOUBLE,
    ask DOUBLE,
    mid DOUBLE NOT NULL,
    PRIMARY KEY (instrument_id, timestamp, granularity)
);

CREATE INDEX idx_quote_intraday_ts ON quote_intraday(instrument_id, timestamp DESC);
```

### Metadata Tables

```sql
-- Roll events for continuous contracts
CREATE TABLE roll_events (
    id INTEGER PRIMARY KEY,
    continuous_id INTEGER NOT NULL REFERENCES instruments(id),
    roll_date DATE NOT NULL,
    from_contract VARCHAR NOT NULL,
    to_contract VARCHAR NOT NULL,
    from_price DOUBLE NOT NULL,
    to_price DOUBLE NOT NULL,
    price_gap DOUBLE NOT NULL,
    adjustment_factor DOUBLE NOT NULL,
    roll_method VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT current_timestamp
);

-- Extraction progress tracking
CREATE TABLE extraction_progress (
    id INTEGER PRIMARY KEY,
    instrument_id INTEGER REFERENCES instruments(id),
    granularity VARCHAR NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR DEFAULT 'pending',  -- pending, running, complete, failed
    rows_fetched INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message VARCHAR
);

-- Extraction log (historical record)
CREATE TABLE extraction_log (
    id INTEGER PRIMARY KEY,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    granularity VARCHAR NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    rows_fetched INTEGER NOT NULL,
    extracted_at TIMESTAMP DEFAULT current_timestamp
);
```

### Views

```sql
-- Data coverage summary
CREATE VIEW data_coverage AS
SELECT
    i.symbol,
    i.asset_class,
    i.data_shape,
    CASE i.data_shape
        WHEN 'ohlcv' THEN (SELECT MIN(date) FROM ohlcv_daily WHERE instrument_id = i.id)
        WHEN 'quote' THEN (SELECT MIN(date) FROM quote_daily WHERE instrument_id = i.id)
        WHEN 'fixing' THEN (SELECT MIN(date) FROM fixing_daily WHERE instrument_id = i.id)
    END as earliest,
    CASE i.data_shape
        WHEN 'ohlcv' THEN (SELECT MAX(date) FROM ohlcv_daily WHERE instrument_id = i.id)
        WHEN 'quote' THEN (SELECT MAX(date) FROM quote_daily WHERE instrument_id = i.id)
        WHEN 'fixing' THEN (SELECT MAX(date) FROM fixing_daily WHERE instrument_id = i.id)
    END as latest,
    CASE i.data_shape
        WHEN 'ohlcv' THEN (SELECT COUNT(*) FROM ohlcv_daily WHERE instrument_id = i.id)
        WHEN 'quote' THEN (SELECT COUNT(*) FROM quote_daily WHERE instrument_id = i.id)
        WHEN 'fixing' THEN (SELECT COUNT(*) FROM fixing_daily WHERE instrument_id = i.id)
    END as row_count
FROM instruments i;

-- Full futures view (joins details)
CREATE VIEW futures_full AS
SELECT
    i.*,
    f.underlying,
    f.expiry_date,
    f.contract_month,
    f.continuous_type,
    f.tick_size,
    f.point_value
FROM instruments i
JOIN futures_details f ON i.id = f.instrument_id;

-- Full rates view
CREATE VIEW rates_full AS
SELECT
    i.*,
    r.currency as rate_currency,
    r.tenor,
    r.reference_rate,
    r.day_count,
    r.payment_frequency
FROM instruments i
JOIN rate_details r ON i.id = r.instrument_id;
```

---

## Date Convention

### Primary Index: Trade Date (UTC)

All data is indexed by **trade date** in UTC:
- For exchange-traded: the exchange trading day
- For FX/rates: the quote date
- For fixings: the fixing date (not publication date)

### Settlement Date

Not stored as the primary index. Can be derived:
- Equities: T+1 (US), T+2 (Europe)
- FX Spot: T+2
- Futures: varies by contract

### Value Date

For FX forwards and swaps, use the `MATUR_DATE` field if needed.

---

## Field Mapping: LSEG → Storage

### OHLCV Instruments

| LSEG Field | Storage Column | Notes |
|------------|----------------|-------|
| OPEN_PRC | open | |
| HIGH_1 | high | |
| LOW_1 | low | |
| TRDPRC_1 | close | Last trade price |
| SETTLE | settle | Futures only |
| ACVOL_UNS | volume | |
| OPINT_1 | open_interest | Futures only |
| VWAP | vwap | |

### Quote Instruments

| LSEG Field | Storage Column | Notes |
|------------|----------------|-------|
| BID | bid | |
| ASK | ask | |
| MID_PRICE | mid | Calculated if not present |
| OPEN_BID | open_bid | |
| BID_HIGH_1 | bid_high | |
| BID_LOW_1 | bid_low | |
| OPEN_ASK | open_ask | |
| ASK_HIGH_1 | ask_high | |
| ASK_LOW_1 | ask_low | |

### Fixing Instruments

| LSEG Field | Storage Column | Notes |
|------------|----------------|-------|
| FIXING_1 | value | Primary fixing value |
| PRIMACT_1 | value | Alternative field |
| ACVOL_UNS | volume | Transaction volume (SOFR) |

---

## Parquet Export Structure

```
data/parquet/
├── ohlcv/
│   ├── bond_futures/
│   │   ├── TYc1/
│   │   │   ├── 2024.parquet
│   │   │   └── 2025.parquet
│   │   └── USc1/
│   ├── equity/
│   │   └── AAPL/
│   └── commodity/
│       └── CLc1/
├── quote/
│   ├── fx_spot/
│   │   └── EURUSD/
│   ├── ois/
│   │   └── USD/
│   │       ├── 1Y.parquet
│   │       └── 10Y.parquet
│   └── irs/
│       └── USD/
└── fixing/
    ├── SOFR.parquet
    ├── ESTR.parquet
    └── EURIBOR3M.parquet
```

---

## Query Examples

### Cross-Asset Queries

```sql
-- Get all USD rates data for a date
SELECT
    i.symbol,
    q.date,
    q.mid
FROM quote_daily q
JOIN instruments i ON i.id = q.instrument_id
JOIN rate_details r ON r.instrument_id = i.id
WHERE r.currency = 'USD'
  AND q.date = '2025-01-06'
ORDER BY r.tenor;

-- Get futures vs spot comparison
SELECT
    f.date,
    f.close as futures_price,
    s.mid as spot_price,
    f.close - s.mid as basis
FROM ohlcv_daily f
JOIN quote_daily s ON s.date = f.date
WHERE f.instrument_id = (SELECT id FROM instruments WHERE symbol = 'TYc1')
  AND s.instrument_id = (SELECT id FROM instruments WHERE symbol = 'US10YT')
ORDER BY f.date;
```

### Time Series Retrieval

```sql
-- Get daily data with proper shape routing
SELECT * FROM ohlcv_daily
WHERE instrument_id = ?
  AND date BETWEEN ? AND ?
ORDER BY date;

-- Or use helper function (in application code)
-- get_timeseries(symbol, start, end) routes to correct table
```
