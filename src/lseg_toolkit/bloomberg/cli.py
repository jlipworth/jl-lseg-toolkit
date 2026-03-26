"""
Supported Bloomberg CLI.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from lseg_toolkit.bloomberg.connection import BloombergError
from lseg_toolkit.bloomberg.export import export_csv
from lseg_toolkit.bloomberg.fx_atm_vol import (
    DEFAULT_PAIRS,
    DEFAULT_TENORS,
    extract_fx_atm_vol_historical,
    extract_fx_atm_vol_snapshot,
)
from lseg_toolkit.bloomberg.jgb import extract_jgb_historical, extract_jgb_snapshot
from lseg_toolkit.exceptions import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def parse_date(value: str):
    """Parse YYYY-MM-DD dates for CLI use."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {value}. Use YYYY-MM-DD"
        ) from exc


def cmd_jgb(args: argparse.Namespace) -> int:
    if args.historical:
        if args.start_date is None:
            raise SystemExit("--start-date is required with --historical")
        df = extract_jgb_historical(
            start_date=args.start_date,
            end_date=args.end_date,
            tenors=args.tenors,
        )
    else:
        df = extract_jgb_snapshot(tenors=args.tenors)

    if df.empty:
        print("No data returned")
        return 0

    if args.output:
        path = export_csv(df, args.output)
        print(f"Saved to {path}")
    else:
        print(df.to_string(index=False))

    return 0


def cmd_fx_atm_vol(args: argparse.Namespace) -> int:
    if args.historical:
        if args.start_date is None:
            raise SystemExit("--start-date is required with --historical")
        df = extract_fx_atm_vol_historical(
            start_date=args.start_date,
            end_date=args.end_date,
            pairs=args.pairs,
            tenors=args.tenors,
        )
    else:
        df = extract_fx_atm_vol_snapshot(
            pairs=args.pairs,
            tenors=args.tenors,
        )

    if df.empty:
        print("No data returned")
        return 0

    if args.output:
        path = export_csv(df, args.output)
        print(f"Saved to {path}")
    else:
        print(df.to_string(index=False))

    return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bbg-extract",
        description="Supported Bloomberg workflows",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    jgb_parser = subparsers.add_parser("jgb", help="Fetch JGB yields")
    jgb_parser.add_argument("--tenors", nargs="+", default=None)
    jgb_parser.add_argument("--historical", action="store_true")
    jgb_parser.add_argument("--start-date", type=parse_date, default=None)
    jgb_parser.add_argument("--end-date", type=parse_date, default=None)
    jgb_parser.add_argument("--output", type=Path, default=None)
    jgb_parser.set_defaults(func=cmd_jgb)

    fx_parser = subparsers.add_parser("fx-atm-vol", help="Fetch FX ATM implied vol")
    fx_parser.add_argument("--pairs", nargs="+", default=list(DEFAULT_PAIRS))
    fx_parser.add_argument("--tenors", nargs="+", default=list(DEFAULT_TENORS))
    fx_parser.add_argument("--historical", action="store_true")
    fx_parser.add_argument("--start-date", type=parse_date, default=None)
    fx_parser.add_argument("--end-date", type=parse_date, default=None)
    fx_parser.add_argument("--output", type=Path, default=None)
    fx_parser.set_defaults(func=cmd_fx_atm_vol)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except ConfigurationError as exc:
        print(f"Bloomberg configuration error: {exc}", file=sys.stderr)
        return 2
    except BloombergError as exc:
        print(f"Bloomberg runtime error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
