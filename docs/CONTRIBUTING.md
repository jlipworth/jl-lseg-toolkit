# Contributing

Thanks for contributing to `jl-lseg-toolkit`.

## Getting started

For local environment setup and LSEG connectivity, see
[GETTING_STARTED.md](GETTING_STARTED.md).

```bash
git clone <repository-url>
cd jl-lseg-toolkit
uv sync
make install-hooks
make ci-local
```

## Contribution workflow

1. Create a focused branch
2. Make the change
3. Update tests/docs/changelog as needed
4. Run `make ci-local`
5. Open a PR against `master`

## Branch naming

```bash
git checkout -b feature/your-feature
git checkout -b fix/your-bug
git checkout -b docs/your-doc-change
```

## Required validation before PR

```bash
make ci-local
uv run pre-commit run --all-files
```

If you are iterating quickly, targeted commands are fine, but PR readiness is
measured by `make ci-local`.

## What to update when behavior changes

- `README.md` for user-facing CLI/workflow changes
- `docs/TIMESERIES.md` for extraction/storage behavior
- `docs/SCHEDULER.md` for scheduler commands/groups/schema
- `docs/PREDICTION_MARKETS.md` / `docs/POLYMARKET_RESOLUTION.md` for PM logic
- `docs/LSEG_API_REFERENCE.md` / `docs/INSTRUMENTS.md` for mapping/support claims
- `docs/CHANGELOG.md` for notable changes

## Code style

- Ruff for lint + format
- mypy for type checking
- pre-commit for local hooks
- Google-style docstrings for public functions
- Prefer small, reviewable commits and PRs

## Testing guidance

Use:
- `make ci-local` for the exact CI mirror
- `uv run pytest tests/ -m "not integration" --no-cov` for quick unit loops
- `uv run pytest tests/ -m "integration"` for real LSEG-backed checks

## Documentation guidance

Please keep docs aligned with current behavior. In particular, avoid:
- stale CLI flags/examples
- outdated schema/table names
- private hostnames, internal paths, or maintainer-only secret-manager examples
- “plan” language in docs for features that have already merged

## CI image maintenance

The test jobs use the Python-only image in `ci/Dockerfile`; Renovate runs in a
separate image pinned in `.woodpecker/renovate.yml`. Renovate currently manages
Python dependencies only, so review and refresh its image manually. Before a
refresh, execute `node --version` in the selected immutable image on both
`linux/amd64` and `linux/arm64`, check the applicable Node security release,
and run `renovate-config-validator renovate.json`. Keep the version and index
digest together; the scheduled job prints its Node version before scanning.

On October 23, 2026, Renovate 44.181.0 was verified with Node 24.22.1 on both
architectures. The pinned toolkit test image reports Python 3.13.12 and has no
Node executable in PATH or under `/usr/local`, `/usr/bin`, or `/opt` on amd64.
The Node remediation therefore updates only the Renovate job.
