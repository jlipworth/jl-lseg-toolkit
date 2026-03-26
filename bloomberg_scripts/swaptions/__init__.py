"""Legacy / research swaption volatility extraction.

This package is retained for Bloomberg Desktop API discovery work only.
"""

from .extract import extract_swaption_surface
from .tickers import generate_swaption_tickers

__all__ = ["generate_swaption_tickers", "extract_swaption_surface"]
