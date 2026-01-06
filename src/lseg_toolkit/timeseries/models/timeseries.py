"""
Time series data models for the timeseries module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from lseg_toolkit.timeseries.enums import Granularity


@dataclass
class OHLCV:
    """Single OHLCV bar.

    Attributes:
        timestamp: Bar timestamp
        open: Opening price
        high: High price
        low: Low price
        close: Closing price
        volume: Trading volume
        open_interest: Open interest (futures only)
        settle: Settlement price (futures only)
    """

    timestamp: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float = 0.0
    volume: float | None = None
    open_interest: float | None = None
    settle: float | None = None

    @property
    def date(self) -> date:
        """Get date portion of timestamp."""
        return self.timestamp.date()

    @property
    def mid(self) -> float | None:
        """Calculate mid price from high/low."""
        if self.high is not None and self.low is not None:
            return (self.high + self.low) / 2
        return None


@dataclass
class TimeSeries:
    """Container for time series data.

    Attributes:
        symbol: Instrument symbol
        lseg_ric: LSEG RIC used to fetch data
        granularity: Data granularity
        start_date: Series start date
        end_date: Series end date
        data: DataFrame with OHLCV data
        source_contract: For continuous series, the underlying contract
        adjustment_factor: Cumulative adjustment factor (for adjusted series)
    """

    symbol: str
    lseg_ric: str
    granularity: Granularity
    start_date: date
    end_date: date
    data: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_contract: str | None = None
    adjustment_factor: float = 1.0

    def __post_init__(self):
        """Validate time series."""
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")

    def __len__(self) -> int:
        """Return number of bars."""
        return len(self.data)

    @property
    def is_empty(self) -> bool:
        """Check if series has no data."""
        return self.data.empty

    @property
    def first_date(self) -> date | None:
        """Get first date in series."""
        if self.is_empty:
            return None
        return self.data.index.min().date()

    @property
    def last_date(self) -> date | None:
        """Get last date in series."""
        if self.is_empty:
            return None
        return self.data.index.max().date()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "lseg_ric": self.lseg_ric,
            "granularity": self.granularity.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "rows": len(self.data),
            "first_date": self.first_date.isoformat() if self.first_date else None,
            "last_date": self.last_date.isoformat() if self.last_date else None,
        }


@dataclass
class RollEvent:
    """Roll event for continuous contract construction.

    Attributes:
        roll_date: Date of the roll
        from_contract: Contract being rolled out of (e.g., 'TYH5')
        to_contract: Contract being rolled into (e.g., 'TYM5')
        from_price: Price of from_contract at roll
        to_price: Price of to_contract at roll
        price_gap: to_price - from_price
        adjustment_factor: Ratio adjustment factor (to_price / from_price)
        roll_method: Method used to determine roll date
    """

    roll_date: date
    from_contract: str
    to_contract: str
    from_price: float
    to_price: float
    price_gap: float = field(init=False)
    adjustment_factor: float = field(init=False)
    roll_method: str = ""

    def __post_init__(self):
        """Calculate derived fields."""
        self.price_gap = self.to_price - self.from_price
        if self.from_price != 0:
            self.adjustment_factor = self.to_price / self.from_price
        else:
            self.adjustment_factor = 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "roll_date": self.roll_date.isoformat(),
            "from_contract": self.from_contract,
            "to_contract": self.to_contract,
            "from_price": self.from_price,
            "to_price": self.to_price,
            "price_gap": self.price_gap,
            "adjustment_factor": self.adjustment_factor,
            "roll_method": self.roll_method,
        }
