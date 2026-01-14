"""
Configuration for time series extraction.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus

from lseg_toolkit.timeseries.enums import (
    AssetClass,
    ContinuousType,
    Granularity,
    RollMethod,
)


@dataclass
class DatabaseConfig:
    """
    TimescaleDB/PostgreSQL connection configuration.

    Can be configured via environment variables:
        TSDB_HOST, TSDB_PORT, TSDB_DATABASE, TSDB_USER, TSDB_PASSWORD

    Example:
        >>> config = DatabaseConfig.from_env()
        >>> with psycopg.connect(config.dsn) as conn:
        ...     # use connection
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "timeseries"
    user: str = "postgres"
    password: str = ""

    # Connection pool settings
    pool_min_size: int = 2
    pool_max_size: int = 10

    # Batch settings - maximized for historical backfills
    batch_size: int = 50_000  # Rows per COPY batch

    @property
    def dsn(self) -> str:
        """Build PostgreSQL connection DSN with URL-encoded credentials."""
        if self.password:
            encoded_password = quote_plus(self.password)
            return f"postgresql://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.database}"
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """
        Load configuration from environment variables.

        Environment variables (TSDB_* preferred, POSTGRES_* as fallback):
            TSDB_HOST / POSTGRES_HOST: Database host (default: localhost)
            TSDB_PORT / POSTGRES_PORT: Database port (default: 5432)
            TSDB_DATABASE / POSTGRES_DB: Database name (default: timeseries)
            TSDB_USER / POSTGRES_USER: Database user (default: postgres)
            TSDB_PASSWORD / POSTGRES_PASSWORD: Database password (default: empty)
            TSDB_POOL_MIN: Min pool connections (default: 2)
            TSDB_POOL_MAX: Max pool connections (default: 10)
            TSDB_BATCH_SIZE: Rows per COPY batch (default: 50000)
        """
        return cls(
            host=os.getenv("TSDB_HOST", "") or os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("TSDB_PORT", "") or os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("TSDB_DATABASE", "")
            or os.getenv("POSTGRES_DB", "timeseries"),
            user=os.getenv("TSDB_USER", "") or os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("TSDB_PASSWORD", "")
            or os.getenv("POSTGRES_PASSWORD", ""),
            pool_min_size=int(os.getenv("TSDB_POOL_MIN", "2")),
            pool_max_size=int(os.getenv("TSDB_POOL_MAX", "10")),
            batch_size=int(os.getenv("TSDB_BATCH_SIZE", "50000")),
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
    parquet_dir: str = "data/parquet"
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
            if days_range > 365:
                raise ValueError(
                    f"Intraday data only available for ~365 days. "
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
            "parquet_dir": self.parquet_dir,
            "export_parquet": self.export_parquet,
        }
