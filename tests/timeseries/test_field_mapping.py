from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lseg_toolkit.timeseries.storage.field_mapping import FieldMapper


class TestFieldMapper:
    def test_extract_ohlcv_row_uses_fallbacks(self):
        row = pd.Series(
            {
                "SETTLE": 99.25,
                "ACVOL_UNS": 1234,
                "OPINT_1": 456,
                "session_date": date(2026, 3, 2),
            }
        )

        extracted = FieldMapper.extract_row(row, "ohlcv")

        assert extracted["close"] == 99.25
        assert extracted["settle"] == 99.25
        assert extracted["volume"] == 1234
        assert extracted["open_interest"] == 456
        assert extracted["session_date"] == date(2026, 3, 2)

    def test_extract_quote_row_preserves_quote_specific_columns(self):
        row = pd.Series(
            {
                "BID": 1.0850,
                "ASK": 1.0852,
                "BID_HIGH_1": 1.0860,
                "BID_LOW_1": 1.0840,
                "OPEN_BID": 1.0845,
            }
        )

        extracted = FieldMapper.extract_row(row, "quote")

        assert extracted["bid"] == 1.0850
        assert extracted["ask"] == 1.0852
        assert extracted["bid_high"] == 1.0860
        assert extracted["bid_low"] == 1.0840
        assert extracted["open_bid"] == 1.0845

    def test_extract_rate_row_prefers_primary_rate_field(self):
        row = pd.Series(
            {
                "PRIMACT_1": 4.11,
                "BID": 4.10,
                "ASK": 4.12,
                "BID_HIGH_1": 4.15,
                "BID_LOW_1": 4.05,
            }
        )

        extracted = FieldMapper.extract_row(row, "rate")

        assert extracted["rate"] == 4.11
        assert extracted["bid"] == 4.10
        assert extracted["ask"] == 4.12
        assert extracted["high_rate"] == 4.15
        assert extracted["low_rate"] == 4.05

    def test_extract_bond_row_maps_yield_fields(self):
        row = pd.Series(
            {
                "MID_YLD_1": 4.25,
                "B_YLD_1": 4.24,
                "A_YLD_1": 4.26,
                "OPEN_PRC": 99.5,
                "MOD_DURTN": 8.7,
                "BPV": 0.081,
            }
        )

        extracted = FieldMapper.extract_row(row, "bond")

        assert extracted["yield"] == 4.25
        assert extracted["yield_bid"] == 4.24
        assert extracted["yield_ask"] == 4.26
        assert extracted["open_price"] == 99.5
        assert extracted["mod_duration"] == 8.7
        assert extracted["dv01"] == 0.081

    def test_extract_required_field_raises(self):
        row = pd.Series({"volume": 1000})

        with pytest.raises(ValueError, match="Required field 'close'"):
            FieldMapper.extract_row(row, "ohlcv")

    def test_calculate_mid(self):
        assert FieldMapper.calculate_mid(100.0, 100.5) == 100.25
        assert FieldMapper.calculate_mid(None, 100.5) is None
