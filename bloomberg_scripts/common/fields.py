"""Bloomberg field definitions for each instrument type."""

# Swaption fields
SWAPTION_FIELDS = [
    "PX_LAST",           # Last price (implied vol in %)
    "PX_BID",            # Bid volatility
    "PX_ASK",            # Ask volatility
    "PX_MID",            # Mid volatility
    "LAST_UPDATE_DT",    # Last update date
    "IVOL_DELTA",        # Delta
]

# Cap/Floor fields
CAP_FLOOR_FIELDS = [
    "PX_LAST",           # Last price (implied vol)
    "PX_BID",
    "PX_ASK",
    "LAST_UPDATE_DT",
    "CAP_VOL_STRIKE",    # Cap strike rate
]

# JGB Yield fields
JGB_FIELDS = [
    "PX_LAST",           # Yield to maturity
    "PX_BID",
    "PX_ASK",
    "YLD_YTM_MID",       # Yield to maturity (mid)
    "DURATION",          # Modified duration
    "CONVEXITY",         # Convexity
    "LAST_UPDATE_DT",
]

# FX Option fields (risk reversals and butterflies)
FX_OPTION_FIELDS = [
    "PX_LAST",           # Implied vol
    "PX_BID",
    "PX_ASK",
    "PX_MID",
    "IVOL_DELTA",        # Delta
    "LAST_UPDATE_DT",
]

# Common tenors and expiries
SWAPTION_EXPIRIES = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"]
SWAPTION_TENORS = ["2Y", "5Y", "10Y", "30Y"]

CAP_TENORS = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y"]
CAP_STRIKES = ["A", "+50", "+100", "+150", "+200"]  # ATM and OTM strikes

JGB_TENORS = ["2", "5", "10", "20", "30", "40"]

FX_TENORS = ["1W", "1M", "3M", "6M", "1Y", "2Y"]
FX_PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "AUDUSD"]

# Currency prefixes for swaptions
SWAPTION_CURRENCY_PREFIXES = {
    "USD": "USSV",
    "EUR": "EUSV",
    "GBP": "BPSV",
    "JPY": "JYSV",
    "CHF": "SFSV",
    "AUD": "ADSV",
}

# Currency prefixes for caps
CAP_CURRENCY_PREFIXES = {
    "USD": "USCP",
    "EUR": "EUCP",
    "GBP": "BPCP",
}

# Rate type mapping for caps
CAP_RATE_TYPES = {
    "SOFR": "",       # Default for USD
    "ESTR": "",       # Default for EUR
    "SONIA": "",      # Default for GBP
}
