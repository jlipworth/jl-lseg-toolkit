"""Legacy / research CLI for swaption extraction."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from .._legacy import legacy_surface_message
from .extract import run_swaption_extraction

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for swaption CLI."""
    parser = argparse.ArgumentParser(
        description="Extract swaption volatility surfaces from Bloomberg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract USD swaption surface (snapshot)
  python -m bloomberg_scripts.swaptions --currency USD

  # Extract all currency surfaces
  python -m bloomberg_scripts.swaptions --currency all

  # Extract with historical data
  python -m bloomberg_scripts.swaptions --currency USD --historical --start-date 2024-01-01

  # Export to CSV
  python -m bloomberg_scripts.swaptions --currency EUR --format csv
        """,
    )

    parser.add_argument(
        "--currency",
        "-c",
        type=str,
        default="USD",
        help="Currency code (USD, EUR, GBP, JPY, CHF, AUD) or 'all' (default: USD)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: data/bloomberg/swaptions)",
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
    """Main entry point for swaption CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    print(
        legacy_surface_message(
            "bloomberg_scripts.swaptions",
            replacement=None,
            note='This CLI is research-only because Bloomberg Desktop API swaption ticker access is still unconfirmed.',
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
        output_paths = run_swaption_extraction(
            currency=args.currency,
            output_dir=args.output_dir,
            historical=args.historical,
            start_date=args.start_date,
            end_date=args.end_date,
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
