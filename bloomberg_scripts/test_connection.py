#!/usr/bin/env python3
"""Standalone Bloomberg connection test script.

Just copy this single file and run:
    python test_connection.py

Or in IPython:
    %run ~/Downloads/test_connection.py
"""

from __future__ import annotations

import sys


def test_blpapi_import():
    """Test that blpapi is installed."""
    print("1. Testing blpapi import...", end=" ")
    try:
        import blpapi
        version = getattr(blpapi, "__version__", "installed")
        print(f"OK ({version})")
        return True
    except ImportError as e:
        print(f"FAILED\n   Error: {e}")
        print("   Install with: pip install blpapi")
        return False


def test_pandas_import():
    """Test that pandas is installed."""
    print("2. Testing pandas import...", end=" ")
    try:
        import pandas as pd
        print(f"OK ({pd.__version__})")
        return True
    except ImportError as e:
        print(f"FAILED\n   Error: {e}")
        return False


def test_pyarrow_import():
    """Test that pyarrow is installed."""
    print("3. Testing pyarrow import...", end=" ")
    try:
        import pyarrow as pa
        print(f"OK ({pa.__version__})")
        return True
    except ImportError as e:
        print(f"FAILED\n   Error: {e}")
        print("   Install with: pip install pyarrow")
        return False


def test_bloomberg_connection():
    """Test Bloomberg Terminal connection with a simple query."""
    print("4. Testing Bloomberg connection...", end=" ")

    import blpapi

    # Session options
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("FAILED (could not start session)")
            print("   Make sure Bloomberg Terminal is running!")
            return False

        if not session.openService("//blp/refdata"):
            print("FAILED (could not open refdata service)")
            return False

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")
        request.append("securities", "IBM US Equity")
        request.append("fields", "PX_LAST")
        request.append("fields", "NAME")

        session.sendRequest(request)

        # Process response
        name = None
        price = None

        while True:
            event = session.nextEvent(5000)

            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData").getValue(0)
                    if sec_data.hasElement("fieldData"):
                        field_data = sec_data.getElement("fieldData")
                        if field_data.hasElement("PX_LAST"):
                            price = field_data.getElementAsFloat("PX_LAST")
                        if field_data.hasElement("NAME"):
                            name = field_data.getElementAsString("NAME")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        if price is not None:
            print("OK")
            print(f"   Test: IBM US Equity")
            print(f"   Name: {name}")
            print(f"   Price: {price}")
            return True
        else:
            print("FAILED (no data returned)")
            return False

    except Exception as e:
        print(f"FAILED\n   Error: {e}")
        return False
    finally:
        session.stop()


def test_swaption_ticker():
    """Test swaption ticker generation."""
    print("5. Testing ticker generation...", end=" ")

    # Inline ticker generation (no package import needed)
    CURRENCY_PREFIXES = {
        "USD": "USSV",
        "EUR": "EUSV",
        "GBP": "BPSV",
    }

    currency = "USD"
    expiry = "1Y"
    tenor = "10Y"

    prefix = CURRENCY_PREFIXES[currency]
    ticker = f"{prefix}{expiry}{tenor} BGN Curncy"
    expected = "USSV1Y10Y BGN Curncy"

    if ticker == expected:
        print("OK")
        print(f"   Sample: {ticker}")
        return True
    else:
        print(f"FAILED (got {ticker})")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Bloomberg Connection Test")
    print("=" * 60)
    print()

    results = []

    # Import tests
    blpapi_ok = test_blpapi_import()
    results.append(("blpapi import", blpapi_ok))
    results.append(("pandas import", test_pandas_import()))
    results.append(("pyarrow import", test_pyarrow_import()))

    # Ticker test (no deps)
    results.append(("ticker generation", test_swaption_ticker()))

    # Bloomberg connection (only if blpapi works)
    if blpapi_ok:
        results.append(("Bloomberg connection", test_bloomberg_connection()))

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    print()
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\nAll tests passed! Ready to extract data.")
        return 0
    else:
        print("\nFix issues above before extracting data.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
