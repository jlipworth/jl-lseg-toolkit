"""
Bloomberg support package (partial / unvalidated).

This package contains the repo's Bloomberg workflows — currently JGB yields and FX ATM
implied vol. These have been probed against a live Terminal but have not been validated
end-to-end since the feature landed on master, so treat behavior as experimental and
report divergence as an issue.

Research/probe utilities remain outside the package surface in ``bloomberg_scripts/``.
See ``docs/instruments/BLOOMBERG.md`` and ``docs/BLOOMBERG_LIVE_VALIDATION_RUNBOOK.md``.
"""

from lseg_toolkit.bloomberg.fx_atm_vol import (
    DEFAULT_PAIRS,
    DEFAULT_TENORS,
    FX_ATM_VOL_QUOTE_TYPE,
    FX_ATM_VOL_SOURCE,
    extract_fx_atm_vol_historical,
    extract_fx_atm_vol_snapshot,
    generate_fx_atm_vol_tickers,
)
from lseg_toolkit.bloomberg.jgb import (
    JGB_CURRENCY,
    JGB_INSTRUMENT,
    JGB_SOURCE,
    JGB_TICKERS,
    extract_jgb_historical,
    extract_jgb_snapshot,
    get_jgb_tickers,
)

__all__ = [
    "DEFAULT_PAIRS",
    "DEFAULT_TENORS",
    "FX_ATM_VOL_QUOTE_TYPE",
    "FX_ATM_VOL_SOURCE",
    "JGB_CURRENCY",
    "JGB_INSTRUMENT",
    "JGB_SOURCE",
    "JGB_TICKERS",
    "extract_fx_atm_vol_historical",
    "extract_fx_atm_vol_snapshot",
    "extract_jgb_historical",
    "extract_jgb_snapshot",
    "generate_fx_atm_vol_tickers",
    "get_jgb_tickers",
]
