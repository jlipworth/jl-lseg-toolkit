"""Tests for LSEG client."""

import pytest

from lseg_toolkit.client import LsegClient


class TestLsegClient:
    """Test cases for LsegClient."""

    def test_client_initialization(self):
        """Test client can be initialized."""
        client = LsegClient(auto_open=False)
        assert client is not None
        assert not client._session_opened

    @pytest.mark.integration
    def test_client_auto_open(self):
        """Test client with auto_open parameter."""
        # Note: This requires LSEG Workspace to be running
        client = LsegClient(auto_open=True)
        assert client._session_opened
        client.close_session()

    # TODO: Add tests for:
    # - get_index_constituents
    # - get_company_data
    # - get_earnings_data
    # - get_financial_ratios
