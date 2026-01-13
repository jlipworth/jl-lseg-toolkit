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

# Stock Index Futures (Validated 2026-01-07)
INDEX_FUTURES_MAPPING: dict[str, str] = {
    # US (CME)
    "ES": "ES",  # E-mini S&P 500
    "NQ": "NQ",  # E-mini Nasdaq-100
    "RTY": "RTY",  # E-mini Russell 2000
    "YM": "YM",  # E-mini Dow
    "VX": "VX",  # VIX Futures
    # Canada (TMX)
    "SXF": "SXF",  # S&P/TSX 60
    # European (Eurex/ICE)
    "FESX": "STXE",  # Euro Stoxx 50
    "FXXP": "FXXP",  # STOXX Europe 600
    "FDAX": "FDX",  # DAX
    "FCE": "FCE",  # CAC 40
    "Z": "FFI",  # FTSE 100
    "FMIB": "FMIB",  # FTSE MIB (Italy)
    "FSMI": "FSMI",  # SMI (Swiss)
    "FTI": "AEX",  # AEX (Dutch)
    # Asian
    "JNI": "JNI",  # Nikkei 225 (Osaka)
    "NIY": "NIY",  # Nikkei 225 (CME Yen)
    "HSI": "HSI",  # Hang Seng
    "HCEI": "HCEI",  # Hang Seng China Enterprises
    "KS": "KS",  # KOSPI 200
    "TX": "TX",  # TAIEX (Taiwan)
    "YAP": "YAP",  # ASX 200 Mini (Australia)
    "SSN": "SSN",  # SGX Nifty (India)
    # Latin America
    "IND": "IND",  # Bovespa (Brazil)
    "WSP": "WSP",  # Mini Bovespa (Brazil)
    "IPC": "IPC",  # IPC Mexico
}

# Bond Futures - Asian (Validated 2026-01-06)
ASIAN_BOND_FUTURES_MAPPING: dict[str, str] = {
    "JGB": "JGB",  # 10Y JGB (Japan)
}

# Commodity Futures (Validated 2026-01-06)
COMMODITY_FUTURES_MAPPING: dict[str, str] = {
    # Energy
    "CL": "CL",  # WTI Crude
    "BRN": "LCO",  # Brent Crude
    "NG": "NG",  # Natural Gas
    "RB": "RB",  # RBOB Gasoline
    "HO": "HO",  # Heating Oil
    "LGO": "LGO",  # Gasoil ICE
    # Metals
    "GC": "GC",  # Gold
    "SI": "SI",  # Silver
    "HG": "HG",  # Copper
    "PL": "PL",  # Platinum
    "PA": "PA",  # Palladium
    # Grains
    "ZC": "C",  # Corn
    "ZW": "W",  # Wheat (SRW)
    "ZS": "S",  # Soybeans
    "ZL": "BO",  # Soybean Oil
    "ZM": "SM",  # Soybean Meal
    "KE": "KW",  # KC HRW Wheat
    # Softs
    "KC": "KC",  # Coffee
    "SB": "SB",  # Sugar
    "CC": "CC",  # Cocoa
    "CT": "CT",  # Cotton
    # Livestock
    "LE": "LC",  # Live Cattle
    "GF": "FC",  # Feeder Cattle
    "HE": "LH",  # Lean Hogs
}

# All futures mappings combined
ALL_FUTURES_MAPPING: dict[str, str] = {
    **TREASURY_FUTURES_MAPPING,
    **EUROPEAN_FUTURES_MAPPING,
    **FX_FUTURES_MAPPING,
    **INDEX_FUTURES_MAPPING,
    **COMMODITY_FUTURES_MAPPING,
}

# Reverse mapping: LSEG RIC root → CME symbol
LSEG_TO_CME_MAPPING: dict[str, str] = {v: k for k, v in ALL_FUTURES_MAPPING.items()}


# =============================================================================
# Equity Index (Spot) RICs (Validated 2026-01-07)
# =============================================================================

EQUITY_INDEX_RICS: dict[str, str] = {
    # US Indices
    "SPX": ".SPX",  # S&P 500
    "NDX": ".NDX",  # Nasdaq 100
    "DJI": ".DJI",  # Dow Jones Industrial
    "RUT": ".RUT",  # Russell 2000
    "RUI": ".RUI",  # Russell 1000
    "RUA": ".RUA",  # Russell 3000
    "IXIC": ".IXIC",  # Nasdaq Composite
    "SP400": ".SP400",  # S&P MidCap 400
    # Canadian
    "SPTSE": ".SPTSE",  # S&P/TSX Composite (old)
    "GSPTSE": ".GSPTSE",  # S&P/TSX Composite
    # European
    "FTSE": ".FTSE",  # FTSE 100
    "GDAXI": ".GDAXI",  # DAX
    "FCHI": ".FCHI",  # CAC 40
    "FTMIB": ".FTMIB",  # FTSE MIB
    "AEX": ".AEX",  # AEX
    "IBEX": ".IBEX",  # IBEX 35
    "STOXX": ".STOXX",  # STOXX Europe 600
    "STOXX50E": ".STOXX50E",  # Euro STOXX 50
    # Asian
    "N225": ".N225",  # Nikkei 225
    "TOPX": ".TOPX",  # TOPIX
    "CSI300": ".CSI000300",  # CSI 300
    "HSI": ".HSI",  # Hang Seng
    "KS11": ".KS11",  # KOSPI
    "AXJO": ".AXJO",  # ASX 200
    # Latin American
    "BVSP": ".BVSP",  # Bovespa
    "MXX": ".MXX",  # IPC Mexico
    "SPIPSA": ".SPIPSA",  # S&P IPSA Chile
    "MERV": ".MERV",  # MERVAL Argentina
    "IBC": ".IBC",  # IBC Venezuela
    "COLCAP": ".COLCAP",  # COLCAP Colombia
    # Other
    "NSEI": ".NSEI",  # Nifty 50
    "SPCY": ".SPCY",  # S&P Emerging Markets
    "MSCIWLD": ".dMIWD00000PUS",  # MSCI World USD
}

# Volatility Indices (Validated 2026-01-07)
VOLATILITY_INDEX_RICS: dict[str, str] = {
    "VIX": ".VIX",  # CBOE VIX (S&P 500)
    "VXD": ".VXD",  # VXD (Dow Jones)
    "VVIX": ".VVIX",  # VVIX (VIX of VIX)
    "VIX9D": ".VIX9D",  # VIX 9-Day
    "VIX3M": ".VIX3M",  # VIX 3-Month
    "VIX6M": ".VIX6M",  # VIX 6-Month
    "VIX1Y": ".VIX1Y",  # VIX 1-Year
    "V2TX": ".V2TX",  # VSTOXX (European)
}


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

# CME Symbol → LSEG RIC Mapping:
#   SR3 (3-Mo SOFR) → SRA
#   SR1 (1-Mo SOFR) → SOFR (access denied, may need permissions)
#   ZQ (Fed Funds)  → FF

STIR_FUTURES_RICS: dict[str, str] = {
    # USD SOFR
    "SOFR_3M": "SRAc1",  # 3-Month SOFR continuous (CME SR3 → LSEG SRA)
    "SOFR_3M_CHAIN": "0#SRA:",  # 3-Month SOFR contract chain
    "SOFR_1M": "SOFRc1",  # 1-Month SOFR continuous (CME SR1 → LSEG SOFR) - ACCESS DENIED
    "SOFR_1M_CHAIN": "0#SOFR:",  # 1-Month SOFR contract chain (snapshot only)
    # Fed Funds
    "FF": "FFc1",  # 30-Day Fed Funds continuous (CME ZQ → LSEG FF)
    "FF_CHAIN": "0#FF:",  # Fed Funds contract chain
    # EUR Euribor
    "EURIBOR_3M": "FEIc1",  # 3-Month Euribor continuous
    "EURIBOR_CHAIN": "0#FEI:",  # Euribor contract chain
    # GBP SONIA
    "SONIA": "SONc1",  # SONIA continuous
}

# CME to LSEG STIR symbol mapping
STIR_CME_TO_LSEG: dict[str, str] = {
    "SR3": "SRA",  # 3-Month SOFR
    "SR1": "SOFR",  # 1-Month SOFR (may need permissions)
    "ZQ": "FF",  # 30-Day Fed Funds
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
# EUR Interest Rate Swaps (Validated 2026-01-06)
# =============================================================================

# Pattern: EURIRS{tenor}=
# Note: Short-end (< 1Y) not available - use EURIBOR for short rates
EUR_IRS_TENORS: list[str] = [
    "1Y",
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
    "40Y",
    "50Y",
]


def get_eur_irs_ric(tenor: str) -> str:
    """Get EUR IRS RIC for tenor."""
    return f"EURIRS{tenor}="


EUR_IRS_FIELDS: list[str] = [
    "BID",
    "ASK",
    "HST_CLOSE",
    "PRIMACT_1",
]


# =============================================================================
# EUR Benchmark Rates (Validated 2026-01-06)
# =============================================================================

# ESTR Fixing
ESTR_FIXING_RIC: str = "EUROSTR="

ESTR_FIELDS: list[str] = [
    "PRIMACT_1",
    "VALUE_DT1",
    "VALUE_TS1",
    "DSPLY_NAME",
]


# =============================================================================
# EURIBOR Fixings (Validated 2026-01-06)
# =============================================================================

# Pattern: EURIBOR{tenor}D=
# Note: 1W not available
EURIBOR_RICS: dict[str, str] = {
    "1M": "EURIBOR1MD=",
    "3M": "EURIBOR3MD=",
    "6M": "EURIBOR6MD=",
    "12M": "EURIBOR1YD=",
}

EURIBOR_FIELDS: list[str] = [
    "PRIMACT_1",
    "VALUE_DT1",
    "VALUE_TS1",
    "DSPLY_NAME",
]


# =============================================================================
# Sovereign Yield Curves (Validated 2026-01-06)
# =============================================================================

# Complete tenor coverage per country
# Pattern: {CC}{tenor}T=RR (except US which uses =RRPS for history)

SOVEREIGN_YIELD_RICS: dict[str, dict[str, str]] = {
    # United States Treasury - 13 tenors
    # Note: =RR works for snapshot, =RRPS needed for some history
    "US": {
        "1M": "US1MT=RR",
        "2M": "US2MT=RR",
        "3M": "US3MT=RR",
        "4M": "US4MT=RR",
        "6M": "US6MT=RR",
        "1Y": "US1YT=RR",
        "2Y": "US2YT=RR",
        "3Y": "US3YT=RR",
        "5Y": "US5YT=RR",
        "7Y": "US7YT=RR",
        "10Y": "US10YT=RR",
        "20Y": "US20YT=RR",
        "30Y": "US30YT=RR",
    },
    # German Bund - 18 tenors (BUBIL short, BUND long)
    "DE": {
        "1M": "DE1MT=RR",
        "3M": "DE3MT=RR",
        "6M": "DE6MT=RR",
        "9M": "DE9MT=RR",
        "1Y": "DE1YT=RR",
        "2Y": "DE2YT=RR",
        "3Y": "DE3YT=RR",
        "4Y": "DE4YT=RR",
        "5Y": "DE5YT=RR",
        "6Y": "DE6YT=RR",
        "7Y": "DE7YT=RR",
        "8Y": "DE8YT=RR",
        "9Y": "DE9YT=RR",
        "10Y": "DE10YT=RR",
        "15Y": "DE15YT=RR",
        "20Y": "DE20YT=RR",
        "25Y": "DE25YT=RR",
        "30Y": "DE30YT=RR",
    },
    # UK Gilt - 20 tenors (T-BILL short, GILT long)
    "GB": {
        "1M": "GB1MT=RR",
        "3M": "GB3MT=RR",
        "6M": "GB6MT=RR",
        "1Y": "GB1YT=RR",
        "2Y": "GB2YT=RR",
        "3Y": "GB3YT=RR",
        "4Y": "GB4YT=RR",
        "5Y": "GB5YT=RR",
        "6Y": "GB6YT=RR",
        "7Y": "GB7YT=RR",
        "8Y": "GB8YT=RR",
        "9Y": "GB9YT=RR",
        "10Y": "GB10YT=RR",
        "12Y": "GB12YT=RR",
        "15Y": "GB15YT=RR",
        "20Y": "GB20YT=RR",
        "25Y": "GB25YT=RR",
        "30Y": "GB30YT=RR",
        "40Y": "GB40YT=RR",
        "50Y": "GB50YT=RR",
    },
    # French OAT - 19 tenors (BTF short, OAT long)
    "FR": {
        "1M": "FR1MT=RR",
        "3M": "FR3MT=RR",
        "6M": "FR6MT=RR",
        "9M": "FR9MT=RR",
        "1Y": "FR1YT=RR",
        "2Y": "FR2YT=RR",
        "3Y": "FR3YT=RR",
        "4Y": "FR4YT=RR",
        "5Y": "FR5YT=RR",
        "6Y": "FR6YT=RR",
        "7Y": "FR7YT=RR",
        "8Y": "FR8YT=RR",
        "9Y": "FR9YT=RR",
        "10Y": "FR10YT=RR",
        "15Y": "FR15YT=RR",
        "20Y": "FR20YT=RR",
        "25Y": "FR25YT=RR",
        "30Y": "FR30YT=RR",
        "50Y": "FR50YT=RR",
    },
    # Italian BTP - 19 tenors (BOT short, BTP long)
    "IT": {
        "1M": "IT1MT=RR",
        "3M": "IT3MT=RR",
        "6M": "IT6MT=RR",
        "9M": "IT9MT=RR",
        "1Y": "IT1YT=RR",
        "2Y": "IT2YT=RR",
        "3Y": "IT3YT=RR",
        "4Y": "IT4YT=RR",
        "5Y": "IT5YT=RR",
        "6Y": "IT6YT=RR",
        "7Y": "IT7YT=RR",
        "8Y": "IT8YT=RR",
        "9Y": "IT9YT=RR",
        "10Y": "IT10YT=RR",
        "15Y": "IT15YT=RR",
        "20Y": "IT20YT=RR",
        "25Y": "IT25YT=RR",
        "30Y": "IT30YT=RR",
        "50Y": "IT50YT=RR",
    },
    # Canadian Government - 13 tenors (T-BILL short, T-BOND long)
    "CA": {
        "1M": "CA1MT=RR",
        "2M": "CA2MT=RR",
        "3M": "CA3MT=RR",
        "6M": "CA6MT=RR",
        "1Y": "CA1YT=RR",
        "2Y": "CA2YT=RR",
        "3Y": "CA3YT=RR",
        "4Y": "CA4YT=RR",
        "5Y": "CA5YT=RR",
        "7Y": "CA7YT=RR",
        "10Y": "CA10YT=RR",
        "20Y": "CA20YT=RR",
        "30Y": "CA30YT=RR",
    },
    # Japanese JGB - Requires additional permissions (access_denied)
    # Pattern JP{tenor}T=RR exists but needs JGB data package
    "JP": {},  # Not available in basic tier
    # Spanish Bono - 18 tenors (T-BILL short, T-BOND long)
    "ES": {
        "1M": "ES1MT=RR",
        "3M": "ES3MT=RR",
        "6M": "ES6MT=RR",
        "9M": "ES9MT=RR",
        "1Y": "ES1YT=RR",
        "2Y": "ES2YT=RR",
        "3Y": "ES3YT=RR",
        "4Y": "ES4YT=RR",
        "5Y": "ES5YT=RR",
        "6Y": "ES6YT=RR",
        "7Y": "ES7YT=RR",
        "8Y": "ES8YT=RR",
        "9Y": "ES9YT=RR",
        "10Y": "ES10YT=RR",
        "15Y": "ES15YT=RR",
        "20Y": "ES20YT=RR",
        "25Y": "ES25YT=RR",
        "30Y": "ES30YT=RR",
    },
    # Netherlands DSL - 16 tenors (DTC short, DSL long)
    "NL": {
        "1M": "NL1MT=RR",
        "3M": "NL3MT=RR",
        "6M": "NL6MT=RR",
        "2Y": "NL2YT=RR",
        "3Y": "NL3YT=RR",
        "4Y": "NL4YT=RR",
        "5Y": "NL5YT=RR",
        "6Y": "NL6YT=RR",
        "7Y": "NL7YT=RR",
        "8Y": "NL8YT=RR",
        "9Y": "NL9YT=RR",
        "10Y": "NL10YT=RR",
        "15Y": "NL15YT=RR",
        "20Y": "NL20YT=RR",
        "25Y": "NL25YT=RR",
        "30Y": "NL30YT=RR",
    },
    # Belgian OLO - 17 tenors (BTC short, OLO long)
    "BE": {
        "3M": "BE3MT=RR",
        "6M": "BE6MT=RR",
        "9M": "BE9MT=RR",
        "1Y": "BE1YT=RR",
        "2Y": "BE2YT=RR",
        "3Y": "BE3YT=RR",
        "4Y": "BE4YT=RR",
        "5Y": "BE5YT=RR",
        "6Y": "BE6YT=RR",
        "7Y": "BE7YT=RR",
        "8Y": "BE8YT=RR",
        "9Y": "BE9YT=RR",
        "10Y": "BE10YT=RR",
        "15Y": "BE15YT=RR",
        "20Y": "BE20YT=RR",
        "30Y": "BE30YT=RR",
        "50Y": "BE50YT=RR",
    },
    # Austrian Government - 18 tenors (BILL short, BUND long)
    "AT": {
        "3M": "AT3MT=RR",
        "6M": "AT6MT=RR",
        "1Y": "AT1YT=RR",
        "2Y": "AT2YT=RR",
        "3Y": "AT3YT=RR",
        "4Y": "AT4YT=RR",
        "5Y": "AT5YT=RR",
        "6Y": "AT6YT=RR",
        "7Y": "AT7YT=RR",
        "8Y": "AT8YT=RR",
        "9Y": "AT9YT=RR",
        "10Y": "AT10YT=RR",
        "15Y": "AT15YT=RR",
        "20Y": "AT20YT=RR",
        "25Y": "AT25YT=RR",
        "30Y": "AT30YT=RR",
        "40Y": "AT40YT=RR",
        "50Y": "AT50YT=RR",
    },
    # Swiss Confederation - 18 tenors (DEPOSIT short, T-BOND long)
    "CH": {
        "1M": "CH1MT=RR",
        "2M": "CH2MT=RR",
        "3M": "CH3MT=RR",
        "6M": "CH6MT=RR",
        "1Y": "CH1YT=RR",
        "2Y": "CH2YT=RR",
        "3Y": "CH3YT=RR",
        "4Y": "CH4YT=RR",
        "5Y": "CH5YT=RR",
        "6Y": "CH6YT=RR",
        "7Y": "CH7YT=RR",
        "8Y": "CH8YT=RR",
        "9Y": "CH9YT=RR",
        "10Y": "CH10YT=RR",
        "15Y": "CH15YT=RR",
        "20Y": "CH20YT=RR",
        "30Y": "CH30YT=RR",
        "40Y": "CH40YT=RR",
    },
    # Australian Government - 14 tenors (T-BOND only, no short end)
    "AU": {
        "1Y": "AU1YT=RR",
        "2Y": "AU2YT=RR",
        "3Y": "AU3YT=RR",
        "4Y": "AU4YT=RR",
        "5Y": "AU5YT=RR",
        "6Y": "AU6YT=RR",
        "7Y": "AU7YT=RR",
        "8Y": "AU8YT=RR",
        "9Y": "AU9YT=RR",
        "10Y": "AU10YT=RR",
        "12Y": "AU12YT=RR",
        "15Y": "AU15YT=RR",
        "20Y": "AU20YT=RR",
        "30Y": "AU30YT=RR",
    },
}

# For backwards compatibility - German Bund
DE_YIELD_TENORS: list[str] = list(SOVEREIGN_YIELD_RICS["DE"].keys())


def get_de_yield_ric(tenor: str) -> str:
    """Get German Bund yield RIC for tenor."""
    return SOVEREIGN_YIELD_RICS["DE"].get(tenor, f"DE{tenor}T=RR")


def get_sovereign_yield_ric(country_code: str, tenor: str) -> str:
    """Get sovereign yield RIC for any supported country and tenor."""
    if country_code in SOVEREIGN_YIELD_RICS:
        return SOVEREIGN_YIELD_RICS[country_code].get(
            tenor, f"{country_code}{tenor}T=RR"
        )
    return f"{country_code}{tenor}T=RR"


def get_sovereign_tenors(country_code: str) -> list[str]:
    """Get available tenors for a country's sovereign yield curve."""
    return list(SOVEREIGN_YIELD_RICS.get(country_code, {}).keys())


SOVEREIGN_YIELD_FIELDS: list[str] = [
    "BID",
    "ASK",
    "HIGH_1",
    "LOW_1",
    "HST_CLOSE",
    "PRIMACT_1",
    "MID_YLD_1",
]


# =============================================================================
# EUR FRAs (Validated 2026-01-06)
# =============================================================================

# Pattern: EUR{tenor}F=
EUR_FRA_TENORS: list[str] = [
    "1X4",
    "2X5",
    "3X6",
    "4X7",
    "5X8",
    "6X9",
    "6X12",
    "9X12",
]


# =============================================================================
# GBP OIS (SONIA-based) - Validated 2026-01-06
# =============================================================================

# Pattern: GBP{tenor}OIS=
# Note: GBP OIS works with bare = pattern (unlike EUR which needs IRS)
GBP_OIS_TENORS: list[str] = [
    "1M",
    "2M",
    "3M",
    "6M",
    "9M",
    "1Y",
    "2Y",
    "3Y",
    "5Y",
    "7Y",
    "10Y",
    "15Y",
    "20Y",
    "30Y",
]


def get_gbp_ois_ric(tenor: str) -> str:
    """Get GBP OIS RIC for tenor."""
    return f"GBP{tenor}OIS="


GBP_OIS_FIELDS: list[str] = [
    "BID",
    "ASK",
    "HST_CLOSE",
    "PRIMACT_1",
]


# =============================================================================
# UK Gilt Yields (Validated 2026-01-06)
# =============================================================================

# Pattern: GB{tenor}T=RR - Full curve (9 tenors)
GB_YIELD_TENORS: list[str] = list(SOVEREIGN_YIELD_RICS["GB"].keys())


def get_gb_yield_ric(tenor: str) -> str:
    """Get UK Gilt yield RIC for tenor."""
    return SOVEREIGN_YIELD_RICS["GB"].get(tenor, f"GB{tenor}T=RR")


# =============================================================================
# GBP FRAs (Validated 2026-01-06)
# =============================================================================

# Pattern: GBP{tenor}F=
GBP_FRA_TENORS: list[str] = [
    "1X4",
    "2X5",
    "3X6",
    "4X7",
    "5X8",
    "6X9",
    "6X12",
    "9X12",
]


# =============================================================================
# Eurozone Sovereign Yields (Validated 2026-01-06)
# =============================================================================

# Pattern: {cc}{tenor}T=RR (all countries use same pattern)
EZ_YIELD_TENORS: list[str] = ["2Y", "5Y", "10Y", "30Y"]

EZ_YIELD_COUNTRIES: dict[str, str] = {
    "DE": "Germany (Bunds)",
    "FR": "France (OATs)",
    "IT": "Italy (BTPs)",
    "ES": "Spain (Bonos)",
    "NL": "Netherlands",
    "BE": "Belgium",
    "AT": "Austria",
    "PT": "Portugal",
    "IE": "Ireland",
    "GR": "Greece",
    "FI": "Finland",
}


def get_ez_yield_ric(country_code: str, tenor: str) -> str:
    """Get Eurozone sovereign yield RIC for country and tenor."""
    return f"{country_code}{tenor}T=RR"


EZ_YIELD_FIELDS: list[str] = [
    "BID",
    "ASK",
    "HIGH_1",
    "LOW_1",
    "HST_CLOSE",
    "PRIMACT_1",
    "MID_YLD_1",
]


# =============================================================================
# G7+ OIS Curves (Validated 2026-01-06)
# =============================================================================

# Pattern: {ccy}{tenor}OIS= works for all major currencies
G7_OIS_CURRENCIES: list[str] = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

G7_OIS_TENORS: list[str] = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"]


def get_g7_ois_ric(currency: str, tenor: str) -> str:
    """Get OIS RIC for any G7 currency and tenor."""
    return f"{currency}{tenor}OIS="


# =============================================================================
# G7+ IRS Curves (Validated 2026-01-06)
# =============================================================================

# Pattern: {ccy}IRS{tenor}= works for most currencies
# USD and EUR confirmed working. GBP uses different pattern: GBPSB6L{tenor}=
G7_IRS_CURRENCIES: list[str] = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

G7_IRS_TENORS: list[str] = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]


def get_g7_irs_ric(currency: str, tenor: str) -> str:
    """Get IRS RIC for G7 currency and tenor.

    Note: GBP uses a different pattern - use get_gbp_irs_ric() instead.
    """
    if currency == "GBP":
        return get_gbp_irs_ric(tenor)
    return f"{currency}IRS{tenor}="


# GBP IRS specific (GBPSB6L pattern confirmed 17/17)
# Pattern: GBPSB6L{tenor}= (GBP Swap vs 6-month SONIA)
GBP_IRS_TENORS: list[str] = [
    "1Y",
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
    "40Y",
    "50Y",
]


def get_gbp_irs_ric(tenor: str) -> str:
    """Get GBP IRS RIC for tenor."""
    return f"GBPSB6L{tenor}="


# USD IRS specific (USDIRS pattern confirmed 10/10)
USD_IRS_TENORS: list[str] = [
    "1Y",
    "2Y",
    "3Y",
    "4Y",
    "5Y",
    "7Y",
    "10Y",
    "15Y",
    "20Y",
    "30Y",
]


def get_usd_irs_ric(tenor: str) -> str:
    """Get USD IRS RIC for tenor."""
    return f"USDIRS{tenor}="


# =============================================================================
# G7+ Government Yields (Validated 2026-01-06)
# =============================================================================

# Pattern: {cc}{tenor}T=RR works for all G7 countries
# See SOVEREIGN_YIELD_RICS for complete tenor coverage per country
G7_GOVT_YIELD_COUNTRIES: dict[str, str] = {
    "US": "United States (13 tenors: 1M-30Y)",
    "GB": "United Kingdom Gilts (9 tenors: 1Y-30Y)",
    "JP": "Japan JGBs (access_denied - requires JGB data package)",
    "DE": "Germany Bunds (9 tenors: 1Y-30Y)",
    "FR": "France OATs (9 tenors: 1Y-30Y)",
    "IT": "Italy BTPs (9 tenors: 1Y-30Y)",
    "ES": "Spain Bonos (4 tenors: 2Y-30Y)",
    "CA": "Canada (8 tenors: 1Y-30Y)",
    "CH": "Switzerland (4 tenors: 2Y-30Y)",
    "AU": "Australia (6 tenors: 2Y-30Y)",
    "NL": "Netherlands DSL (4 tenors: 2Y-30Y)",
    "BE": "Belgium OLO (4 tenors: 2Y-30Y)",
    "AT": "Austria (4 tenors: 2Y-30Y)",
}

# Standard benchmark tenors (minimum coverage)
G7_GOVT_YIELD_TENORS: list[str] = ["2Y", "5Y", "10Y", "30Y"]


def get_govt_yield_ric(country_code: str, tenor: str) -> str:
    """Get government yield RIC for country and tenor.

    Uses SOVEREIGN_YIELD_RICS lookup first, falls back to pattern.
    """
    # Check if we have a validated RIC
    if country_code in SOVEREIGN_YIELD_RICS:
        if tenor in SOVEREIGN_YIELD_RICS[country_code]:
            return SOVEREIGN_YIELD_RICS[country_code][tenor]
    # Fallback to pattern
    return f"{country_code}{tenor}T=RR"


# =============================================================================
# G7+ FRAs (Validated 2026-01-06)
# =============================================================================

# Pattern: {ccy}{tenor}F=
# Note: FRAs only available for USD, EUR, GBP, JPY
FRA_CURRENCIES: list[str] = ["USD", "EUR", "GBP", "JPY"]

FRA_TENORS: list[str] = ["1X4", "3X6", "6X9", "6X12"]


def get_g7_fra_ric(currency: str, tenor: str) -> str:
    """Get FRA RIC for currency and tenor."""
    return f"{currency}{tenor}F="


# =============================================================================
# G7+ Benchmark Rates (Validated 2026-01-06)
# =============================================================================

BENCHMARK_FIXINGS: dict[str, str] = {
    "SOFR": "USDSOFR=",  # USD SOFR fixing
    "ESTR": "EUROSTR=",  # EUR ESTR fixing
    "SARON": "SARON=",  # CHF SARON fixing
    "CORRA": "CORRA=",  # CAD CORRA fixing
    # Note: SONIA (SONIAOSR=) returns access_denied
    # Note: TONA (JPY) not found with standard RICs
}
