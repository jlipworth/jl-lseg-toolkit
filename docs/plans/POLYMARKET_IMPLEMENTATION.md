# Polymarket Prediction Markets Implementation Plan

**Status:** Planning
**Created:** 2026-03-21
**Branch:** `feature/prediction-markets`

---

## Objective

Add **read-only Polymarket ingestion** to the prediction-markets module, using the
existing TimescaleDB prediction-market schema wherever possible and following the
same architectural pattern used for Kalshi.

This plan is grounded in:

- the existing Kalshi implementation in `src/lseg_toolkit/timeseries/prediction_markets/kalshi/`
- the current prediction-markets schema/models/storage layer
- live TSDB inspection of how Kalshi data is actually stored
- live verification that public Polymarket endpoints are reachable for market data
- the normalization/resolution rules in `docs/POLYMARKET_RESOLUTION.md`

---

## Scope

### In scope (Phase 1 / MVP)

- Public Polymarket market metadata ingestion
- Public Polymarket trade ingestion
- Token/outcome-level representation in `pm_markets`
- Latest price / latest trade timestamp refresh
- Optional recent best bid/ask snapshot enrichment from public CLOB endpoints
- Basic derived candlestick generation from trade history

### Out of scope (initially)

- Trading / order placement
- Authenticated user endpoints
- Portfolio/account state
- US-based execution workflows
- Full analytics parity with Kalshi Fed-rate ladders

---

## Key Decision: Reuse Existing Prediction-Market Schema

**No major schema rewrite is required for MVP.**

The current schema is flexible enough to support Polymarket if we model:

> **one Polymarket outcome token = one `pm_markets` row**

This matches how the existing schema already handles:

- contracts with and without `strike_value`
- optional `fomc_meeting_id`
- optional `last_trade_time`
- partially populated candlesticks

### Current schema fit

Existing core tables:

- `pm_platforms`
- `pm_series`
- `pm_markets`
- `pm_candlesticks`

### Mapping decision

| Polymarket concept | Existing table/field |
|--------------------|----------------------|
| Platform | `pm_platforms` |
| Event/group | `pm_series` |
| Outcome token | `pm_markets` |
| Trade-derived bar | `pm_candlesticks` |

---

## Validated Findings (2026-03-21)

### 1. Infisical / TSDB access path

The TimescaleDB credentials are available via:

```bash
infisical export --env=dev --path="/kubernetes/infrastructure/timescaledb"
```

Exported keys:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

This was verified by exporting a temporary env file and successfully querying
the live TSDB instance.

### 2. Current Kalshi live TSDB representation

Live counts observed:

- platforms: **1**
- series: **3**
- markets: **740**
- candlesticks: **107090**

Kalshi series counts:

| Series | Markets | With FOMC Link | With `last_trade_time` | With `strike_value` |
|--------|---------|----------------|-------------------------|---------------------|
| `KXFED` | 489 | 486 | 128 | 489 |
| `KXFEDDECISION` | 200 | 75 | 80 | 0 |
| `KXRATECUTCOUNT` | 51 | 0 | 21 | 51 |

### 3. How Kalshi is actually stored

Observed conventions in live TSDB:

- `market_ticker == platform_market_id`
- `event_ticker` groups related contracts
- `subtitle` carries the human-readable outcome label
- `strike_value` is optional
- `fomc_meeting_id` is optional
- `last_trade_time` is optional
- `pm_candlesticks` may contain:
  - full OHLC
  - or only bid/ask + volume/open_interest, with OHLC null

### 4. Existing data-quality wrinkle

At least one event-ticker inconsistency was observed in stored Kalshi rows:

- `RATECUTCOUNT-24DEC31`
- `KXRATECUTCOUNT-25DEC31`
- `KXRATECUTCOUNT-26DEC31`

This is a reminder that identifier normalization should be explicit in the
Polymarket implementation.

### 5. Public Polymarket data is reachable

Public Polymarket endpoints responded successfully when called with normal HTTP
headers/user-agent from this environment:

- Gamma API
- Data API
- public CLOB market endpoints

This supports a **read-only ingestion** approach without requiring a paid API.

### 6. Geoblock caveat

Polymarket's geoblock endpoint reported this US environment as blocked for
regulated access. That does **not** prevent public read-only data collection,
but it reinforces that Phase 1 should be **data ingestion only**, not trading.

### 7. Live TSDB ingest result: generic active-page ingest is not sufficient for Fed work

A limited live ingest was run into TSDB after applying the branch's idempotent
PM schema migration.

Observed result:

- Polymarket platform seeded successfully
- one-page backfill and one-page refresh both completed successfully
- token-level `pm_markets` rows were stored as expected
- `last_trade_time` populated for a meaningful subset of active rows

However:

- the ingested active-market universe was dominated by sports / entertainment /
  crypto / general event contracts
- no genuine Fed/FOMC/rate-cut contracts were surfaced in the ingested sample
- a broader scan of 500 active Polymarket markets also returned **0 hits** for:
  - `federal reserve`
  - `fomc`
  - `rate cut`
  - `interest rate`
  - `fed funds`
  - `powell`
  - `cpi`

**Implication:** generic "first page of active markets" ingestion is valid as a
plumbing test, but it is **not enough** for macro/Fed research workflows.

We need an explicit **targeted discovery layer** for macro/Fed contracts.

### 8. Live targeted discovery result: search + tags + events works

A targeted discovery path was then implemented and validated against live
Polymarket data on **2026-03-21**.

Discovery method:

- seed with Gamma **`/public-search`**
- expand candidate tags from **`/tags`**
- fetch event payloads via **`/events?tag_id=...&related_tags=true`**
- flatten nested event markets into ingestable market rows

Observed result:

- discovered events: **74**
- discovered raw market contracts: **522**
- targeted TSDB ingest wrote **74 series** and **1,044 `pm_markets` rows**
  (mostly binary contracts represented as two token rows)

This surfaced the contracts we actually care about for Fed/FOMC work, including:

- `fed-decision-in-april`
- `fed-decision-in-june-825`
- `fed-decision-in-july-181`
- `fed-rate-cut-by-629`
- `what-will-the-fed-rate-be-at-the-end-of-2026`
- `what-will-powell-say-during-march-press-conference`

It also produced exact date matches against `fomc_meetings.meeting_date` for a
meaningful set of Polymarket event series, confirming that **event-centric
discovery is the right ingestion path for FOMC-linked Polymarket data**.

---

## Source Systems / Endpoints

### Primary Polymarket sources

1. **Gamma API**
   - event/market metadata
   - slugs, question text, dates, active/closed/resolved flags

2. **Data API**
   - recent/historical trades
   - useful for `last_trade_time` and trade-derived bars
   - use documented `market=<condition_id>` + `offset` pagination
   - token-level filtering should use `asset == token_id`

3. **Public CLOB endpoints**
   - market snapshots
   - token prices
   - best bid/ask or simplified market state

4. **Public websocket market channel** (later phase)
   - real-time market updates
   - best bid/ask / price-change events

---

## Proposed Polymarket Mapping

### `pm_platforms`

Add a Polymarket seed row:

```text
name         = polymarket
display_name = Polymarket
api_base_url = https://gamma-api.polymarket.com
is_regulated = false
currency     = USD
```

### `pm_series`

Use **event/group-level** identifiers.

Preferred mapping:

- `series_ticker = eventSlug`

Fallbacks:

- normalized market slug
- category/event-group slug
- synthetic stable event key

### `pm_markets`

Use **one row per token / outcome**.

Recommended field mapping:

| `pm_markets` field | Polymarket source |
|--------------------|-------------------|
| `market_ticker` | synthetic stable key: `POLY:{condition_id}:{token_id}` |
| `platform_market_id` | `token_id` |
| `event_ticker` | `condition_id` |
| `title` | question |
| `subtitle` | outcome label |
| `strike_value` | numeric threshold only when genuinely applicable |
| `open_time` | market/event start time |
| `close_time` | market/event end time |
| `status` | normalized active/closed/settled |
| `result` | winning outcome if resolved |
| `last_price` | current token price |
| `last_trade_time` | latest trade timestamp |
| `volume` | token or market volume where available |
| `open_interest` | null initially unless a reliable field exists |
| `fomc_meeting_id` | nullable; only for macro/Fed-linked markets |

### `pm_candlesticks`

Polymarket bars should be **derived from trades**, not treated as source-native.

Use:

- `price_open/high/low/close/mean` from aggregated trades
- `yes_bid_close` / `yes_ask_close` from public book/snapshot data when available
- `volume` from summed trade size
- `open_interest` left null unless a reliable platform field is found

Current implementation details:

- bars are grouped by **UTC trade date**
- `ts` is anchored at **00:00:00 UTC**
- `price_mean` is **size-weighted**
- `volume` is currently stored as a **rounded integer** because the shared
  schema uses `INTEGER`, even though Polymarket trade size is fractional
- deep-offset trade pagination may return HTTP 400; the current backfill treats
  `offset > 0` 400s as end-of-history for that condition
- practical bid/ask enrichment appears limited to **current** token orderbook
  snapshots from CLOB `/book`, not true historical daily bid/ask close history

---

## Recommended Minimal Schema Extension

MVP can be implemented without schema changes, but a small nullable extension is
recommended to avoid overloading generic fields too heavily.

### Suggested new nullable columns on `pm_markets`

```sql
ALTER TABLE pm_markets ADD COLUMN IF NOT EXISTS condition_id TEXT;
ALTER TABLE pm_markets ADD COLUMN IF NOT EXISTS token_id TEXT;
ALTER TABLE pm_markets ADD COLUMN IF NOT EXISTS outcome_label TEXT;
ALTER TABLE pm_markets ADD COLUMN IF NOT EXISTS event_slug TEXT;
ALTER TABLE pm_markets ADD COLUMN IF NOT EXISTS question_slug TEXT;
```

### Why these help

- cleaner Polymarket representation
- easier debugging and backfills
- less dependence on synthetic parsing of `market_ticker`
- no negative impact on Kalshi

If we choose not to extend schema immediately, the MVP can still proceed using:

- `event_ticker = condition_id`
- `platform_market_id = token_id`
- `subtitle = outcome label`

---

## Architecture: Mirror the Kalshi Pattern

### Existing Kalshi structure

- `kalshi/client.py`
- `kalshi/extractor.py`
- shared `models.py`
- shared `schema.py`
- shared `storage.py`

### Polymarket should follow the same shape

Add:

```text
src/lseg_toolkit/timeseries/prediction_markets/polymarket/__init__.py
src/lseg_toolkit/timeseries/prediction_markets/polymarket/client.py
src/lseg_toolkit/timeseries/prediction_markets/polymarket/extractor.py
```

Optional helper modules:

```text
src/lseg_toolkit/timeseries/prediction_markets/polymarket/normalization.py
src/lseg_toolkit/timeseries/prediction_markets/polymarket/trades.py
```

---

## Implementation Tasks

Status note as of 2026-03-22:

- Phases 0-3 are largely complete for metadata/discovery
- conservative family resolution + dry-run FOMC suggestion helpers are in place
- no automatic Polymarket `fomc_meeting_id` writes are enabled
- the main remaining engineering block is historical trades -> derived
  candlesticks

### Phase 0: Schema / platform prep

- [x] **0.1** Add `seed_polymarket_platform(conn)` to `prediction_markets/schema.py`
- [x] **0.2** Decide whether to add Polymarket-specific nullable columns to `pm_markets`
- [x] **0.3** Add schema migration/tests if those columns are added

### Phase 1: Public client

- [x] **1.1** Implement `PolymarketClient` in `polymarket/client.py`
- [x] **1.2** Add request helper with:
  - retries on 429/5xx
  - basic throttling
  - standard user-agent/header handling
- [x] **1.3** Implement metadata fetch methods:
  - `list_events(...)`
  - `list_markets(...)`
  - `list_simplified_markets(...)`
- [x] **1.4** Implement trade fetch methods:
  - `get_trades(...)`
  - `get_last_trade_time(...)`

### Phase 2: Normalization

- [x] **2.1** Implement stable synthetic `market_ticker` builder
- [x] **2.2** Implement event/series normalization
- [x] **2.3** Implement token/outcome normalization into `Market`
- [x] **2.4** Implement status normalization:
  - Polymarket raw states → `active` / `closed` / `settled`
- [x] **2.5** Implement timestamp normalization
- [x] **2.6** Implement identifier normalization tests to avoid Kalshi-style drift

### Phase 3: Metadata ingestion

- [x] **3.1** Implement `upsert` flow for Polymarket series
- [x] **3.2** Implement token-level market upserts
- [ ] **3.3** Populate:
  - `last_price`
  - `volume`
  - `status`
  - `last_trade_time`
- [x] **3.4** Add summary return structure similar to Kalshi `daily_refresh()`

### Phase 3b: Targeted market discovery for macro/Fed use cases

The live ingest validated that broad active-market pagination is insufficient
for finding the contracts we actually care about in the rates workflow.

- [x] **3b.1** Add a targeted Polymarket discovery helper in the client or extractor
- [x] **3b.2** Support discovery by keyword/query terms across title / slug / event fields
- [x] **3b.3** Include both **active** and **closed** markets in discovery mode
- [ ] **3b.4** Start with a curated search list for macro/rates:
  - `fed`
  - `fomc`
  - `federal reserve`
  - `rate cut`
  - `interest rate`
  - `fed funds`
  - `powell`
  - `cpi`
  - `inflation`
  - `recession`
- [x] **3b.5** Persist only matched/approved markets for the macro workflow instead of
  relying on generic first-page ingestion
- [x] **3b.6** Add tests for the discovery/filtering logic so false positives like
  “federal charge” are excluded from Fed/rates workflows
- [x] **3b.7** Add a discovery summary/reporting mode to show:
  - matched series/event slugs
  - matched titles
  - close dates
  - candidate FOMC linkage opportunities
- [x] **3b.8** Ensure discovery outputs can be passed through the documented
  resolution spec in `docs/POLYMARKET_RESOLUTION.md`

Implementation note:

- discovery should be **event-centric, search-seeded, and tag-filtered**
- generic `/markets` pagination should remain a fallback/enrichment path, not the
  primary discovery path

### Phase 3c: FOMC sanity-check workflow

Once targeted discovery exists, add a narrow sanity-check flow against
`fomc_meetings` in TSDB.

- [x] **3c.1** For discovered Fed/FOMC candidates, compare `close_time::date` to `fomc_meetings.meeting_date`
- [x] **3c.2** Report:
  - exact matches
  - near matches (±1 day)
  - obvious mismatches
- [ ] **3c.3** Only populate `fomc_meeting_id` when the linkage is high-confidence
- [ ] **3c.4** Add regression tests around date-linkage heuristics

Current recommendation after live validation:

- do **not** bulk-write `fomc_meeting_id` yet
- keep using the dry-run candidate list in `docs/TEMP_POLYMARKET_FOMC_LINKS.md`
- when we do write linkage, restrict the first pass to:
  - exact `close_time::date = meeting_date`
  - clearly Fed/FOMC/rates-oriented series only
  - explicit exclusions for legal/political “federal” false positives

### Phase 4: Historical trade ingestion

- [x] **4.1** Add trade fetch pagination/chunking strategy
- [x] **4.2** Normalize trade rows into an internal trade representation
- [ ] **4.3** Decide whether to persist raw trades separately later
- [x] **4.4** For MVP, at minimum support trade-based bar reconstruction without raw-trade persistence

### Phase 5: Derived candlesticks

- [x] **5.1** Aggregate trades into bars (daily first; intraday optional)
- [x] **5.2** Map aggregated bars into `Candlestick`
- [ ] **5.3** Enrich `yes_bid_close` / `yes_ask_close` from public market snapshot data when possible
- [x] **5.4** Upsert bars into `pm_candlesticks`

### Phase 6: Extractor/orchestration

- [x] **6.1** Implement `backfill(conn)` in `polymarket/extractor.py`
- [x] **6.2** Implement `daily_refresh(conn)` in `polymarket/extractor.py`
- [ ] **6.3** Follow Kalshi-style FK order:
  1. seed platform
  2. upsert series
  3. upsert markets
  4. fetch trades / derive bars
  5. upsert candlesticks
  - current state: explicit/manual wrapper `backfill_with_candlesticks()` exists,
    but bars are not yet folded into default `backfill()` / `daily_refresh()`
- [ ] **6.4** Make the flow idempotent and resumable
- [ ] **6.5** Tolerate partial failures per market/token

### Phase 7: Optional macro/Fed linkage

- [x] **7.0** Implement conservative Polymarket family resolver matching
  `docs/POLYMARKET_RESOLUTION.md`
- [x] **7.1** Add market-family resolution for Fed/macro-related Polymarket contracts
- [ ] **7.2** Link those to `fomc_meetings` when the mapping is high-confidence
- [x] **7.3** Keep all linkage nullable and optional

Note: this phase depends on **Phase 3b targeted discovery**. The live ingest
showed that linkage work should not be attempted off generic active-page
sampling alone.

### Phase 8: Documentation

- [x] **8.1** Update `docs/PREDICTION_MARKETS.md`
- [x] **8.2** Update `docs/OUTSTANDING.md`
- [x] **8.3** Update `docs/TESTING.md`
- [x] **8.4** Document:
  - public read-only access model
  - geoblock/trading caveat
  - trade-derived bar semantics
  - source-native vs reconstructed fields

### Phase 8b: Exploration follow-ups / session handoff

- [x] **8b.1** Keep a temporary troubleshooting note with Polymarket ↔ FOMC dry-run links
- [x] **8b.2** Record temporary Polymarket vs Kalshi comparison snapshots for cross-session reference
- [ ] **8b.3** Retest Polymarket vs Kalshi liquidity during **U.S. daylight hours**
- [ ] **8b.4** Add a small matched-liquidity comparison table for:
  - April / June / July Fed decisions
  - 2026 cut-count buckets
  - selected end-2026 rate buckets
- [ ] **8b.5** Decide whether to convert the temporary troubleshooting note into a longer-lived reference doc or fold it into `docs/PREDICTION_MARKETS.md`

---

## Testing Plan

### Unit tests

Add:

- `tests/timeseries/test_polymarket_client.py`
- `tests/timeseries/test_polymarket_extractor.py`
- `tests/timeseries/test_polymarket_resolution.py`

Cover:

- pagination
- retry behavior
- status normalization
- token/outcome mapping
- identifier normalization
- timestamp parsing
- trade aggregation into bars

### DB-backed tests

Add real Postgres-backed tests for:

- platform seeding
- series upsert
- market upsert
- candlestick upsert
- explicit/manual `backfill_candlesticks()` smoke
- extractor backfill/refresh smoke

### Live smoke tests

Add at least one opt-in live smoke test hitting public Polymarket endpoints:

- Gamma metadata
- Data API trades
- public CLOB snapshot endpoint

This should be marked clearly and not run by default in CI.

---

## Analytics Implications

### Current state

The current analysis helpers are **Kalshi-specific**, especially:

- `rate_distribution()`
- `implied_rate()`
- FedWatch comparison helpers

These assume a `KXFED` strike ladder.

### Decision

Polymarket ingestion should **not** be blocked on immediate analytics parity.

Instead:

- keep Polymarket ingestion generic
- later add Polymarket-specific comparison helpers where useful
- only add Fed-specific Polymarket analytics after ingestion is stable

---

## Risks / Open Questions

### 1. Token-level volume semantics

Need to confirm whether the best available volume field is:

- per token
- per market
- rolling vs lifetime

### 2. Orderbook snapshot semantics

Need to confirm which public endpoint is best for:

- best bid
- best ask
- end-of-day snapshot semantics

Current partial answer:

- live `bestBid` / `bestAsk` are available from Gamma event-market payloads
- full public orderbook snapshots are available from CLOB `/book` by token id
- however, we have **not** yet defined a canonical archival/snapshot policy for
  storing Polymarket orderbook state over time

### 3. Historical completeness

Need to confirm how far back trade history can be fetched reliably from public
endpoints and whether paging limits require chunking.

### 4. Event grouping choice

Need to lock whether `series_ticker` should be:

- `eventSlug`
- `slug`
- or another normalized grouping key

### 5. Optional schema extension timing

Need to decide whether to:

- ship MVP first with current schema
- or add the nullable Polymarket-specific columns upfront

My recommendation: **add the small nullable extension early**.

### 6. Discovery strategy for macro/Fed contracts

Open question:

- can Gamma endpoints support sufficiently precise query-side filtering for
  macro/rates discovery, or do we need app-side filtering after broader fetches?

Current recommendation:

- start with app-side targeted filtering against a larger fetched universe
- promote to a more selective query strategy later if the API supports it cleanly

### 7. Liquidity comparison methodology

Open question:

- what is the best apples-to-apples liquidity comparison between Polymarket and
  Kalshi?

Current recommendation:

- do **not** compare raw headline liquidity fields alone
- prefer:
  - best bid / best ask
  - top-of-book size
  - spread
  - 24h volume
- retest during **U.S. daylight hours**, because the overnight snapshot may not
  be representative

---

## Recommended Implementation Order

1. Add `seed_polymarket_platform`
2. Add optional Polymarket-specific nullable fields to `pm_markets`
3. Build `PolymarketClient`
4. Implement token/outcome normalization
5. Implement token-level `pm_markets` ingest
6. Populate `last_trade_time` from public trades
7. Add **targeted macro/Fed discovery**
8. Add **FOMC sanity-check workflow** against TSDB
9. Add trade-derived `pm_candlesticks`
10. Add live smoke tests
11. Update docs
12. Add optional Fed/macro linkage later

---

## Recommendation

Proceed with:

> **Phase 1 Polymarket = public read-only metadata + token-level market ingest + latest trade timestamps + optional snapshot enrichment, with trade-derived bars as the next step.**

This is the cleanest, lowest-risk extension of the current prediction-markets
architecture and is fully consistent with how Kalshi is already modeled in TSDB.
