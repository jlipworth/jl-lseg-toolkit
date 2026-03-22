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
- `docs/POLYMARKET_RESOLUTION.md`
  - working resolution and normalization spec for Polymarket macro/Fed data
- `docs/TEMP_POLYMARKET_FOMC_LINKS.md`
  - temporary troubleshooting note for candidate Polymarket ↔ FOMC links and
    cross-session comparison snapshots

## Doc Map

Use the Polymarket docs in this order:

1. `docs/PREDICTION_MARKETS.md`
   - top-level reference and workflow entry point
2. `docs/POLYMARKET_RESOLUTION.md`
   - canonical normalization and resolution spec
3. `docs/plans/POLYMARKET_IMPLEMENTATION.md`
   - implementation history, findings, and next tasks
4. `docs/TEMP_POLYMARKET_FOMC_LINKS.md`
   - temporary dry-run linkage and comparison troubleshooting note

Recommended interpretation:

- this file explains the module at a high level
- the resolution doc is the canonical semantic reference
- the implementation plan is the canonical build/history log
- the temporary FOMC link note is exploratory and should not be treated as
  production linkage policy

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
- `condition_id`
- `token_id`
- `event_slug`
- `question_slug`
- `strike_value`
- `status`
- `last_price`
- `last_trade_time`
- `volume`
- `open_interest`
- `updated_at` (our ingest timestamp)

## Polymarket Endpoint Roles

Polymarket should be treated as a multi-source system.

| Concern | Preferred source |
|---|---|
| discovery / search / grouping | Gamma API |
| event + market metadata | Gamma API |
| executed trade activity | Data API |
| last trade timestamp | Data API |
| best bid / ask / spread / midpoint | CLOB API |
| convenience enrichment | CLOB `/simplified-markets` |

Operational rule:

- **Gamma** is the structural source of truth
- **Data API** is the trade/freshness source of truth
- **CLOB** is the liquidity/orderbook source of truth

## Polymarket Normalization Summary

Core Polymarket modeling choice:

> **one Polymarket outcome token = one `pm_markets` row**

Current mapping:

| Polymarket concept | Internal representation |
|---|---|
| event | `pm_series` |
| condition / market question | grouped inside the event series |
| token / outcome | `pm_markets` row |
| trade-derived token history | `pm_candlesticks` row set |

Canonical identity fields for Polymarket:

- `series_ticker = event_slug`
- `condition_id`
- `token_id`
- `market_ticker = POLY:{condition_id}:{token_id}`

This is important for troubleshooting because:

- `event_slug` is the event-level grouping key
- `condition_id` is the question-level key
- `token_id` is the tradable outcome key

If two rows look similar, compare those three layers before assuming a duplicate
or a bad ingest.

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

## Polymarket Ingestion Paths

### Generic backfill

Entry point:

- `polymarket.backfill(conn)`

Current behavior:

- seed Polymarket platform
- fetch Gamma market pages
- normalize event buckets into `pm_series`
- normalize token/outcome rows into `pm_markets`

### Generic active refresh

Entry point:

- `polymarket.daily_refresh(conn)`

Current behavior:

- seed Polymarket platform
- fetch active Gamma markets
- fetch simplified CLOB market rows for enrichment
- fetch latest trade timestamps from Data API
- upsert token/outcome rows into `pm_markets`

### Targeted macro/Fed discovery ingest

Entry point:

- `polymarket.backfill_fed_discovery(conn)`
- dry-run review helper: `polymarket.discover_fed_event_summaries(conn=...)`

Current behavior:

- seed with Gamma public search
- expand via Gamma tags
- fetch Gamma events
- flatten nested event markets
- ingest discovered token/outcome rows

Important note:

- generic active-market pagination is a plumbing path
- targeted event-centric discovery is the current preferred path for macro/Fed
  research workflows
- the dry-run summary helper is intended to guide manual review, not to
  auto-write FOMC linkage

### Dry-run review example

Notebook/script-friendly example:

```python
import pandas as pd

from lseg_toolkit.timeseries.prediction_markets.polymarket import (
    discover_fed_event_summaries,
)
from lseg_toolkit.timeseries.storage import get_connection

with get_connection() as conn:
    rows = discover_fed_event_summaries(
        conn=conn,
        active=None,
        closed=None,
    )

df = pd.DataFrame(rows)
print(
    df[
        [
            "event_slug",
            "close_date",
            "family",
            "suggested_fomc_meeting_id",
            "reason",
        ]
    ].to_string(index=False)
)
```

Recommended manual review flow:

1. inspect `family`
2. inspect `suggested_fomc_meeting_id`
3. verify the event title/slug still means what we think it means
4. only then decide whether to treat the row as trusted for comparison or
   linkage work

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

## Polymarket Freshness and Liquidity Semantics

For Polymarket, distinguish these concepts explicitly:

1. **`last_trade_time`**
   - latest observed executed trade timestamp
   - best primary freshness signal for active contracts
2. **`last_price`**
   - best available current token snapshot price
   - not necessarily the same as the most recent trade price
3. **best bid / ask / spread**
   - liquidity/tradability signal
   - belongs to CLOB-style troubleshooting, not basic metadata troubleshooting
4. **event liquidity / event volume**
   - useful context
   - not a substitute for token-level tradability

Recommended troubleshooting order for Polymarket:

1. inspect `event_slug`, `condition_id`, and `token_id`
2. inspect `status`
3. inspect `last_trade_time`
4. inspect current token `last_price`
5. inspect best bid / ask / spread if tradability is the question

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

## Polymarket Troubleshooting Workflow

When Polymarket and Kalshi appear to disagree, check in this order:

1. **resolution**
   - is the Polymarket contract actually in a resolved family we trust?
   - use `docs/POLYMARKET_RESOLUTION.md`
2. **meeting linkage**
   - is the Polymarket event actually tied to the same FOMC date?
   - do not assume date alignment from slug text alone
3. **token interpretation**
   - confirm which token/outcome row you are comparing
   - verify `outcome_label`
4. **freshness**
   - inspect `last_trade_time`
   - stale differences are often just timestamp differences
5. **liquidity**
   - inspect best bid / ask / spread before over-interpreting a price
6. **aggregation logic**
   - confirm whether the contract is a meeting decision, cut-count market,
     year-end rate view, or Powell wording market

Avoid comparing raw prices across platforms before confirming all six.

## Worked Polymarket Troubleshooting Examples

### Example 1: Meeting decision vs meeting decision

Safe comparison:

- Polymarket event: `fed-decision-in-april`
- Kalshi family: `KXFEDDECISION` or a meeting-aligned rate-decision view

Why this is safe:

- both are trying to describe a specific FOMC decision distribution
- event date can be checked against `fomc_meetings`
- Polymarket token outcomes can be mapped into hold/cut/hike buckets

Checks before trusting the comparison:

- exact FOMC date match
- correct Polymarket outcome token mapping
- recent `last_trade_time`
- reasonable bid/ask spread

### Example 2: Powell wording vs Kalshi rate market

Unsafe direct comparison:

- Polymarket event:
  `what-will-powell-say-during-march-press-conference`
- Kalshi event: March rate decision market

Why this is unsafe:

- both may align to the same meeting date
- but they are not the same economic object
- one is language/communication risk, the other is policy-rate outcome risk

Correct treatment:

- keep the Powell market as meeting-linked context
- do not treat it as direct policy-distribution parity

### Example 3: Year-end rate view vs single-meeting decision

Unsafe direct comparison:

- Polymarket event: `what-will-the-fed-rate-be-at-the-end-of-2026`
- Kalshi event: `KXFEDDECISION-26JUN-...`

Why this is unsafe:

- year-end rate markets aggregate expectations across multiple future meetings
- single-meeting decision markets describe only one meeting

Correct treatment:

- compare only inside a horizon-consistent framework
- do not auto-link year-end rate markets to one `fomc_meeting_id`

## TSDB Row Inspection Checklist

When troubleshooting a Polymarket row already stored in TSDB, inspect these
fields first:

### Series level

- `pm_series.series_ticker`
- `pm_series.title`

For Polymarket, `series_ticker` should generally match the **event slug**.

### Market level

- `pm_markets.market_ticker`
- `pm_markets.platform_market_id`
- `pm_markets.event_ticker`
- `pm_markets.condition_id`
- `pm_markets.token_id`
- `pm_markets.event_slug`
- `pm_markets.question_slug`
- `pm_markets.title`
- `pm_markets.subtitle`
- `pm_markets.outcome_label`
- `pm_markets.status`
- `pm_markets.last_price`
- `pm_markets.last_trade_time`
- `pm_markets.fomc_meeting_id`
- `pm_markets.updated_at`

### Quick interpretation guide

- `series_ticker` / `event_slug`
  - event-level grouping
- `condition_id`
  - question-level identity
- `token_id`
  - tradable outcome identity
- `market_ticker`
  - should be `POLY:{condition_id}:{token_id}`
- `subtitle` / `outcome_label`
  - the specific token outcome being compared
- `last_trade_time`
  - best freshness signal
- `updated_at`
  - our ingest timestamp, not source freshness

### Minimal troubleshooting questions

1. am I looking at the correct event?
2. am I looking at the correct question/condition?
3. am I looking at the correct token/outcome?
4. is the row fresh enough to compare?
5. is this market family actually comparable to the Kalshi row?

## Operational Notes

Recommended checks when something looks stale:

- inspect `last_trade_time`
- inspect live orderbook
- inspect recent trades
- do **not** conclude a market is stale from Kalshi `updated_time` alone

Recommended Polymarket checks when something looks wrong:

- inspect `event_slug`
- inspect `condition_id`
- inspect `token_id`
- inspect `outcome_label`
- inspect `last_trade_time`
- inspect whether the contract family is actually comparable to Kalshi

## Known Gaps

- Polymarket ingestion
- finalized Polymarket family-resolution implementation
- Polymarket trade-derived candlestick generation
- Polymarket troubleshooting examples/tests in docs
- automated FedWatch scraping/export retrieval
- richer reference docs / examples for PM comparison workflows
