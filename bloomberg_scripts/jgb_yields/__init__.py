"""Legacy / research JGB yields extraction.

Use `bbg-extract jgb` for the supported Bloomberg JGB workflow.
"""

from .extract import (
    JGB_TICKERS,
    extract_jgb_yields_historical,
    extract_jgb_yields_snapshot,
    get_jgb_tickers,
    run_jgb_extraction,
)

__all__ = [
    "JGB_TICKERS",
    "extract_jgb_yields_historical",
    "extract_jgb_yields_snapshot",
    "get_jgb_tickers",
    "run_jgb_extraction",
]
