# Bloomberg Implementation — Summary

> This file used to be a 756-line implementation plan. It has been compressed
> to a short summary of key decisions. The open validation work lives in
> [issue #11](https://github.com/jlipworth/jl-lseg-toolkit/issues/11). Full
> history is in git (`git log -- docs/plans/BLOOMBERG_IMPLEMENTATION.md`).

## Current status

Partial / unvalidated. The maintainer does not have ongoing Bloomberg Terminal
access; see [`docs/instruments/BLOOMBERG.md`](../instruments/BLOOMBERG.md) for
the support matrix banner and [`docs/BLOOMBERG_LIVE_VALIDATION_RUNBOOK.md`](../BLOOMBERG_LIVE_VALIDATION_RUNBOOK.md)
for the validation runbook.

## Key architectural decisions (preserved from the original plan)

1. **Standalone Bloomberg subsystem.** `src/lseg_toolkit/bloomberg/` is a
   standalone package, not folded into `src/lseg_toolkit/timeseries/`. Keeps
   LSEG and Bloomberg failure modes isolated and lets the Bloomberg surface
   ship as partial without destabilizing the LSEG pipeline.

2. **`bbg-extract` as the only supported CLI.** Research/probe scripts under
   `bloomberg_scripts/` are explicitly out-of-scope for the supported surface
   and stay there for future Terminal-assisted discovery.

3. **Only validated features are user-facing.** Today that is JGB yields and
   FX ATM implied vol. Everything else (swaptions, caps/floors, FX RR/BF,
   treasury basis) stays in `bloomberg_scripts/` until a Terminal-assisted
   validation pass confirms ticker and field patterns.

4. **Integration with storage is deferred.** Bloomberg outputs CSV/Parquet
   today. Integration with the TimescaleDB storage layer happens only after
   live validation broadens the supported surface; not worth the refactor
   cost with two validated workflows.

## Pointers

- Current support matrix → [`docs/instruments/BLOOMBERG.md`](../instruments/BLOOMBERG.md)
- Probe findings log → [`docs/BLOOMBERG_FINDINGS.md`](../BLOOMBERG_FINDINGS.md)
- Validation runbook → [`docs/BLOOMBERG_LIVE_VALIDATION_RUNBOOK.md`](../BLOOMBERG_LIVE_VALIDATION_RUNBOOK.md)
- Research scripts → [`docs/BLOOMBERG_SCRIPTS.md`](../BLOOMBERG_SCRIPTS.md)
- Open validation work → [issue #11](https://github.com/jlipworth/jl-lseg-toolkit/issues/11)
