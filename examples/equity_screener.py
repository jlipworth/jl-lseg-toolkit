#!/usr/bin/env python3
"""
Screen US large-cap stocks with financial metrics.

This example demonstrates:
- Using the equity screener pipeline programmatically
- Filtering by market cap
- Getting historical snapshot data
- Exporting with sector-based sheets

Usage:
    python examples/equity_screener.py

Output:
    exports/screener_example_YYYYMMDD_HHMMSS.xlsx
"""

from datetime import datetime
from pathlib import Path

from lseg_toolkit import LsegClient
from lseg_toolkit.equity_screener.config import EquityScreenerConfig
from lseg_toolkit.equity_screener.pipeline import EquityScreenerPipeline
from lseg_toolkit.excel import ExcelExporter


def main():
    # Configure the screener
    config = EquityScreenerConfig(
        index="SPX",  # S&P 500
        min_market_cap=50_000,  # $50B+ large caps
        country="US",  # US stocks only
        # snapshot_date="2024-12-31",  # Uncomment for historical data
    )

    print(f"Running equity screener for {config.index}...")
    print(f"Min market cap: ${config.min_market_cap:,}M")

    # Run the pipeline
    with LsegClient() as client:
        pipeline = EquityScreenerPipeline(client, config)
        df = pipeline.run()

    if df.empty:
        print("No stocks found for the specified criteria.")
        return

    print(f"\nFound {len(df)} companies")
    print(f"Sectors: {df['Sector'].nunique()}")

    # Show top 5 by market cap
    print("\nTop 5 by Market Cap:")
    top5 = df.nlargest(5, "Market Cap")
    for _, row in top5.iterrows():
        print(
            f"  {row['Ticker']:6} {row['Company'][:30]:30} ${row['Market Cap']:,.0f}M"
        )

    # Export to Excel
    output_dir = Path("exports")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"screener_example_{timestamp}.xlsx"

    exporter = ExcelExporter()
    exporter.export_screener_report(df, output_path)

    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
