"""
Enumerations for the timeseries module.
"""

from enum import Enum


class AssetClass(str, Enum):
    """Asset class classification for instruments."""

    # Futures
    BOND_FUTURES = "bond_futures"
    STIR_FUTURES = "stir_futures"
    INDEX_FUTURES = "index_futures"
    FX_FUTURES = "fx_futures"
    COMMODITY_FUTURES = "commodity_futures"

    # FX
    FX_SPOT = "fx_spot"
    FX_FORWARD = "fx_forward"

    # Rates
    OIS = "ois"
    IRS = "irs"
    FRA = "fra"
    DEPOSIT = "deposit"
    REPO = "repo"
    FIXING = "fixing"

    # Bonds
    GOVT_YIELD = "govt_yield"
    CORP_BOND = "corp_bond"

    # Equities & Funds
    EQUITY = "equity"
    ETF = "etf"
    EQUITY_INDEX = "equity_index"  # Spot indices (.SPX, .DJI)

    # Commodities (spot - XAU=, XAG= - uses Quote shape, not OHLCV)
    COMMODITY = "commodity"

    # Credit
    CDS = "cds"

    # Derivatives
    OPTION = "option"


class DataShape(str, Enum):
    """Data shape classification for routing to correct storage table."""

    OHLCV = "ohlcv"  # Futures, equities, commodities, indices
    QUOTE = "quote"  # FX spot, FX forwards
    RATE = "rate"  # OIS, IRS, FRA, repo, deposits
    BOND = "bond"  # Govt yields, corp bonds
    FIXING = "fixing"  # SOFR, ESTR, SONIA, EURIBOR fixings


class Granularity(str, Enum):
    """Time series data granularity.

    Note: 15min is NOT supported by LSEG API.
    Tick data requires recent dates (30-90 day retention).
    """

    TICK = "tick"
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_10 = "10min"
    MINUTE_30 = "30min"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ContinuousType(str, Enum):
    """Type of continuous contract series."""

    DISCRETE = "discrete"  # Single contract (e.g., TYH5)
    UNADJUSTED = "unadjusted"  # Stitched without price adjustment
    RATIO_ADJUSTED = "ratio_adjusted"  # Backward ratio adjustment
    DIFFERENCE_ADJUSTED = "difference_adjusted"  # Backward difference adjustment


class RollMethod(str, Enum):
    """Method for determining roll dates in continuous contracts."""

    VOLUME_SWITCH = "volume_switch"  # Roll when back month volume > front
    FIRST_NOTICE = "first_notice"  # Roll N days before first notice date
    FIXED_DAYS = "fixed_days"  # Roll N days before expiry
    EXPIRY = "expiry"  # Roll on expiry day (LSEG default for c1)


class FuturesMonth(str, Enum):
    """Futures month codes."""

    F = "F"  # January
    G = "G"  # February
    H = "H"  # March
    J = "J"  # April
    K = "K"  # May
    M = "M"  # June
    N = "N"  # July
    Q = "Q"  # August
    U = "U"  # September
    V = "V"  # October
    X = "X"  # November
    Z = "Z"  # December

    @classmethod
    def from_month(cls, month: int) -> "FuturesMonth":
        """Get month code from month number (1-12)."""
        codes = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]
        return cls(codes[month - 1])

    def to_month(self) -> int:
        """Get month number (1-12) from month code."""
        codes = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]
        return codes.index(self.value) + 1
