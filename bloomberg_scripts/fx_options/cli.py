"""Legacy / research CLI for FX options extraction."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from .._legacy import legacy_surface_message
from .extract import DEFAULT_PAIRS, DEFAULT_TENORS, run_fx_options_extraction

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for FX options CLI."""
    parser = argparse.ArgumentParser(
        description="Extract FX options (risk reversals and butterflies) from Bloomberg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Default pairs: {', '.join(DEFAULT_PAIRS)}
Default tenors: {', '.join(DEFAULT_TENORS)}

Examples:
  # Extract all FX options for default pairs (snapshot)
  python -m bloomberg_scripts.fx_options

  # Extract specific pairs
  python -m bloomberg_scripts.fx_options --pairs EURUSD USDJPY

  # Extract with specific tenors
  python -m bloomberg_scripts.fx_options --pairs EURUSD --tenors 1M 3M 6M 1Y

  # Extract with historical data
  python -m bloomberg_scripts.fx_options --historical --start-date 2024-01-01

  # Export to CSV
  python -m bloomberg_scripts.fx_options --format csv
        """,
    )

    parser.add_argument(
        "--pairs",
        "-p",
        nargs="+",
        default=None,
        help=f"Currency pair(s) (default: {', '.join(DEFAULT_PAIRS)})",
    )

    parser.add_argument(
        "--tenors",
        "-t",
        nargs="+",
        default=None,
        help=f"Option tenor(s) (default: {', '.join(DEFAULT_TENORS)})",
    )

    parser.add_argument(
        "--deltas",
        "-d",
        nargs="+",
        default=None,
        help="Delta level(s) (default: 25, 10)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: data/bloomberg/fx_options)",
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
    """Main entry point for FX options CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    print(
        legacy_surface_message(
            "bloomberg_scripts.fx_options",
            replacement='bbg-extract fx-atm-vol',
            note='This CLI targets RR/BF research and may hit stale DataFrame/ticker assumptions.',
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
        output_paths = run_fx_options_extraction(
            pairs=args.pairs,
            output_dir=args.output_dir,
            historical=args.historical,
            start_date=args.start_date,
            end_date=args.end_date,
            tenors=args.tenors,
            deltas=args.deltas,
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
