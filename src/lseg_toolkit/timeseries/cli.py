"""
Command-line interface for time series extraction.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta

from lseg_toolkit.exceptions import LsegError
from lseg_toolkit.timeseries.config import TimeSeriesConfig
from lseg_toolkit.timeseries.constants import (
    DEFAULT_DB_PATH,
    DEFAULT_PARQUET_DIR,
    USD_OIS_TENORS,
    UST_YIELD_TENORS,
)
from lseg_toolkit.timeseries.enums import (
    AssetClass,
    ContinuousType,
    Granularity,
    RollMethod,
)
from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {date_str}. Use YYYY-MM-DD"
        )


def list_instruments():
    """Display list of supported instruments."""
    print("=" * 80)
    print("SUPPORTED INSTRUMENTS")
    print("=" * 80)
    print()

    print("BOND FUTURES (use CME symbols):")
    print("-" * 40)
    print("  ZT    2-Year T-Note")
    print("  ZF    5-Year T-Note")
    print("  ZN    10-Year T-Note")
    print("  ZB    30-Year T-Bond")
    print("  UB    Ultra 30-Year T-Bond")
    print("  FGBL  Euro-Bund 10Y")
    print("  FGBM  Euro-Bobl 5Y")
    print()

    print("FX SPOT (use pair symbols):")
    print("-" * 40)
    print("  EURUSD, GBPUSD, USDJPY, USDCHF")
    print("  AUDUSD, USDCAD, NZDUSD")
    print("  EURGBP, EURJPY, GBPJPY")
    print()

    print("OIS CURVE (use tenor symbols):")
    print("-" * 40)
    print(f"  Tenors: {', '.join(USD_OIS_TENORS)}")
    print()

    print("TREASURY YIELDS (use tenor symbols):")
    print("-" * 40)
    print(f"  Tenors: {', '.join(UST_YIELD_TENORS)}")
    print()

    print("Examples:")
    print("  lseg-extract ZN ZB --start 2024-01-01")
    print("  lseg-extract EURUSD USDJPY --asset-class fx")
    print("  lseg-extract 1M 3M 1Y 5Y 10Y --asset-class ois")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract time series data from LSEG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract bond futures (last year, daily)
  lseg-extract ZN ZB

  # Extract with specific date range
  lseg-extract ZN --start 2023-01-01 --end 2024-12-31

  # Build continuous contracts with ratio adjustment
  lseg-extract ZN --continuous --adjust ratio

  # Extract FX data
  lseg-extract EURUSD USDJPY --asset-class fx

  # Extract OIS curve
  lseg-extract 1M 3M 6M 1Y 5Y 10Y --asset-class ois

  # Extract Treasury yields
  lseg-extract 2Y 5Y 10Y 30Y --asset-class govt-yield

  # Intraday data (recent dates only)
  lseg-extract ZN --start 2025-01-01 --end 2025-01-05 --interval hourly

  # Custom output paths
  lseg-extract ZN --db data/custom.db --parquet ./output/

  # List supported instruments
  lseg-extract --list
        """,
    )

    # Positional: symbols
    parser.add_argument(
        "symbols",
        nargs="*",
        help="Symbols to extract (e.g., ZN ZB EURUSD)",
    )

    # Special actions
    parser.add_argument(
        "--list",
        action="store_true",
        help="List supported instruments and exit",
    )

    # Asset class
    parser.add_argument(
        "--asset-class",
        choices=["futures", "fx", "ois", "govt-yield", "fra"],
        help="Asset class (auto-detected if not specified)",
    )

    # Date range
    parser.add_argument(
        "--start",
        type=parse_date,
        help="Start date (YYYY-MM-DD) [default: 1 year ago]",
    )
    parser.add_argument(
        "--end",
        type=parse_date,
        help="End date (YYYY-MM-DD) [default: today]",
    )

    # Granularity
    parser.add_argument(
        "--interval",
        choices=[
            "tick",
            "1min",
            "5min",
            "10min",
            "30min",
            "hourly",
            "daily",
            "weekly",
            "monthly",
        ],
        default="daily",
        help="Data interval [default: daily]",
    )

    # Continuous contract options
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Build continuous contract (futures only)",
    )
    parser.add_argument(
        "--adjust",
        choices=["none", "ratio", "difference"],
        default="ratio",
        help="Price adjustment method [default: ratio]",
    )
    parser.add_argument(
        "--roll-method",
        choices=["volume", "first-notice", "fixed-days", "expiry"],
        default="volume",
        help="Roll detection method [default: volume]",
    )
    parser.add_argument(
        "--roll-days",
        type=int,
        default=5,
        help="Days before expiry for fixed-days roll [default: 5]",
    )

    # Output options
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path [default: {DEFAULT_DB_PATH}]",
    )
    parser.add_argument(
        "--parquet",
        default=DEFAULT_PARQUET_DIR,
        help=f"Parquet output directory [default: {DEFAULT_PARQUET_DIR}]",
    )
    parser.add_argument(
        "--no-parquet",
        action="store_true",
        help="Skip Parquet export",
    )

    # Verbosity
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    # Handle special actions
    if args.list:
        list_instruments()
        sys.exit(0)

    # Validate symbols
    if not args.symbols:
        parser.error("At least one symbol is required (or use --list to see options)")

    # Map interval string to enum
    interval_map = {
        "tick": Granularity.TICK,
        "1min": Granularity.MINUTE_1,
        "5min": Granularity.MINUTE_5,
        "10min": Granularity.MINUTE_10,
        "30min": Granularity.MINUTE_30,
        "hourly": Granularity.HOURLY,
        "daily": Granularity.DAILY,
        "weekly": Granularity.WEEKLY,
        "monthly": Granularity.MONTHLY,
    }
    granularity = interval_map[args.interval]

    # Map asset class
    asset_class_map = {
        "futures": AssetClass.BOND_FUTURES,
        "fx": AssetClass.FX_SPOT,
        "ois": AssetClass.OIS,
        "govt-yield": AssetClass.GOVT_YIELD,
        "fra": AssetClass.FRA,
    }
    asset_class = asset_class_map.get(args.asset_class) if args.asset_class else None

    # Map adjustment type
    adjust_map = {
        "none": ContinuousType.UNADJUSTED,
        "ratio": ContinuousType.RATIO_ADJUSTED,
        "difference": ContinuousType.DIFFERENCE_ADJUSTED,
    }
    continuous_type = adjust_map[args.adjust]

    # Map roll method
    roll_map = {
        "volume": RollMethod.VOLUME_SWITCH,
        "first-notice": RollMethod.FIRST_NOTICE,
        "fixed-days": RollMethod.FIXED_DAYS,
        "expiry": RollMethod.EXPIRY,
    }
    roll_method = roll_map[args.roll_method]

    # Create config
    config = TimeSeriesConfig(
        symbols=args.symbols,
        asset_class=asset_class,
        start_date=args.start or (date.today() - timedelta(days=365)),
        end_date=args.end or date.today(),
        granularity=granularity,
        continuous=args.continuous,
        continuous_type=continuous_type,
        roll_method=roll_method,
        roll_days_before=args.roll_days,
        db_path=args.db,
        parquet_dir=args.parquet,
        export_parquet=not args.no_parquet,
    )

    # Run pipeline
    try:
        pipeline = TimeSeriesExtractionPipeline(config, verbose=not args.quiet)
        result = pipeline.run()

        if result.failure_count > 0:
            sys.exit(1)

    except LsegError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
