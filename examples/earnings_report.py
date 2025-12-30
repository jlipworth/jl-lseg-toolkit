#!/usr/bin/env python3
"""
Generate an earnings report for Nasdaq 100.

This example demonstrates:
- Using the earnings pipeline programmatically
- Configuring report parameters
- Exporting to Excel

Usage:
    python examples/earnings_report.py

Output:
    exports/earnings_example_YYYYMMDD_HHMMSS.xlsx
"""

from datetime import datetime
from pathlib import Path

from lseg_toolkit import LsegClient
from lseg_toolkit.earnings.config import EarningsConfig
from lseg_toolkit.earnings.pipeline import EarningsReportPipeline
from lseg_toolkit.excel import ExcelExporter


def main():
    # Configure the report
    config = EarningsConfig(
        index="NDX",  # Nasdaq 100
        timeframe="week",  # Current week
        min_market_cap=10_000,  # $10B minimum
        timezone="US/Eastern",  # Convert times to Eastern
    )

    print(f"Generating earnings report for {config.index}...")
    print(f"Timeframe: {config.timeframe}")
    print(f"Min market cap: ${config.min_market_cap:,}M")

    # Run the pipeline
    with LsegClient() as client:
        pipeline = EarningsReportPipeline(client, config)
        df = pipeline.run()

    if df.empty:
        print("No earnings found for the specified criteria.")
        return

    print(f"\nFound {len(df)} companies with earnings this {config.timeframe}")

    # Export to Excel
    output_dir = Path("exports")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"earnings_example_{timestamp}.xlsx"

    exporter = ExcelExporter()
    exporter.export_earnings_report(df, output_path)

    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
