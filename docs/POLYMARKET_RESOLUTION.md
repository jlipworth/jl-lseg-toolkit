# Polymarket Resolution Spec

Working spec for normalizing Polymarket data and resolving a small set of
high-value market families for macro/Fed workflows.

## Purpose

This document defines:

- which Polymarket endpoint family we trust for each data concern
- how raw Polymarket objects map into our prediction-market schema
- which market families we resolve programmatically
- which cases we intentionally leave unresolved
- when a Polymarket contract may be linked to a specific `fomc_meetings` row

This is intentionally a **resolver spec**, not a universal classifier spec.

The design goal is:

- keep ingestion generic
- keep programmatic resolution conservative
- prefer manual review for ambiguous contracts

## Relationship to Other Docs

This document is the canonical reference for:

- endpoint-role semantics
- structural normalization
- family-resolution vocabulary
- FOMC linkage policy

Related docs:

- `docs/PREDICTION_MARKETS.md`
  - top-level workflow and troubleshooting entry point
- `docs/plans/POLYMARKET_IMPLEMENTATION.md`
  - implementation history and next tasks
- `docs/TEMP_POLYMARKET_FOMC_LINKS.md`
  - dry-run exploratory note, not production linkage policy

---

## Endpoint Roles

### Gamma API

Base URL:

```text
https://gamma-api.polymarket.com
```

Use for:

- discovery
- search
- tags
- event metadata
- market metadata
- grouping
- condition ids and token ids

Gamma is the **structural source of truth**.

### Data API

Base URL:

```text
https://data-api.polymarket.com
```

Use for:

- recent/historical trades
- latest trade timestamps
- later: trade-derived bars

Data API is the **executed-activity source of truth**.

### CLOB API

Base URL:

```text
https://clob.polymarket.com
```

Use for:

- best bid / ask
- midpoint
- spread
- orderbook state
- token-level tradability

CLOB is the **liquidity/orderbook source of truth**.

### Convenience enrichment

The current implementation also uses:

- `/simplified-markets`

Treat that as helpful enrichment, not the canonical semantic model.

---

## Structural Normalization

### Core principle

Use:

> **one Polymarket outcome token = one `pm_markets` row**

### Concept mapping

| Polymarket concept | Internal table |
|---|---|
| platform | `pm_platforms` |
| event | `pm_series` |
| outcome token | `pm_markets` |
| trade-derived token bar | `pm_candlesticks` |

### Event to `pm_series`

Use the event as the series bucket.

| Internal field | Source |
|---|---|
| `series_ticker` | `event.slug` |
| `title` | `event.title` |
| `category` | `"prediction_markets"` for now |

### Outcome token to `pm_markets`

Each token/outcome becomes a separate row.

| Internal field | Source |
|---|---|
| `market_ticker` | `POLY:{condition_id}:{token_id}` |
| `platform_market_id` | `token_id` |
| `event_ticker` | `condition_id` |
| `condition_id` | market `conditionId` |
| `token_id` | token id from `clobTokenIds` |
| `outcome_label` | outcome label from `outcomes` |
| `event_slug` | parent event slug |
| `question_slug` | market/question slug |
| `title` | market question/title |
| `subtitle` | outcome label |
| `open_time` | event/market start time |
| `close_time` | event/market end time |
| `status` | normalized active/closed/settled |
| `last_price` | current token snapshot price |
| `last_trade_time` | latest trade timestamp from Data API |

### Canonical identity fields

- `event_slug`
- `question_slug`
- `condition_id`
- `token_id`
- `market_ticker = POLY:{condition_id}:{token_id}`

Interpretation:

- `event_slug` identifies the event bucket
- `condition_id` identifies the question/condition
- `token_id` identifies the tradable outcome token

---

## Status, Price, and Freshness Semantics

### Status

Normalize to:

- `active`
- `closed`
- `settled`

Current precedence:

1. resolved/UMA-resolved -> `settled`
2. `active = true` -> `active`
3. `closed = true` or `archived = true` -> `closed`
4. otherwise default to `active`

### `last_price`

Treat `last_price` as the **best available token snapshot price**, not
necessarily the price of the latest executed trade.

Preferred source order:

1. explicit token-level CLOB snapshot price, if fetched
2. Gamma `outcomePrices`
3. simplified CLOB convenience payload, if needed

### `last_trade_time`

Use Data API trades for:

- freshness checks
- recent activity checks
- later bar reconstruction

`last_trade_time` is the main active-market freshness signal.

---

## Discovery vs Resolution

These are separate steps.

### Discovery

Discovery should stay broad and high-recall:

1. seed with Gamma `/public-search`
2. expand via Gamma `/tags`
3. fetch Gamma `/events?tag_id=...&related_tags=true`
4. flatten nested event markets
5. normalize token rows

Discovery asks:

> should we inspect this?

### Resolution

Resolution should stay narrow and conservative.

Resolution asks:

> is this in one of the small families we trust enough to label automatically?

Everything else may stay unresolved.

That is acceptable and expected.

---

## Resolved Families

Programmatic resolution should only target a small allowlist.

### `fomc_decision`

Use when the event/market is clearly about the Fed decision at a specific
meeting.

Typical cues:

- `fed-decision-in-*`
- `fed decision in ...`
- `fed-interest-rates-*`
- `fed interest rates ...`

Expected usage:

- FOMC-link candidate
- often comparable to Kalshi meeting-decision products

### `powell_press_conference`

Use when the event/market is clearly about Powell wording or press-conference
behavior around a meeting.

Typical cues:

- `powell`
- plus `press conference`, `intro statement`, `say during`, or similar

Expected usage:

- possible FOMC-link candidate
- usually context, not direct FedWatch parity

### `cut_count`

Use only for clear cumulative cut-count wording.

Typical cues:

- `how many fed rate cuts`
- `how-many-fed-rate-cuts-*`

Expected usage:

- not a direct single-meeting link
- qualitatively comparable to cut-count products

### `year_end_rate`

Use only for clear year-end rate framing.

Typical cues:

- `what will the fed rate be at the end of ...`
- `what-will-the-fed-rate-be-at-the-end-of-*`

Expected usage:

- not tied to one meeting
- context/horizon view, not direct one-meeting parity

---

## Unresolved and Excluded Cases

### `unresolved_macro`

Use when a market is clearly macro/Fed related but does not fit one of the
allowlisted resolved families.

Examples:

- CPI/inflation markets
- jobs/unemployment markets
- unusual Fed/rates markets with unclear framing
- macro contracts we may still want to inspect manually

### `exclude`

Use when a discovered row should be dropped from macro/Fed workflows.

Examples:

- legal/political `federal` false positives
- obviously unrelated contracts

---

## FOMC Linkage Rules

`fomc_meeting_id` should be written only for high-confidence cases.

### First-pass rule

Allow auto-link candidates only when all are true:

1. resolved family is `fomc_decision` or `powell_press_conference`
2. the event is clearly meeting-oriented
3. `close_time::date = fomc_meetings.meeting_date`

### Explicit non-link cases

Do not auto-link:

- `cut_count`
- `year_end_rate`
- `unresolved_macro`
- `exclude`

---

## Worked Resolution Examples

### Example 1: FOMC decision event

Raw shape:

- event slug: `fed-decision-in-april`
- event title: `Fed decision in April?`
- market `conditionId`: `cond-abc`
- outcomes: `["25+ bps hike", "No change", "25 bps cut", "50+ bps cut"]`

Normalized interpretation:

- `pm_series.series_ticker = "fed-decision-in-april"`
- each outcome token becomes its own `pm_markets` row
- resolved family: `fomc_decision`

### Example 2: Powell wording market

Raw shape:

- event slug: `what-will-powell-say-during-march-press-conference`

Interpretation:

- each token still becomes its own `pm_markets` row
- resolved family: `powell_press_conference`
- may be meeting-linked if date-aligned
- should usually be treated as context, not direct policy-distribution parity

### Example 3: Year-end rate market

Raw shape:

- event slug: `what-will-the-fed-rate-be-at-the-end-of-2026`

Interpretation:

- one event series
- one row per rate-bucket token
- resolved family: `year_end_rate`
- do not auto-populate `fomc_meeting_id`

### Example 4: False positive

Raw shape:

- title: `Will Trump face a federal charge?`

Interpretation:

- resolved family: `exclude`
- not a macro/Fed workflow input

---

## Implementation Guidance

The resolver should be:

- deterministic
- explicit
- allowlist-first
- easy to inspect

It should **not** try to classify the entire Polymarket universe.

If a market is ambiguous, return `unresolved_macro` or `exclude` and leave the
rest to manual review.

---

## Minimum Regression Set

Any resolver implementation should include tests for at least these cases:

- `fed-decision-in-april` -> `fomc_decision`
- `what-will-powell-say-during-march-press-conference` ->
  `powell_press_conference`
- `how-many-fed-rate-cuts-in-2026` -> `cut_count`
- `what-will-the-fed-rate-be-at-the-end-of-2026` -> `year_end_rate`
- representative CPI market -> `unresolved_macro`
- `will-trump-face-a-federal-charge` -> `exclude`

## Current Operational Recommendation

Until this is more mature:

- keep discovery broad
- use dry-run summary/reporting helpers for review guidance
- keep resolution narrow
- keep `fomc_meeting_id` writes conservative
- prefer manual review for ambiguous cases
- treat `docs/TEMP_POLYMARKET_FOMC_LINKS.md` as a dry-run troubleshooting note,
  not a production linkage table
