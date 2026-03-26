"""Legacy / research CLI for caps/floors extraction."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from .._legacy import legacy_surface_message
from .extract import run_caps_floors_extraction

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for caps/floors CLI."""
    parser = argparse.ArgumentParser(
        description="Extract interest rate caps/floors data from Bloomberg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract USD SOFR caps (snapshot)
  python -m bloomberg_scripts.caps_floors --currency USD

  # Extract both caps and floors
  python -m bloomberg_scripts.caps_floors --currency USD --type both

  # Extract EUR ESTR caps with historical data
  python -m bloomberg_scripts.caps_floors --currency EUR --historical --start-date 2024-01-01

  # Export to CSV
  python -m bloomberg_scripts.caps_floors --currency GBP --format csv
        """,
    )

    parser.add_argument(
        "--currency",
        "-c",
        type=str,
        default="USD",
        help="Currency code (USD, EUR, GBP) or 'all' (default: USD)",
    )

    parser.add_argument(
        "--type",
        "-t",
        choices=["cap", "floor", "both"],
        default="cap",
        help="Instrument type (default: cap)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: data/bloomberg/caps_floors)",
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
    """Main entry point for caps/floors CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    print(
        legacy_surface_message(
            "bloomberg_scripts.caps_floors",
            replacement=None,
            note='This CLI is research-only because the Bloomberg caps/floors ticker format is still unresolved.',
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
        output_paths = run_caps_floors_extraction(
            currency=args.currency,
            output_dir=args.output_dir,
            historical=args.historical,
            start_date=args.start_date,
            end_date=args.end_date,
            instrument_type=args.type,
            output_format=args.format,
        )

        print(f"Successfully exported {len(output_paths)} file(s):")
        for path in output_paths:
            print(f"  {path}")

        return 0

    except Exception as e:
        logger.error("Extraction failed: %s", e)
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
