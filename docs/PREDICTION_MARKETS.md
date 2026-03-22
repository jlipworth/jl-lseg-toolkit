# Prediction Markets

Reference notes for the prediction-market ingestion and comparison workflow.

## Scope

This module currently focuses on:

- **Kalshi** policy/rates markets
- **FOMC** meeting calendar + historical decision linkage
- **FedWatch** comparison inputs

Current implementation status:

- Implemented:
  - FOMC historical sync
  - future FOMC calendar scrape
  - Kalshi market/candlestick ingestion
  - Kalshi active-market refresh
  - implied probability reconstruction helpers
  - manual FedWatch loader scaffolding
- Not yet implemented:
  - full Polymarket ingestion / candlestick history
  - full FedWatch automated scraping/export retrieval

Current exploratory Polymarket work:

- `src/lseg_toolkit/timeseries/prediction_markets/polymarket/`
  - mirrors the Kalshi module layout with a `client.py` and `extractor.py`
- `docs/plans/POLYMARKET_IMPLEMENTATION.md`
  - actively updated implementation plan
- `docs/TEMP_POLYMARKET_FOMC_LINKS.md`
  - temporary troubleshooting note for candidate Polymarket ↔ FOMC links and
    cross-session comparison snapshots

## Main Modules

- `src/lseg_toolkit/timeseries/fomc/`
  - FOMC meeting history + future schedule
- `src/lseg_toolkit/timeseries/prediction_markets/kalshi/`
  - Kalshi client + extractor
- `src/lseg_toolkit/timeseries/prediction_markets/fedwatch/`
  - FedWatch file loader helpers
- `src/lseg_toolkit/timeseries/prediction_markets/analysis/`
  - probability reconstruction + comparison helpers

## Storage Model

Primary tables:

- `fomc_meetings`
- `pm_platforms`
- `pm_series`
- `pm_markets`
- `pm_candlesticks`

Key relationships:

- `pm_series.platform_id -> pm_platforms.id`
- `pm_markets.series_id -> pm_series.id`
- `pm_markets.fomc_meeting_id -> fomc_meetings.id`
- `pm_candlesticks.market_id -> pm_markets.id`

Important market fields:

- `market_ticker`
- `event_ticker`
- `strike_value`
- `status`
- `last_price`
- `last_trade_time`
- `volume`
- `open_interest`
- `updated_at` (our ingest timestamp)

## Kalshi Series

Currently ingested series:

- `KXFED`
  - laddered “upper bound above X% after meeting” markets
- `KXFEDDECISION`
  - discrete hike/cut/hold style contracts
- `KXRATECUTCOUNT`
  - cumulative cut-count contracts

Examples:

- `KXFED-26MAR-T4.50`
- `KXFEDDECISION-27DEC-H25`
- `KXRATECUTCOUNT-26DEC31-T4`

## FOMC Linkage

Markets are linked to `fomc_meetings` using the Kalshi market `close_time`
date. This supports:

- grouping markets by meeting
- comparing Kalshi distributions to FOMC outcomes
- joining prediction-market state to historical decision metadata

## Ingestion Paths

### Historical / backfill

Entry point:

- `backfill(conn)`

Behavior:

- sync FOMC meetings
- fetch Kalshi series + markets
- store settled/finalized market candlesticks

### Active refresh

Entry point:

- `daily_refresh(conn)`

Behavior:

- sync FOMC meetings
- fetch active Kalshi markets
- update market metadata
- populate `last_trade_time` from the most recent trade
- fetch active-market candlesticks

## Freshness Semantics

For Kalshi rates products, **do not rely on source `updated_time` as the main
freshness signal**.

Observed behavior:

- `updated_time` can appear stale across many rate contracts
- trades may still be printing
- orderbooks may still be live

Use these fields/signals instead:

1. **`pm_markets.last_trade_time`**
   - best primary freshness signal for active markets
2. `pm_candlesticks.ts`
   - useful for daily history freshness
3. live orderbook / trade endpoints
   - useful for real-time comparison and execution checks

Note:

- `pm_markets.updated_at` is **our database ingest timestamp**, not Kalshi's
  source freshness field

## FedWatch

Current FedWatch support is oriented around **manual files**:

- CSV
- XLS/XLSX
- ad hoc PDF snapshots for visual sanity checks

Loader module:

- `src/lseg_toolkit/timeseries/prediction_markets/fedwatch/loader.py`

Current limitations:

- no automated CME export retrieval yet
- PDF snapshots are useful for quick comparisons, but not as the canonical
  ingestion format

## Comparison Workflow

Typical workflow:

1. sync FOMC meetings
2. refresh Kalshi markets
3. load FedWatch snapshot/export
4. reconstruct Kalshi implied probabilities
5. compare by meeting date and rate bucket / exceedance threshold

Relevant helpers:

- `analysis/probability.py`
- `analysis/comparison.py`

## Operational Notes

Recommended checks when something looks stale:

- inspect `last_trade_time`
- inspect live orderbook
- inspect recent trades
- do **not** conclude a market is stale from Kalshi `updated_time` alone

## Known Gaps

- Polymarket ingestion
- automated FedWatch scraping/export retrieval
- richer reference docs / examples for PM comparison workflows
