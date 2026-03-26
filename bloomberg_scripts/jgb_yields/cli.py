"""Legacy / research CLI for JGB yields extraction."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from .._legacy import legacy_surface_message
from .extract import JGB_TICKERS, run_jgb_extraction

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for JGB yields CLI."""
    parser = argparse.ArgumentParser(
        description="Extract JGB (Japanese Government Bond) yields from Bloomberg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available tenors: {', '.join(JGB_TICKERS.keys())}

Examples:
  # Extract all JGB yields (snapshot)
  python -m bloomberg_scripts.jgb_yields

  # Extract specific tenors
  python -m bloomberg_scripts.jgb_yields --tenors 2Y 5Y 10Y

  # Extract with historical data
  python -m bloomberg_scripts.jgb_yields --historical --start-date 2020-01-01

  # Include benchmark tickers
  python -m bloomberg_scripts.jgb_yields --include-benchmarks

  # Export to CSV
  python -m bloomberg_scripts.jgb_yields --format csv
        """,
    )

    parser.add_argument(
        "--tenors",
        "-t",
        nargs="+",
        default=None,
        help=f"Tenor(s) to extract (default: all). Options: {', '.join(JGB_TICKERS.keys())}",
    )

    parser.add_argument(
        "--include-benchmarks",
        "-b",
        action="store_true",
        help="Include benchmark tickers (10Y benchmark, super-long)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: data/bloomberg/jgb)",
    )

    parser.add_argument(
        "--historical",
        action="store_true",
        help="Extract historical data instead of snapshot",
    )

    parser.add_argument(
        "--start-date",
        type=parse_date,
        default=None,
        help="Start date for historical data (YYYY-MM-DD)",
    )

    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=None,
        help="End date for historical data (YYYY-MM-DD, default: today)",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["parquet", "csv"],
        default="parquet",
        help="Output format (default: parquet)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for JGB yields CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    print(
        legacy_surface_message(
            "bloomberg_scripts.jgb_yields",
            replacement='bbg-extract jgb',
            note='This older modular CLI is superseded by the supported Bloomberg package path.',
        ),
        file=sys.stderr,
    )

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Validate arguments
    if args.historical and args.start_date is None:
        parser.error("--start-date is required when using --historical")

    try:
        output_paths = run_jgb_extraction(
            output_dir=args.output_dir,
            historical=args.historical,
            start_date=args.start_date,
            end_date=args.end_date,
            tenors=args.tenors,
            include_benchmarks=args.include_benchmarks,
            output_format=args.format,
        )

        if output_paths:
            print(f"Successfully exported {len(output_paths)} file(s):")
            for path in output_paths:
                print(f"  {path}")
        else:
            print("No data exported")

        return 0

    except Exception as e:
        logger.error("Extraction failed: %s", e)
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
