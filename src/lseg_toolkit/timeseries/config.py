"""
Configuration for time series extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from lseg_toolkit.timeseries.constants import DEFAULT_DB_PATH, DEFAULT_PARQUET_DIR
from lseg_toolkit.timeseries.enums import (
    AssetClass,
    ContinuousType,
    Granularity,
    RollMethod,
)


def _default_start_date() -> date:
    """Default start date: 1 year ago."""
    return date.today() - timedelta(days=365)


def _default_end_date() -> date:
    """Default end date: today."""
    return date.today()


@dataclass
class TimeSeriesConfig:
    """
    Configuration for time series extraction.

    Attributes:
        symbols: List of symbols to extract (e.g., ['ZN', 'EURUSD'])
        asset_class: Asset class for the symbols (auto-detected if None)
        start_date: Start date for extraction
        end_date: End date for extraction
        granularity: Data granularity (default: daily)
        continuous: Whether to build continuous contracts (futures only)
        continuous_type: Type of continuous series to build
        roll_method: Method for determining roll dates
        roll_days_before: Days before expiry/notice for FIXED_DAYS roll
        db_path: Path to SQLite database
        parquet_dir: Directory for Parquet exports
        export_parquet: Whether to export to Parquet
    """

    symbols: list[str] = field(default_factory=list)
    asset_class: AssetClass | None = None
    start_date: date = field(default_factory=_default_start_date)
    end_date: date = field(default_factory=_default_end_date)
    granularity: Granularity = Granularity.DAILY
    continuous: bool = False
    continuous_type: ContinuousType = ContinuousType.RATIO_ADJUSTED
    roll_method: RollMethod = RollMethod.VOLUME_SWITCH
    roll_days_before: int = 5
    db_path: str = DEFAULT_DB_PATH
    parquet_dir: str = DEFAULT_PARQUET_DIR
    export_parquet: bool = True

    def __post_init__(self):
        """Validate configuration."""
        # Convert datetime to date if needed
        if isinstance(self.start_date, datetime):
            self.start_date = self.start_date.date()
        if isinstance(self.end_date, datetime):
            self.end_date = self.end_date.date()

        # Validate date range
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")

        # Validate intraday date range
        if self.granularity in (
            Granularity.TICK,
            Granularity.MINUTE_1,
            Granularity.MINUTE_5,
            Granularity.MINUTE_10,
            Granularity.MINUTE_30,
            Granularity.HOURLY,
        ):
            days_range = (self.end_date - self.start_date).days
            if days_range > 90:
                raise ValueError(
                    f"Intraday data only available for ~90 days. "
                    f"Requested range: {days_range} days"
                )

        # Validate roll_days_before
        if self.roll_method == RollMethod.FIXED_DAYS and self.roll_days_before < 1:
            raise ValueError("roll_days_before must be >= 1 for FIXED_DAYS method")

    def to_dict(self) -> dict:
        """Convert config to dictionary for summary/logging."""
        return {
            "symbols": self.symbols,
            "asset_class": self.asset_class.value if self.asset_class else "auto",
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "granularity": self.granularity.value,
            "continuous": self.continuous,
            "continuous_type": self.continuous_type.value if self.continuous else None,
            "roll_method": self.roll_method.value if self.continuous else None,
            "db_path": self.db_path,
            "parquet_dir": self.parquet_dir,
            "export_parquet": self.export_parquet,
        }
