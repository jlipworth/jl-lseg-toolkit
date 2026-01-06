"""
Instrument dataclasses for the timeseries module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from lseg_toolkit.timeseries.enums import AssetClass, ContinuousType


@dataclass
class Instrument:
    """Base class for all instruments.

    Attributes:
        symbol: User-facing symbol (e.g., 'ZN', 'EURUSD')
        lseg_ric: LSEG RIC code (e.g., 'TYc1', 'EUR=')
        name: Human-readable name
        asset_class: Asset class classification
    """

    symbol: str
    lseg_ric: str
    name: str
    asset_class: AssetClass

    def __post_init__(self):
        """Validate instrument data."""
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if not self.lseg_ric:
            raise ValueError("lseg_ric cannot be empty")


@dataclass
class FuturesContract(Instrument):
    """Futures contract instrument.

    Attributes:
        underlying: Underlying root symbol (e.g., 'ZN', 'FGBL')
        expiry_date: Contract expiration date
        expiry_month: Month code (H, M, U, Z)
        expiry_year: Two-digit year
        continuous_type: Type if this is a continuous contract
        tick_size: Minimum price movement
        point_value: Dollar value per point
    """

    underlying: str = ""
    expiry_date: date | None = None
    expiry_month: str | None = None
    expiry_year: int | None = None
    continuous_type: ContinuousType = ContinuousType.DISCRETE
    tick_size: float = 0.0
    point_value: float = 0.0

    def __post_init__(self):
        """Validate and set defaults."""
        super().__post_init__()
        if not self.underlying:
            # Extract underlying from symbol
            self.underlying = self.symbol.rstrip("0123456789cHMUZ")

    @property
    def is_continuous(self) -> bool:
        """Check if this is a continuous contract."""
        return self.continuous_type != ContinuousType.DISCRETE

    @classmethod
    def from_continuous_ric(
        cls,
        symbol: str,
        lseg_ric: str,
        name: str,
        asset_class: AssetClass = AssetClass.BOND_FUTURES,
    ) -> FuturesContract:
        """Create a continuous futures contract.

        Args:
            symbol: User symbol (e.g., 'ZN')
            lseg_ric: LSEG continuous RIC (e.g., 'TYc1')
            name: Human-readable name
            asset_class: Asset class (default: bond_futures)
        """
        return cls(
            symbol=symbol,
            lseg_ric=lseg_ric,
            name=name,
            asset_class=asset_class,
            underlying=symbol,
            continuous_type=ContinuousType.UNADJUSTED,
        )


@dataclass
class FXSpot(Instrument):
    """FX spot rate instrument.

    Attributes:
        base_currency: Base currency (e.g., 'EUR')
        quote_currency: Quote currency (e.g., 'USD')
        pip_size: Size of one pip
    """

    base_currency: str = ""
    quote_currency: str = ""
    pip_size: float = 0.0001

    def __post_init__(self):
        """Validate and extract currency pair."""
        super().__post_init__()
        # Auto-detect asset class
        if self.asset_class == AssetClass.FX_SPOT:
            pass  # Already set correctly
        # Extract currencies from symbol if not provided
        if not self.base_currency and len(self.symbol) >= 6:
            self.base_currency = self.symbol[:3]
            self.quote_currency = self.symbol[3:6]
        # JPY pairs have different pip size
        if self.quote_currency == "JPY" or self.base_currency == "JPY":
            self.pip_size = 0.01


@dataclass
class OISRate(Instrument):
    """Overnight Index Swap rate.

    Attributes:
        currency: Currency (e.g., 'USD')
        tenor: Tenor string (e.g., '1M', '5Y')
        reference_rate: Reference overnight rate (e.g., 'SOFR', 'SONIA')
    """

    currency: str = ""
    tenor: str = ""
    reference_rate: str = ""

    def __post_init__(self):
        """Validate OIS rate."""
        super().__post_init__()
        if self.asset_class != AssetClass.OIS:
            self.asset_class = AssetClass.OIS
        # Auto-detect reference rate from currency
        if not self.reference_rate:
            reference_rates = {
                "USD": "SOFR",
                "EUR": "ESTR",
                "GBP": "SONIA",
                "JPY": "TONA",
                "CHF": "SARON",
            }
            self.reference_rate = reference_rates.get(self.currency, "")


@dataclass
class GovernmentYield(Instrument):
    """Government bond yield.

    Attributes:
        country: Country code (e.g., 'US', 'DE', 'GB')
        tenor: Tenor string (e.g., '10Y', '2Y')
    """

    country: str = ""
    tenor: str = ""

    def __post_init__(self):
        """Validate government yield."""
        super().__post_init__()
        if self.asset_class != AssetClass.GOVT_YIELD:
            self.asset_class = AssetClass.GOVT_YIELD


@dataclass
class FRA(Instrument):
    """Forward Rate Agreement.

    Attributes:
        currency: Currency (e.g., 'USD')
        start_months: Months until start (e.g., 3 for 3x6)
        end_months: Months until end (e.g., 6 for 3x6)
    """

    currency: str = ""
    start_months: int = 0
    end_months: int = 0

    def __post_init__(self):
        """Validate FRA."""
        super().__post_init__()
        if self.asset_class != AssetClass.FRA:
            self.asset_class = AssetClass.FRA

    @property
    def tenor(self) -> str:
        """Get tenor string (e.g., '3X6')."""
        return f"{self.start_months}X{self.end_months}"
