#!/usr/bin/env python3
"""
Advanced: Direct client usage for custom data queries.

This example demonstrates:
- Direct LsegClient usage (without pipelines)
- Custom field selection
- Combining multiple data sources
- Historical snapshots

Usage:
    python examples/custom_queries.py
"""

from lseg_toolkit import LsegClient


def main():
    with LsegClient() as client:
        # Example 1: Get index constituents with market cap filter
        print("=" * 60)
        print("Example 1: Index Constituents")
        print("=" * 60)

        tickers = client.get_index_constituents(
            index="NDX",  # Nasdaq 100
            min_market_cap=100_000,  # $100B+ mega caps
        )
        print(f"Found {len(tickers)} mega-cap Nasdaq stocks")
        print(f"Tickers: {', '.join(tickers[:10])}...")

        # Example 2: Get company data
        print("\n" + "=" * 60)
        print("Example 2: Company Data")
        print("=" * 60)

        companies = client.get_company_data(tickers[:5])
        print(companies[["Ticker", "Company", "Sector", "Exchange"]].to_string())

        # Example 3: Get earnings dates
        print("\n" + "=" * 60)
        print("Example 3: Earnings Dates")
        print("=" * 60)

        earnings = client.get_earnings_data(
            tickers=tickers[:10],
            start_date="2025-01-01",
            end_date="2025-03-31",
            convert_timezone="US/Eastern",
        )
        if not earnings.empty:
            print(earnings[["Ticker", "Earnings Date", "Earnings Time"]].to_string())
        else:
            print("No earnings in date range")

        # Example 4: Get financial ratios
        print("\n" + "=" * 60)
        print("Example 4: Financial Ratios")
        print("=" * 60)

        ratios = client.get_financial_ratios(tickers[:5])
        cols = ["Ticker", "P/E LTM", "EV/EBITDA", "P/FCF"]
        available_cols = [c for c in cols if c in ratios.columns]
        print(ratios[available_cols].to_string())

        # Example 5: Historical snapshot
        print("\n" + "=" * 60)
        print("Example 5: Historical Snapshot (End of Q3 2024)")
        print("=" * 60)

        historical = client.get_financial_ratios(
            tickers=tickers[:5],
            as_of_date="2024-09-30",
        )
        print(historical[available_cols].to_string())

        # Example 6: Consensus estimates
        print("\n" + "=" * 60)
        print("Example 6: Consensus Estimates")
        print("=" * 60)

        consensus = client.get_consensus_estimates(tickers[:5])
        est_cols = ["Ticker", "EPS Est", "Revenue Est"]
        available_est = [c for c in est_cols if c in consensus.columns]
        if available_est:
            print(consensus[available_est].to_string())

        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)


if __name__ == "__main__":
    main()
