"""Legacy / research Bloomberg CLI.

Usage:
    python -m bloomberg_scripts swaptions --currency USD
    python -m bloomberg_scripts caps --currency USD
    python -m bloomberg_scripts jgb --historical --start-date 2020-01-01
    python -m bloomberg_scripts fx-options --pairs EURUSD USDJPY

Note:
    This CLI is retained for exploratory Bloomberg work.
    The supported Bloomberg CLI surface is migrating to ``bbg-extract``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a subparser."""
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: data/bloomberg/<instrument>)",
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


def cmd_swaptions(args: argparse.Namespace) -> int:
    """Handle swaptions subcommand."""
    from .swaptions.extract import run_swaption_extraction

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


def cmd_caps(args: argparse.Namespace) -> int:
    """Handle caps subcommand."""
    from .caps_floors.extract import run_caps_floors_extraction

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


def cmd_jgb(args: argparse.Namespace) -> int:
    """Handle jgb subcommand."""
    from .jgb_yields.extract import run_jgb_extraction

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


def cmd_fx_options(args: argparse.Namespace) -> int:
    """Handle fx-options subcommand."""
    from .fx_options.extract import run_fx_options_extraction

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


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="bloomberg_scripts",
        description="Bloomberg extraction scripts for interest rate options and related data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract USD swaption volatility surface
  python -m bloomberg_scripts swaptions --currency USD

  # Extract all swaption surfaces with history
  python -m bloomberg_scripts swaptions --currency all --historical --start-date 2024-01-01

  # Extract USD SOFR caps
  python -m bloomberg_scripts caps --currency USD

  # Extract JGB yields
  python -m bloomberg_scripts jgb --historical --start-date 2020-01-01

  # Extract FX risk reversals and butterflies
  python -m bloomberg_scripts fx-options --pairs EURUSD USDJPY GBPUSD

Note: Bloomberg Terminal must be running for data extraction.
        """,
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
        help="Available extraction commands",
    )

    # Swaptions subcommand
    swaptions_parser = subparsers.add_parser(
        "swaptions",
        help="Extract swaption volatility surfaces",
        description="Extract swaption volatility surfaces from Bloomberg",
    )
    swaptions_parser.add_argument(
        "--currency",
        "-c",
        type=str,
        default="USD",
        help="Currency code (USD, EUR, GBP, JPY, CHF, AUD) or 'all' (default: USD)",
    )
    add_common_args(swaptions_parser)
    swaptions_parser.set_defaults(func=cmd_swaptions)

    # Caps/floors subcommand
    caps_parser = subparsers.add_parser(
        "caps",
        help="Extract interest rate caps/floors",
        description="Extract interest rate caps and floors data from Bloomberg",
    )
    caps_parser.add_argument(
        "--currency",
        "-c",
        type=str,
        default="USD",
        help="Currency code (USD, EUR, GBP) or 'all' (default: USD)",
    )
    caps_parser.add_argument(
        "--type",
        "-t",
        choices=["cap", "floor", "both"],
        default="cap",
        help="Instrument type (default: cap)",
    )
    add_common_args(caps_parser)
    caps_parser.set_defaults(func=cmd_caps)

    # JGB yields subcommand
    jgb_parser = subparsers.add_parser(
        "jgb",
        help="Extract JGB yields",
        description="Extract Japanese Government Bond yields from Bloomberg",
    )
    jgb_parser.add_argument(
        "--tenors",
        "-t",
        nargs="+",
        default=None,
        help="Tenor(s) to extract (2Y, 5Y, 10Y, 20Y, 30Y, 40Y)",
    )
    jgb_parser.add_argument(
        "--include-benchmarks",
        "-b",
        action="store_true",
        help="Include benchmark tickers",
    )
    add_common_args(jgb_parser)
    jgb_parser.set_defaults(func=cmd_jgb)

    # FX options subcommand
    fx_parser = subparsers.add_parser(
        "fx-options",
        help="Extract FX risk reversals and butterflies",
        description="Extract FX options (risk reversals and butterflies) from Bloomberg",
    )
    fx_parser.add_argument(
        "--pairs",
        "-p",
        nargs="+",
        default=None,
        help="Currency pair(s) (default: EURUSD, USDJPY, GBPUSD, USDCHF, AUDUSD)",
    )
    fx_parser.add_argument(
        "--tenors",
        "-t",
        nargs="+",
        default=None,
        help="Option tenor(s) (default: 1W, 1M, 2M, 3M, 6M, 9M, 1Y, 2Y)",
    )
    fx_parser.add_argument(
        "--deltas",
        "-d",
        nargs="+",
        default=None,
        help="Delta level(s) (default: 25, 10)",
    )
    add_common_args(fx_parser)
    fx_parser.set_defaults(func=cmd_fx_options)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the unified CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    print(
        "Warning: `bloomberg_scripts` is a legacy/research Bloomberg surface. "
        "Use `bbg-extract` for supported Bloomberg workflows.",
        file=sys.stderr,
    )

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Validate common arguments
    if args.historical and args.start_date is None:
        parser.error("--start-date is required when using --historical")

    try:
        return args.func(args)
    except Exception as e:
        logger.error("Extraction failed: %s", e)
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
