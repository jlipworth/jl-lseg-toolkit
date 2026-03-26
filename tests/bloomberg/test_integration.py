import os
from importlib.util import find_spec

import pytest

from lseg_toolkit.bloomberg.fx_atm_vol import extract_fx_atm_vol_snapshot
from lseg_toolkit.bloomberg.jgb import extract_jgb_snapshot

pytestmark = pytest.mark.integration


def _integration_enabled() -> bool:
    return os.getenv("RUN_BLOOMBERG_INTEGRATION") == "1"


def _blpapi_available() -> bool:
    return find_spec("blpapi") is not None


@pytest.mark.skipif(
    not _integration_enabled(),
    reason="Set RUN_BLOOMBERG_INTEGRATION=1 to run Bloomberg Desktop API tests.",
)
@pytest.mark.skipif(not _blpapi_available(), reason="blpapi is not installed.")
def test_jgb_snapshot_smoke():
    df = extract_jgb_snapshot(["10Y"])
    assert not df.empty
    assert {"tenor", "ticker"}.issubset(df.columns)


@pytest.mark.skipif(
    not _integration_enabled(),
    reason="Set RUN_BLOOMBERG_INTEGRATION=1 to run Bloomberg Desktop API tests.",
)
@pytest.mark.skipif(not _blpapi_available(), reason="blpapi is not installed.")
def test_fx_atm_vol_snapshot_smoke():
    df = extract_fx_atm_vol_snapshot(pairs=["EURUSD"], tenors=["1M"])
    assert not df.empty
    assert {"pair", "tenor", "ticker"}.issubset(df.columns)
