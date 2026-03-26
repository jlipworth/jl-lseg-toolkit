"""Legacy / research interest rate caps/floors extraction.

This package is retained for Bloomberg ticker discovery and failed-pattern archaeology.
"""

from .extract import (
    extract_caps_floors_historical,
    extract_caps_floors_snapshot,
    generate_cap_floor_tickers,
    run_caps_floors_extraction,
)

__all__ = [
    "extract_caps_floors_historical",
    "extract_caps_floors_snapshot",
    "generate_cap_floor_tickers",
    "run_caps_floors_extraction",
]
