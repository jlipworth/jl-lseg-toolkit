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
# Validated: All tenors work with bare = pattern for both snapshot and history
# Contributor suffixes (=TREU, =ICAP) return "Access Denied"
# Alternative USDSOFR{tenor}= pattern does not exist
def get_ois_ric(currency: str, tenor: str) -> str:
    """Get OIS RIC for currency and tenor."""
    return f"{currency}{tenor}OIS="


# Validated fields for OIS rates
USD_OIS_FIELDS: list[str] = [
    "BID",
    "ASK",
    "HST_CLOSE",
    "PRIMACT_1",  # Primary rate value
]

USD_OIS_META_FIELDS: list[str] = [
    "VALUE_TS1",
    "VALUE_DT1",
    "CF_NAME",
    "DSPLY_NAME",
    "CURRENCY",
    "CF_CURR",
]

# SOFR Fixing RICs (validated)
SOFR_FIXING_RICS: dict[str, str] = {
    "DAILY": "USDSOFR=",  # Daily SOFR fixing - WORKS
    "30D_AVG": "SOFR1MAVG=",  # 30-day compounded SOFR - WORKS
}

SOFR_FIXING_FIELDS: list[str] = [
    "PRIMACT_1",  # Fixing rate value
    "VALUE_DT1",
    "VALUE_TS1",
]


# =============================================================================
# Treasury Repo Rates (Validated 2026-01-06)
# =============================================================================

# Validated: ON, 1W, 2W, 3W, 1M, 2M, 3M, 6M all work
# Not available: 9M, 12M
USD_REPO_RICS: dict[str, str] = {
    "ON": "USONRP=",  # Overnight
    "1W": "US1WRP=",  # 1 Week
    "2W": "US2WRP=",  # 2 Week
    "3W": "US3WRP=",  # 3 Week
    "1M": "US1MRP=",  # 1 Month
    "2M": "US2MRP=",  # 2 Month
    "3M": "US3MRP=",  # 3 Month
    "6M": "US6MRP=",  # 6 Month
}

USD_REPO_FIELDS: list[str] = [
    "BID",
    "ASK",
    "PRIMACT_1",
    "HST_CLOSE",
    "VALUE_DT1",
    "VALUE_TS1",
    "CF_NAME",
    "DSPLY_NAME",
]


def get_repo_ric(tenor: str) -> str:
    """Get Treasury repo RIC for tenor."""
    return USD_REPO_RICS.get(tenor, f"US{tenor}RP=")


# =============================================================================
# STIR Futures (Short-Term Interest Rate) - Validated 2026-01-06
# =============================================================================

STIR_FUTURES_RICS: dict[str, str] = {
    # USD SOFR
    "SOFR_3M": "SRAc1",  # 3-Month SOFR continuous front (CME SR3)
    # Fed Funds
    "FF": "FFc1",  # 30-Day Fed Funds continuous
    "FF_CHAIN": "0#FF:",  # Fed Funds contract chain
    # EUR Euribor
    "EURIBOR_3M": "FEIc1",  # 3-Month Euribor continuous
    "EURIBOR_CHAIN": "0#FEI:",  # Euribor contract chain
    # GBP SONIA
    "SONIA": "SONc1",  # SONIA continuous
}


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
# Validated: All tenors work with =RRPS for both snapshot and history
# Alternative =X works but has fewer fields (no MID_YLD_1, no risk metrics)
def get_treasury_yield_ric(tenor: str) -> str:
    """Get US Treasury yield RIC for tenor."""
    return f"US{tenor}T=RRPS"


# Validated fields for Treasury yields (=RRPS pattern)
UST_YIELD_FIELDS: list[str] = [
    "BID",
    "ASK",
    "HIGH_1",
    "LOW_1",
    "OPEN_PRC",
    "HST_CLOSE",
    "PRIMACT_1",
    "MID_YLD_1",  # Primary yield field
    "SEC_YLD_1",
]

UST_YIELD_RISK_FIELDS: list[str] = [
    "MOD_DURTN",
    "BPV",
    "DURATION",
    "CONVEXITY",
]

UST_YIELD_META_FIELDS: list[str] = [
    "VALUE_TS1",
    "VALUE_DT1",
    "CF_NAME",
    "DSPLY_NAME",
    "CURRENCY",
]


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
