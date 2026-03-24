# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added
- Timeseries extraction/storage groundwork for futures, FX, OIS, FRAs, sovereign yields, and STIR products
- Scheduler CLI + daemon support for recurring extraction jobs
- Fed Funds continuous extraction, roll-handling helpers, and smoke-test coverage
- FOMC meeting / rate-decision sync and storage support
- Prediction-markets subsystem for Kalshi, Polymarket, and FedWatch comparison workflows
- Bond-basis helpers and additional timeseries storage utilities
- `make ci-local` and `make install-hooks` for reliable local contributor workflow

### Changed
- Documentation now reflects timeseries, scheduler, FOMC, and prediction-markets as first-class repo surfaces
- CI-aligned contributor guidance now centers on `make ci-local`
- Repo examples/docs now avoid stale flags and outdated schema/table names

### Fixed
- Removed stale CLI/documentation references such as nonexistent `--db` / `--ric` examples
- Archived implementation-plan / roadmap docs that had become historical rather than active guidance
- Reconciled bond-futures mapping docs with current code in `timeseries/constants.py`

## [0.1.0] - 2025-10-29

### Completed Features

#### Earnings Report Generator
- Screen index constituents by upcoming earnings dates
- 13 global indices supported
- Market-cap filtering
- Timezone conversion for earnings times
- Excel export with detailed formatting
- Snapshot-date system for point-in-time consistency

#### Equity Screener
- Equity screening with valuation and return metrics
- Historical snapshot support
- Excel export with sector breakdown

#### Infrastructure
- Modular LSEG client
- Shared processing / Excel export utilities
- WSL2 and local connectivity documentation
