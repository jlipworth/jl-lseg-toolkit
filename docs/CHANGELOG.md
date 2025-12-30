# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Enhanced Return Metrics** (November 2, 2025):
  - Added 1-month, 3-month, and 6-month total return columns to both earnings report and equity screener
  - Fields: `TR.TotalReturn1Mo`, `TR.TotalReturn3Mo`, `TR.TotalReturn6Mo`
  - Provides more granular performance tracking alongside existing YTD, 1Y, 2Y, 3Y, 5Y returns
- **Modular Client Architecture** (October 29, 2025):
  - Split monolithic `client.py` (857 lines) into focused submodules
  - `client/session.py` - Session management (73 lines)
  - `client/constituents.py` - Index constituents (168 lines)
  - `client/company.py` - Company data (70 lines)
  - `client/earnings.py` - Earnings data (234 lines)
  - `client/financial.py` - Financial ratios (207 lines)
  - `client/consensus.py` - Consensus estimates (170 lines)
  - `client/__init__.py` - LsegClient wrapper for backwards compatibility (135 lines)
  - **Result**: 100% backwards compatible, all 71 tests passing
- `tests/conftest.py` - Shared pytest fixtures for all tests
  - Session/class/function scoped client fixtures
  - Sample data fixtures (tickers, dates, indices)
  - Custom pytest markers (@integration, @slow, @unit)
- `dev_scripts/README.md` - Documentation for development scripts organization
- `dev_scripts/active/` - Directory for current API investigations
- `dev_scripts/archive/2025-10/` - Archive for completed investigation scripts (52 scripts)

### Changed
- **WSL2 Networking Migration** (November 8, 2025):
  - **Migrated from legacy tunnel to WSL mirrored networking mode**
  - Removed `tunnel.py` and `lseg_tunnel.py` (archived in `dev_scripts/archive/old_wsl_tunnel/`)
  - Removed `lseg-tunnel` CLI command
  - Removed tunnel auto-start logic from `client/session.py`
  - Updated `WSL_SETUP.md` with mirrored networking instructions
  - Updated `CLAUDE.md` and `README.org` to reflect mirrored networking assumption
  - **Requirement**: WSL 2.0.0+ with mirrored networking mode (default on Windows 11 22H2+)
  - **Benefit**: Simpler setup - no port forwarding or tunnel scripts needed
- **Snapshot Date System**: ALL data now fetched as of a single snapshot date for consistency
  - `get_company_data()` - Added `as_of_date` parameter for historical prices/market caps
  - `get_since_last_earnings_return()` - Added `as_of_date` parameter, solves "0.00% return" issue
  - `get_financial_ratios()` - Added numeric type conversions for historical snapshot data
  - `earnings/pipeline.py` - Now passes `consensus_date` to all data fetching methods
- **Documentation Updates**:
  - `CLAUDE.md` - Expanded Project Structure with detailed module descriptions and line counts
  - `CLAUDE.md` - Added "Recent Fixes" section documenting October 2025 changes
  - `README.org` - Updated Snapshot Date System section with code examples and benefits
- **Test Improvements**:
  - Fixed equity_screener config tests (updated to use `country` instead of `headquarters`)
  - Fixed client initialization test (removed outdated `api_key` parameter)
  - Fixed data merge test (proper handling of duplicate column names with suffixes)
  - **Result**: 71 passing tests (was 65 passing, 6 failing) - 100% pass rate

### Fixed
- **YTD Return Bug in Equity Screener** (November 2, 2025):
  - **Problem**: Equity screener was using `TR.TotalReturn1Yr` instead of `TR.TotalReturnYTD`
  - **Solution**: Corrected to use `TR.TotalReturnYTD` for accurate year-to-date returns
  - **Impact**: YTD returns in equity screener now show correct values
- **N/A Return Handling** (November 2, 2025):
  - **Problem**: Missing return data displayed as "0.00%" which was misleading
  - **Solution**: Consistent "N/A" text display for missing/unavailable return data
  - **Impact**: Clearer indication when return data is not available (e.g., IPO < 1 year ago)
- **"0.00% Since Last Earnings" Issue**:
  - **Problem**: When earnings = today, LSEG returns same price for both current and historical queries
  - **Solution**: Use snapshot date (Sunday before week) for ALL data fetching
  - **Impact**: Earnings reports now show meaningful returns even when generated on earnings day
- Historical snapshot queries returning string values instead of numeric
  - Added `pd.to_numeric()` conversions in `get_financial_ratios()` for all numeric columns

## [0.1.0] - 2025-10-29

### Completed Features

#### Earnings Report Generator ✅
- Screen index constituents by upcoming earnings dates
- 13 global indices supported (SPX, NDX, DJI, STOXX, FTSE, etc.)
- Market cap filtering
- Timezone conversion for earnings times (GMT → local)
- Comprehensive data: consensus estimates, valuation ratios, returns (YTD-5Y + Since Last Earnings)
- Excel export with collapsible detail rows and frozen panes
- Snapshot date system for point-in-time data consistency

#### Equity Screener ✅
- Screen US equities by market cap and financial criteria
- 13 global indices or country-based screening
- 16 financial metrics (P/E, EV/EBITDA, P/FCF, P/B, leverage, returns, activism)
- Flexible filtering: index + country + market cap (all optional)
- Excel export with sector breakdown
- Date-aware screening (historical snapshots)

#### Infrastructure ✅
- LSEG client with session management
- Index constituent retrieval (13 verified indices)
- Data processing utilities
- Excel export framework (Book Antiqua formatting)
- WSL2 port tunneling utilities
- Timezone conversion utilities
- 71 passing tests with 100% pass rate
- Comprehensive documentation

### Known Limitations
- Russell indices (1000, 2000, 3000) not available via LSEG API
- Historical snapshots may have slower performance for large datasets
- LSEG API returns some fields as strings for historical dates (handled via type conversion)
