"""
Test that all listed indices are actually available via LSEG API.

This test verifies each index in the available_indices list can be queried
successfully through the LSEG API.

These tests require LSEG Workspace Desktop running.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lseg_toolkit.client import LsegClient  # noqa: E402

pytestmark = pytest.mark.integration  # Skip in CI


class TestIndexAvailability:
    """Test that all listed indices are queryable."""

    @pytest.fixture(scope="class")
    def all_indices(self):
        """Get all available indices."""
        return LsegClient.get_available_indices()

    def test_all_indices_have_required_fields(self, all_indices):
        """Test that all indices have required metadata fields."""
        required_fields = ["name", "region", "description"]

        for code, info in all_indices.items():
            for field in required_fields:
                assert field in info, f"Index {code} missing field: {field}"
                assert info[field], f"Index {code} has empty {field}"

    @pytest.mark.parametrize(
        "index_code",
        [
            "SPX",
            "SPCY",
            "NDX",
            "DJI",  # US
            "STOXX50E",
            "FTSE",
            "GDAXI",
            "FCHI",
            "AEX",  # Europe
            "N225",
            "HSI",  # Asia
            "GSPTSE",  # Canada
        ],
    )
    def test_index_is_queryable(self, lseg_client_class, index_code):
        """Test that each index can be successfully queried."""
        try:
            rics = lseg_client_class.get_index_constituents(index_code)

            assert isinstance(rics, list), f"{index_code} did not return a list"
            assert len(rics) > 0, f"{index_code} returned empty list"

            assert all(isinstance(ric, str) for ric in rics), (
                f"{index_code} contains non-string RICs"
            )

            print(f"✓ {index_code}: {len(rics)} constituents")

        except Exception as e:
            pytest.fail(f"Failed to query {index_code}: {e}")

    @pytest.mark.parametrize(
        "index_code,min_expected,max_expected",
        [
            ("SPX", 400, 600),  # S&P 500
            ("SPCY", 550, 650),  # S&P SmallCap 600
            ("NDX", 80, 120),  # Nasdaq 100
            ("DJI", 25, 35),  # Dow 30
        ],
        ids=["SPX", "SPCY", "NDX", "DJI"],
    )
    def test_us_index_size(self, lseg_client_class, index_code, min_expected, max_expected):
        """Test that US index returns expected number of constituents."""
        rics = lseg_client_class.get_index_constituents(index_code)
        count = len(rics)

        assert min_expected <= count <= max_expected, (
            f"{index_code} has {count} constituents, expected {min_expected}-{max_expected}"
        )

    @pytest.mark.parametrize(
        "index_code,min_expected,max_expected",
        [
            ("FTSE", 80, 120),  # FTSE 100
            ("STOXX50E", 40, 60),  # EURO STOXX 50
            ("GDAXI", 35, 45),  # DAX 40
            ("FCHI", 35, 45),  # CAC 40
            ("AEX", 20, 35),  # AEX 25
        ],
        ids=["FTSE", "STOXX50E", "GDAXI", "FCHI", "AEX"],
    )
    def test_european_index_size(self, lseg_client_class, index_code, min_expected, max_expected):
        """Test that European index returns expected number of constituents."""
        rics = lseg_client_class.get_index_constituents(index_code)
        count = len(rics)

        assert min_expected <= count <= max_expected, (
            f"{index_code} has {count} constituents, expected {min_expected}-{max_expected}"
        )

    @pytest.mark.parametrize("index_code", ["SPX", "GDAXI", "NDX"])
    def test_index_prefix_consistency(self, lseg_client_class, index_code):
        """Test that indices work with or without . prefix."""
        rics1 = lseg_client_class.get_index_constituents(index_code)
        rics2 = lseg_client_class.get_index_constituents(f".{index_code}")

        assert set(rics1) == set(rics2), (
            f"{index_code}: Different results with/without . prefix"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
