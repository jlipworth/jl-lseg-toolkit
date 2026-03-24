# Temporary Polymarket ↔ FOMC Link Notes

**Status:** temporary troubleshooting note
**Created:** 2026-03-22
**Last reviewed:** 2026-03-24
**Purpose:** keep a stable reference list of high-confidence Polymarket/FOMC links
while the integration and comparison workflow is still exploratory.

## Scope

These are **dry-run candidate links**, not yet persisted into
`pm_markets.fomc_meeting_id`.

Selection rule used:

- Polymarket series discovered through targeted search/tag/event discovery
- exact `close_time::date = fomc_meetings.meeting_date`
- Fed/FOMC/Powell/rates semantic filtering
- obvious non-rates false positives excluded

## Exact-match candidate links

| FOMC date | `fomc_meeting_id` | Polymarket series |
|---|---:|---|
| 2024-01-31 | 175 | `fed-interest-rates-january-2024` |
| 2024-09-18 | 180 | `fed-rate-cut-by` |
| 2024-09-18 | 180 | `powell-says-inflation-15-times-in-fomc-intro-statement` |
| 2024-09-18 | 180 | `powell-says-unemployment-5-times-in-fomc-intro-statement` |
| 2025-01-29 | 183 | `fed-interest-rates-january-2025` |
| 2025-06-18 | 186 | `fed-rate-cut-by-june-meeting` |
| 2025-06-18 | 186 | `what-will-powell-say-during-june-press-conference` |
| 2025-07-30 | 187 | `fed-decision-in-july` |
| 2025-07-30 | 187 | `what-will-powell-say-during-july-press-conference` |
| 2025-09-17 | 189 | `fed-decision-in-september` |
| 2025-09-17 | 189 | `what-will-powell-say-during-september-press-conference` |
| 2025-10-29 | 190 | `fed-decision-in-october` |
| 2025-12-10 | 191 | `fed-decision-in-december` |
| 2025-12-10 | 191 | `fed-rate-cut-by-467` |
| 2025-12-10 | 191 | `what-will-powell-say-during-december-press-conference` |
| 2026-01-28 | 192 | `fed-decision-dissent-combo-in-january` |
| 2026-01-28 | 192 | `fed-decision-in-january` |
| 2026-01-28 | 192 | `fed-rate-cut-by-359` |
| 2026-01-28 | 192 | `what-will-powell-say-during-january-press-conference-639` |
| 2026-03-18 | 1148 | `fed-decision-in-march-885` |
| 2026-03-18 | 1148 | `powell-bingo-march` |
| 2026-03-18 | 1148 | `what-will-powell-say-during-march-press-conference` |
| 2026-04-29 | 1149 | `fed-decision-in-april` |
| 2026-04-29 | 1149 | `fed-decisions-jan-apr` |
| 2026-04-29 | 1149 | `how-many-dissent-at-the-next-fed-meeting-113` |
| 2026-06-17 | 1150 | `fed-decision-in-june-825` |
| 2026-06-17 | 1150 | `fed-decisions-mar-jun` |
| 2026-06-17 | 1150 | `fed-rate-cut-by-629` |
| 2026-07-29 | 1151 | `fed-decision-in-july-181` |
| 2026-12-09 | 1154 | `fed-rate-hike-in-2026` |
| 2026-12-09 | 1154 | `what-will-the-fed-rate-be-at-the-end-of-2026` |

## Quick comparison snapshot (2026-03-22)

All percentages below are taken from the current TSDB snapshot and should be
treated as **market-implied prices**, not arbitrage-clean normalized
probabilities.

### April 29, 2026 FOMC

| Outcome | Polymarket | Kalshi |
|---|---:|---:|
| No change | 94.8% | 93.0% |
| 25 bp cut | 1.25% | 6.0% |
| \>25 bp cut | 0.55% | 2.0% |
| 25+ bp hike | 3.55% | 3.0% |

### June 17, 2026 FOMC

| Outcome | Polymarket | Kalshi |
|---|---:|---:|
| No change | 84.5% | 64.0% |
| 25 bp cut | 10.5% | 36.0% |
| \>25 bp cut | 0.9% | 6.0% |
| 25+ bp hike | 3.95% | 4.0% |

### July 29, 2026 FOMC

| Outcome | Polymarket | Kalshi |
|---|---:|---:|
| No change | 77.0% | 61.0% |
| 25 bp cut | 16.0% | 35.0% |
| \>25 bp cut | 2.2% | 5.0% |
| 25+ bp hike | 5.3% | 7.0% |

### 2026 cut-count snapshot

| Metric | Polymarket | Kalshi |
|---|---:|---:|
| 0 cuts | 36.1% | 25.0% |
| 1 cut | 27.5% | 27.0% |
| 2 cuts | 15.5% | 22.0% |
| 3+ cuts | 19.3% | 46.0% |

## Interpretation note

The directional read as of 2026-03-22 is:

- **April:** broadly aligned
- **June/July:** Kalshi is noticeably **more dovish** than Polymarket
- **cut-count:** Kalshi is also more dovish in the cumulative 2026 cut-count view

The `KXFED` year-end rate ladder should be treated cautiously during
troubleshooting because the stored threshold prices were not perfectly monotonic
in the snapshot used here.

## Liquidity snapshot (live Polymarket, 2026-03-22)

Polymarket exposes liquidity directly on Gamma event/market payloads via
`liquidity` / `liquidityClob`, and market rows also expose `bestBid`,
`bestAsk`, `spread`, and `lastTradePrice`.

### Event-level liquidity

| Event slug | Event liquidity | 24h volume | Markets |
|---|---:|---:|---:|
| `fed-decision-in-april` | 2,784,978 | 2,203,495 | 4 |
| `fed-decision-in-june-825` | 658,009 | 97,043 | 5 |
| `fed-decision-in-july-181` | 242,304 | 19,144 | 5 |
| `what-will-the-fed-rate-be-at-the-end-of-2026` | 263,591 | 47,670 | 15 |
| `how-many-fed-rate-cuts-in-2026` | 1,112,990 | 302,698 | 13 |

### Selected contract-level liquidity

| Contract | Liquidity | Best bid | Best ask | Spread |
|---|---:|---:|---:|---:|
| April 2026, 50+ bp cut | 1,208,719 | 0.005 | 0.006 | 0.001 |
| April 2026, 25 bp cut | 584,215 | 0.012 | 0.013 | 0.001 |
| End-2026 fed funds = 4.25% | 20,565 | 0.024 | 0.025 | 0.001 |
| End-2026 fed funds = 2.25% | 14,948 | 0.005 | 0.007 | 0.002 |

### Troubleshooting takeaway

So yes: **we can see liquidity**, and the shape looks intuitive:

- near/important Fed decision events have **hundreds of thousands to millions**
  of event-level liquidity
- farther-out discrete rate buckets are much thinner, often only **~15k–25k**
  per contract
- to judge tradability, the headline liquidity number is useful, but the
  better immediate check is **best bid / best ask / spread** at the token level
