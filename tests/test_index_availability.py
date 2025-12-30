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
    def client(self):
        """Create a client instance for the test class."""
        client = LsegClient()
        yield client
        client.close_session()

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
    def test_index_is_queryable(self, client, index_code):
        """Test that each index can be successfully queried."""
        try:
            rics = client.get_index_constituents(index_code)

            # Should return a non-empty list
            assert isinstance(rics, list), f"{index_code} did not return a list"
            assert len(rics) > 0, f"{index_code} returned empty list"

            # All entries should be strings
            assert all(
                isinstance(ric, str) for ric in rics
            ), f"{index_code} contains non-string RICs"

            print(f"✓ {index_code}: {len(rics)} constituents")

        except Exception as e:
            pytest.fail(f"Failed to query {index_code}: {e}")

    def test_us_indices_have_reasonable_sizes(self, client):
        """Test that major US indices return expected number of constituents."""
        expected_ranges = {
            "SPX": (400, 600),  # S&P 500
            "SPCY": (550, 650),  # S&P SmallCap 600
            "NDX": (80, 120),  # Nasdaq 100
            "DJI": (25, 35),  # Dow 30
        }

        for index_code, (min_expected, max_expected) in expected_ranges.items():
            rics = client.get_index_constituents(index_code)
            count = len(rics)

            assert (
                min_expected <= count <= max_expected
            ), f"{index_code} has {count} constituents, expected {min_expected}-{max_expected}"

            print(
                f"✓ {index_code}: {count} constituents (expected {min_expected}-{max_expected})"
            )

    def test_european_indices_have_reasonable_sizes(self, client):
        """Test that major European indices return expected number of constituents."""
        expected_ranges = {
            "FTSE": (80, 120),  # FTSE 100
            "STOXX50E": (40, 60),  # EURO STOXX 50
            "GDAXI": (35, 45),  # DAX 40
            "FCHI": (35, 45),  # CAC 40
            "AEX": (20, 35),  # AEX 25
        }

        for index_code, (min_expected, max_expected) in expected_ranges.items():
            rics = client.get_index_constituents(index_code)
            count = len(rics)

            assert (
                min_expected <= count <= max_expected
            ), f"{index_code} has {count} constituents, expected {min_expected}-{max_expected}"

            print(
                f"✓ {index_code}: {count} constituents (expected {min_expected}-{max_expected})"
            )

    def test_index_with_and_without_prefix(self, client):
        """Test that indices work with or without . prefix."""
        test_indices = ["SPX", "GDAXI", "NDX"]

        for index_code in test_indices:
            # Without prefix
            rics1 = client.get_index_constituents(index_code)

            # With prefix
            rics2 = client.get_index_constituents(f".{index_code}")

            # Should return same results
            assert set(rics1) == set(
                rics2
            ), f"{index_code}: Different results with/without . prefix"

            print(f"✓ {index_code}: Consistent with/without prefix")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
