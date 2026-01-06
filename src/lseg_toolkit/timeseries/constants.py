"""
Constants for the timeseries module.

Contains CME→LSEG symbol mappings, instrument specifications, and RIC patterns.
"""

from __future__ import annotations

# =============================================================================
# CME → LSEG Symbol Mapping
# =============================================================================

# US Treasury Futures: CME symbol → LSEG RIC root
TREASURY_FUTURES_MAPPING: dict[str, str] = {
    "ZT": "TU",  # 2-Year T-Note
    "Z3N": "Z3N",  # 3-Year T-Note
    "ZF": "FV",  # 5-Year T-Note
    "ZN": "TY",  # 10-Year T-Note
    "TN": "TN",  # Ultra 10-Year
    "TWE": "TWE",  # 20-Year T-Bond
    "ZB": "US",  # 30-Year T-Bond
    "UB": "UB",  # Ultra 30-Year
}

# European Bond Futures
EUROPEAN_FUTURES_MAPPING: dict[str, str] = {
    "FGBL": "FGBL",  # Euro-Bund 10Y
    "FGBM": "FGBM",  # Euro-Bobl 5Y
    "FGBS": "FGBS",  # Euro-Schatz 2Y
    "FGBX": "FGBX",  # Euro-Buxl 30Y
    "FLG": "FLG",  # UK Long Gilt
}

# FX Futures: CME symbol → LSEG RIC root
FX_FUTURES_MAPPING: dict[str, str] = {
    "6E": "URO",  # Euro FX
    "6B": "BP",  # British Pound
    "6J": "JY",  # Japanese Yen
    "6A": "AD",  # Australian Dollar
    "6C": "CD",  # Canadian Dollar
    "6S": "SF",  # Swiss Franc
}

# Grains: CME symbol → LSEG RIC root
GRAIN_FUTURES_MAPPING: dict[str, str] = {
    "ZC": "C",  # Corn
    "ZW": "W",  # Wheat (SRW)
    "ZS": "S",  # Soybeans
    "ZL": "BO",  # Soybean Oil
    "ZM": "SM",  # Soybean Meal
    "KE": "KW",  # KC HRW Wheat
}

# All futures mappings combined
ALL_FUTURES_MAPPING: dict[str, str] = {
    **TREASURY_FUTURES_MAPPING,
    **EUROPEAN_FUTURES_MAPPING,
    **FX_FUTURES_MAPPING,
    **GRAIN_FUTURES_MAPPING,
}

# Reverse mapping: LSEG RIC root → CME symbol
LSEG_TO_CME_MAPPING: dict[str, str] = {v: k for k, v in ALL_FUTURES_MAPPING.items()}


# =============================================================================
# FX Spot RIC Patterns
# =============================================================================

FX_SPOT_RICS: dict[str, str] = {
    "EURUSD": "EUR=",
    "GBPUSD": "GBP=",
    "USDJPY": "JPY=",
    "USDCHF": "CHF=",
    "AUDUSD": "AUD=",
    "USDCAD": "CAD=",
    "NZDUSD": "NZD=",
    "EURGBP": "EURGBP=",
    "EURJPY": "EURJPY=",
    "EURCHF": "EURCHF=",
    "GBPJPY": "GBPJPY=",
}


# =============================================================================
# OIS Tenors
# =============================================================================

USD_OIS_TENORS: list[str] = [
    "1M",
    "2M",
    "3M",
    "4M",
    "5M",
    "6M",
    "9M",
    "1Y",
    "18M",
    "2Y",
    "3Y",
    "4Y",
    "5Y",
    "6Y",
    "7Y",
    "8Y",
    "9Y",
    "10Y",
    "12Y",
    "15Y",
    "20Y",
    "25Y",
    "30Y",
]


# OIS RIC pattern: USD{tenor}OIS=
def get_ois_ric(currency: str, tenor: str) -> str:
    """Get OIS RIC for currency and tenor."""
    return f"{currency}{tenor}OIS="


# =============================================================================
# US Treasury Yield Curve
# =============================================================================

UST_YIELD_TENORS: list[str] = [
    "1M",
    "2M",
    "3M",
    "4M",
    "6M",  # T-Bills
    "1Y",
    "2Y",
    "3Y",
    "5Y",
    "7Y",
    "10Y",
    "20Y",
    "30Y",  # Notes/Bonds
]


# Treasury yield RIC pattern: US{tenor}T=RRPS
def get_treasury_yield_ric(tenor: str) -> str:
    """Get US Treasury yield RIC for tenor."""
    return f"US{tenor}T=RRPS"


# =============================================================================
# FRA Patterns
# =============================================================================

USD_FRA_TENORS: list[str] = [
    "1X4",
    "2X5",
    "3X6",
    "4X7",
    "5X8",
    "6X9",  # Standard
    "1X7",
    "2X8",
    "3X9",  # Extended
]


# FRA RIC pattern: USD{tenor}F=
def get_fra_ric(currency: str, tenor: str) -> str:
    """Get FRA RIC for currency and tenor (e.g., '3X6')."""
    return f"{currency}{tenor}F="


# =============================================================================
# Deposit Rates
# =============================================================================

USD_DEPOSIT_TENORS: list[str] = ["ON", "TN", "SW", "1M", "3M", "6M", "9M", "1Y"]


# Deposit RIC pattern: USD{tenor}D=
def get_deposit_ric(currency: str, tenor: str) -> str:
    """Get deposit rate RIC for currency and tenor."""
    return f"{currency}{tenor}D="


# =============================================================================
# LSEG API Intervals
# =============================================================================

# Valid interval strings for rd.get_history()
VALID_INTERVALS: list[str] = [
    "tick",
    "1min",
    "5min",
    "10min",
    "30min",  # Note: 15min NOT supported
    "hourly",
    "daily",
    "weekly",
    "monthly",
]

# Intraday data retention (approximate)
INTRADAY_RETENTION_DAYS: int = 90


# =============================================================================
# LSEG Field Mappings
# =============================================================================

# Standard OHLCV fields for futures
FUTURES_OHLCV_FIELDS: list[str] = [
    "OPEN_PRC",  # Open
    "HIGH_1",  # High
    "LOW_1",  # Low
    "TRDPRC_1",  # Last/Close
    "SETTLE",  # Settlement price
    "ACVOL_UNS",  # Volume
    "OPINT_1",  # Open interest
]

# FX spot fields
FX_SPOT_FIELDS: list[str] = [
    "BID",
    "ASK",
    "BID_HIGH_1",
    "BID_LOW_1",
]

# Column name normalization: LSEG → Standard
COLUMN_MAPPING: dict[str, str] = {
    "OPEN_PRC": "open",
    "HIGH_1": "high",
    "LOW_1": "low",
    "TRDPRC_1": "close",
    "SETTLE": "settle",
    "ACVOL_UNS": "volume",
    "OPINT_1": "open_interest",
    "BID": "bid",
    "ASK": "ask",
    "BID_HIGH_1": "high",
    "BID_LOW_1": "low",
}


# =============================================================================
# Default Database Path
# =============================================================================

DEFAULT_DB_PATH: str = "data/timeseries.db"
DEFAULT_PARQUET_DIR: str = "data/parquet"
