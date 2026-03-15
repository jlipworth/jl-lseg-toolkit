"""
Backfill the 12-rank Fed Funds continuous strip into TimescaleDB.

Examples:
    uv run python scripts/backfill_ff_strip.py
    uv run python scripts/backfill_ff_strip.py --daily-start 2018-01-01
    uv run python scripts/backfill_ff_strip.py --ranks 1-6 --skip-hourly
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from lseg_toolkit.timeseries.client import ClientConfig, LSEGDataClient
from lseg_toolkit.timeseries.enums import AssetClass, Granularity
from lseg_toolkit.timeseries.fed_funds import (
    fetch_fed_funds_daily,
    fetch_fed_funds_hourly,
    get_ff_continuous_symbol,
)
from lseg_toolkit.timeseries.storage import (
    get_connection,
    log_extraction,
    save_instrument,
    save_timeseries,
)


def parse_ranks(spec: str) -> list[int]:
    """Parse a rank list like '1-12' or '1,2,5,8'."""
    spec = spec.strip()
    if "-" in spec:
        start_str, end_str = spec.split("-", 1)
        start = int(start_str)
        end = int(end_str)
        if start > end:
            raise ValueError("rank range start must be <= end")
        return list(range(start, end + 1))
    return [int(part.strip()) for part in spec.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill the Fed Funds 12-rank continuous strip into TSDB."
    )
    parser.add_argument(
        "--ranks",
        default="1-12",
        help="Ranks to load, e.g. '1-12' or '1,2,3' (default: 1-12).",
    )
    parser.add_argument(
        "--daily-start",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=3650),
        help="Daily backfill start date (default: ~10 years ago).",
    )
    parser.add_argument(
        "--daily-end",
        type=date.fromisoformat,
        default=date.today(),
        help="Daily backfill end date (default: today).",
    )
    parser.add_argument(
        "--hourly-start",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=370),
        help="Hourly backfill start date (default: 370 days ago).",
    )
    parser.add_argument(
        "--hourly-end",
        type=date.fromisoformat,
        default=date.today(),
        help="Hourly backfill end date (default: today).",
    )
    parser.add_argument(
        "--skip-daily",
        action="store_true",
        help="Skip daily backfill.",
    )
    parser.add_argument(
        "--skip-hourly",
        action="store_true",
        help="Skip hourly backfill.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ranks = parse_ranks(args.ranks)
    client = LSEGDataClient(ClientConfig())

    total_rows = 0

    try:
        with get_connection() as conn:
            for rank in ranks:
                symbol = get_ff_continuous_symbol(rank)
                ric = f"FFc{rank}"
                name = (
                    "30-Day Fed Funds Continuous"
                    if rank == 1
                    else f"30-Day Fed Funds Continuous Rank {rank}"
                )

                instrument_id = save_instrument(
                    conn,
                    symbol=symbol,
                    name=name,
                    asset_class=AssetClass.STIR_FUTURES,
                    lseg_ric=ric,
                    underlying="FF",
                    exchange="CME",
                    continuous_type="continuous",
                )

                print(f"\n=== {symbol} ({ric}) ===")

                if not args.skip_daily:
                    daily_df = fetch_fed_funds_daily(
                        client,
                        args.daily_start,
                        args.daily_end,
                        rank=rank,
                    )
                    daily_rows = save_timeseries(
                        conn,
                        instrument_id,
                        daily_df,
                        Granularity.DAILY,
                    )
                    log_extraction(
                        conn,
                        symbol,
                        args.daily_start,
                        args.daily_end,
                        Granularity.DAILY,
                        daily_rows,
                    )
                    total_rows += daily_rows
                    print(
                        f"daily:  {daily_rows:>6} rows "
                        f"({args.daily_start.isoformat()} -> {args.daily_end.isoformat()})"
                    )

                if not args.skip_hourly:
                    hourly_df = fetch_fed_funds_hourly(
                        client,
                        args.hourly_start,
                        args.hourly_end,
                        rank=rank,
                    )
                    hourly_rows = save_timeseries(
                        conn,
                        instrument_id,
                        hourly_df,
                        Granularity.HOURLY,
                    )
                    log_extraction(
                        conn,
                        symbol,
                        args.hourly_start,
                        args.hourly_end,
                        Granularity.HOURLY,
                        hourly_rows,
                    )
                    total_rows += hourly_rows
                    print(
                        f"hourly: {hourly_rows:>6} rows "
                        f"({args.hourly_start.isoformat()} -> {args.hourly_end.isoformat()})"
                    )

            conn.commit()

    finally:
        if client._session is not None:  # noqa: SLF001
            client._session.close_session()  # noqa: SLF001

    print(f"\nDone. Total rows written: {total_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
