"""
Field mapping from LSEG API field names to normalized storage columns.

This module provides the FieldMapper class which handles the translation
between LSEG's field names (TRDPRC_1, ACVOL_UNS, etc.) and our normalized
column names (close, volume, etc.) with fallback chains.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class FieldMapping:
    """Single field mapping with fallback chain."""

    target: str  # Our column name
    sources: list[str]  # LSEG field names (priority order)
    required: bool = False  # Raise if not found?
    transform: Callable[[Any], Any] | None = None  # Optional transform

    def extract(self, row: pd.Series) -> Any:
        """Extract value from row using fallback chain."""
        for source in self.sources:
            value = row.get(source)
            if value is not None and not pd.isna(value):
                return self.transform(value) if self.transform else value

        if self.required:
            raise ValueError(f"Required field '{self.target}' not found in row")
        return None


class FieldMapper:
    """Registry of field mappings by data shape."""

    OHLCV = [
        FieldMapping("open", ["open", "OPEN_PRC"]),
        FieldMapping("high", ["high", "HIGH_1"]),
        FieldMapping("low", ["low", "LOW_1"]),
        FieldMapping(
            "close",
            ["close", "mid", "last", "settle", "SETTLE", "TRDPRC_1"],
            required=True,
        ),
        FieldMapping("volume", ["volume", "ACVOL_UNS"]),
        FieldMapping("settle", ["settle", "SETTLE"]),
        FieldMapping("open_interest", ["open_interest", "OPINT_1"]),
        FieldMapping("bid", ["bid", "BID"]),
        FieldMapping("ask", ["ask", "ASK"]),
        FieldMapping("mid", ["mid", "MID_PRICE"]),
        FieldMapping("implied_rate", ["implied_rate", "IMP_YIELD"]),
        FieldMapping("session_date", ["session_date"]),
        FieldMapping("vwap", ["vwap", "VWAP"]),
    ]

    QUOTE = [
        FieldMapping("bid", ["bid", "BID"]),
        FieldMapping("ask", ["ask", "ASK"]),
        FieldMapping("mid", ["mid", "MID_PRICE"]),
        FieldMapping("open_bid", ["open_bid", "OPEN_BID"]),
        FieldMapping("bid_high", ["bid_high", "BID_HIGH_1"]),
        FieldMapping("bid_low", ["bid_low", "BID_LOW_1"]),
        FieldMapping("open_ask", ["open_ask", "OPEN_ASK"]),
        FieldMapping("ask_high", ["ask_high", "ASK_HIGH_1"]),
        FieldMapping("ask_low", ["ask_low", "ASK_LOW_1"]),
        FieldMapping("forward_points", ["forward_points", "FWD_POINTS"]),
    ]

    RATE = [
        FieldMapping("rate", ["rate", "PRIMACT_1", "MID_PRICE", "HST_CLOSE", "BID"]),
        FieldMapping("bid", ["bid", "BID"]),
        FieldMapping("ask", ["ask", "ASK"]),
        FieldMapping("open_rate", ["open_rate", "OPEN_BID"]),
        FieldMapping("high_rate", ["high_rate", "BID_HIGH_1"]),
        FieldMapping("low_rate", ["low_rate", "BID_LOW_1"]),
        FieldMapping("rate_2", ["rate_2", "GV1_RATE"]),
        FieldMapping("spread", ["spread"]),
    ]

    BOND = [
        FieldMapping(
            "price", ["price", "MID_PRICE", "CLEAN_PRC", "HST_CLOSE", "PRIMACT_1"]
        ),
        FieldMapping("bid", ["bid", "BID"]),
        FieldMapping("ask", ["ask", "ASK"]),
        FieldMapping("open_price", ["open_price", "MID_OPEN", "OPEN_PRC"]),
        FieldMapping("yield", ["yield", "MID_YLD_1", "B_YLD_1"], required=True),
        FieldMapping("yield_bid", ["yield_bid", "B_YLD_1"]),
        FieldMapping("yield_ask", ["yield_ask", "A_YLD_1"]),
        FieldMapping("open_yield", ["open_yield", "OPEN_YLD"]),
        FieldMapping("yield_high", ["yield_high", "HIGH_YLD"]),
        FieldMapping("yield_low", ["yield_low", "LOW_YLD"]),
        FieldMapping("dirty_price", ["dirty_price", "DIRTY_PRC"]),
        FieldMapping("accrued_interest", ["accrued_interest", "ACCR_INT"]),
        FieldMapping("mod_duration", ["mod_duration", "MOD_DURTN"]),
        FieldMapping("mac_duration", ["mac_duration", "MAC_DURTN"]),
        FieldMapping("convexity", ["convexity", "CONVEXITY"]),
        FieldMapping("dv01", ["dv01", "BPV"]),
        FieldMapping("z_spread", ["z_spread", "ZSPREAD"]),
        FieldMapping("oas", ["oas", "OAS_BID"]),
    ]

    FIXING = [
        FieldMapping("value", ["value", "FIXING_1", "PRIMACT_1", "mid", "MID_PRICE"]),
        FieldMapping("volume", ["volume", "ACVOL_UNS"]),
    ]

    @classmethod
    def get_mappings(cls, data_shape: str) -> list[FieldMapping]:
        """Get field mappings for a data shape."""
        return getattr(cls, data_shape.upper(), cls.OHLCV)

    @classmethod
    def extract_row(cls, row: pd.Series, data_shape: str) -> dict[str, Any]:
        """Extract all mapped fields from a row."""
        mappings = cls.get_mappings(data_shape)
        return {m.target: m.extract(row) for m in mappings}

    @classmethod
    def calculate_mid(cls, bid: Any, ask: Any) -> float | None:
        """Calculate mid from bid/ask if both available."""
        if bid is not None and ask is not None:
            if not pd.isna(bid) and not pd.isna(ask):
                return (float(bid) + float(ask)) / 2
        return None
