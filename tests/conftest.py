"""
Shared pytest fixtures for all tests.

This module provides common test fixtures to reduce boilerplate across test files.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lseg_toolkit.client import LsegClient

# ============================================================================
# Client Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def lseg_client_session():
    """
    Session-scoped LSEG client (shared across all tests in session).

    Use this for read-only operations to minimize session overhead.
    The client is created once and reused for all tests.
    """
    client = LsegClient()
    yield client
    client.close_session()


@pytest.fixture(scope="class")
def lseg_client_class():
    """
    Class-scoped LSEG client (shared across tests in a class).

    Use this for test classes that need a fresh client but want to
    share it across multiple test methods.
    """
    client = LsegClient()
    yield client
    client.close_session()


@pytest.fixture(scope="function")
def lseg_client():
    """
    Function-scoped LSEG client (new client for each test).

    Use this when tests need isolation or modify client state.
    """
    client = LsegClient()
    yield client
    client.close_session()


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_tickers_us():
    """Sample US tickers for testing."""
    return ["AAPL.O", "MSFT.O", "GOOGL.O"]


@pytest.fixture
def sample_tickers_global():
    """Sample global tickers for testing."""
    return [
        "AAPL.O",  # US
        "BP.L",  # UK
        "7203.T",  # Japan (Toyota)
    ]


@pytest.fixture
def sample_ticker_single():
    """Single ticker for quick tests."""
    return "AAPL.O"


# ============================================================================
# Date Fixtures
# ============================================================================


@pytest.fixture
def current_week_dates():
    """Get current week's Monday-Sunday date range."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    return {
        "start_date": monday.strftime("%Y-%m-%d"),
        "end_date": sunday.strftime("%Y-%m-%d"),
        "monday": monday,
        "sunday": sunday,
    }


@pytest.fixture
def snapshot_date():
    """
    Get snapshot date (Sunday before current week).

    This matches the logic in EarningsConfig for weekly reports.
    """
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday - timedelta(days=1)

    return sunday.strftime("%Y-%m-%d")


@pytest.fixture
def past_date_range():
    """Get a date range in the past (for historical data tests)."""
    end_date = datetime(2025, 10, 1)
    start_date = end_date - timedelta(days=7)

    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }


# ============================================================================
# Index Fixtures
# ============================================================================


@pytest.fixture
def major_indices():
    """List of major indices for testing."""
    return ["SPX", "NDX", "DJI", "STOXX", "FTSE"]


@pytest.fixture
def small_index():
    """A small index for faster tests (Dow 30)."""
    return "DJI"


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def default_timezone():
    """Default timezone for earnings reports."""
    return "US/Eastern"


# ============================================================================
# Markers
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires LSEG API)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )
