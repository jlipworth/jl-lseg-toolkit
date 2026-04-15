# Backlog Dashboard

This file is a thin dashboard. Active backlog items live as GitHub issues — the source of truth for priority, status, and triage.

**Browse all open backlog:** [`is:open label:backlog`](https://github.com/jlipworth/jl-lseg-toolkit/issues?q=is%3Aopen+label%3Abacklog)

## Current workstreams

| Workstream | Issue | Status |
|------------|-------|--------|
| Prediction Markets / Polymarket follow-ups | [#6](https://github.com/jlipworth/jl-lseg-toolkit/issues/6) | Partial — core ingest landed, follow-ups open |
| CDS intraday investigation | [#7](https://github.com/jlipworth/jl-lseg-toolkit/issues/7) | Daily works, intraday unavailable |
| Options research (chain discovery, Greeks) | [#8](https://github.com/jlipworth/jl-lseg-toolkit/issues/8) | Not started |
| Tech debt — field mapping + bulk insert helper | [#9](https://github.com/jlipworth/jl-lseg-toolkit/issues/9) | Not started |

## How to use this dashboard

- Add a new workstream: open a GitHub issue with the `backlog` label, then add a row above.
- Close a workstream: close the issue; the row can stay until the workstream fully ships, then drop it.
- Keep the table short — one row per workstream, not per task. Sub-tasks belong in the issue body.

Detailed context for any workstream lives in its issue, not here.
