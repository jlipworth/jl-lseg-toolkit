"""Legacy / research FX options extraction (RR/BF).

Use `bbg-extract fx-atm-vol` for the supported Bloomberg FX vol workflow.
"""

from .extract import (
    DEFAULT_PAIRS,
    DEFAULT_TENORS,
    extract_fx_options_historical,
    extract_fx_options_snapshot,
    generate_fx_option_tickers,
    run_fx_options_extraction,
)

__all__ = [
    "DEFAULT_PAIRS",
    "DEFAULT_TENORS",
    "extract_fx_options_historical",
    "extract_fx_options_snapshot",
    "generate_fx_option_tickers",
    "run_fx_options_extraction",
]
