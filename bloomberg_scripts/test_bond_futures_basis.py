#!/usr/bin/env python3
"""Test specific bond-futures basis calculations.

The bond basis market is really about specific cash bonds vs futures.
This script tests if we can:
1. Get individual treasury bond data
2. Calculate/retrieve basis for specific bonds vs futures
3. Access bond analytics relevant to basis trading

Usage:
    python test_bond_futures_basis.py
"""

from __future__ import annotations

import blpapi
from datetime import date


# Some on-the-run and off-the-run treasury bonds (approximate - need current issues)
# Format: "ticker Govt" for treasuries
TREASURY_BONDS = {
    # Current benchmark issues (update CUSIPs as needed)
    "2Y Note": "91282CLH3 Govt",   # Recent 2Y
    "5Y Note": "91282CLF7 Govt",   # Recent 5Y
    "10Y Note": "91282CLL4 Govt",  # Recent 10Y
    "30Y Bond": "912810UB6 Govt",  # Recent 30Y

    # Alternative format - by maturity date
    "T 4.25 11/15/34": "T 4.25 11/15/34 Govt",
    "T 4.625 11/15/54": "T 4.625 11/15/54 Govt",
}

# Generic treasury tickers that might work
GENERIC_TREASURIES = {
    "CT2 Govt": "CT2 Govt",    # Current 2Y
    "CT5 Govt": "CT5 Govt",    # Current 5Y
    "CT10 Govt": "CT10 Govt",  # Current 10Y
    "CT30 Govt": "CT30 Govt",  # Current 30Y
}

# Bond fields relevant to basis trading
BOND_FIELDS = [
    "PX_LAST",
    "PX_BID",
    "PX_ASK",
    "NAME",
    "MATURITY",
    "CPN",                    # Coupon
    "DUR_ADJ_MID",           # Duration
    "YLD_YTM_MID",           # Yield to maturity
    "CONV_FACTOR_TY",        # Conversion factor for TY
    "CONV_FACTOR_US",        # Conversion factor for US
    "FUT_BOND_BASIS_TY",     # Basis vs TY future
    "FUT_BOND_BASIS_US",     # Basis vs US future
    "FUT_BOND_IMPLIED_REPO", # Implied repo
]

# Additional basis-specific fields to try
BASIS_ANALYTICS_FIELDS = [
    "BASIS_NET",
    "BASIS_GROSS",
    "IMPLIED_REPO_RATE",
    "CARRY",
    "ROLL",
    "SWITCH_VALUE",
]


def test_generic_treasuries():
    """Test generic treasury tickers (CT2, CT5, CT10, CT30)."""
    print("\n" + "=" * 80)
    print("TEST 1: Generic Treasury Tickers")
    print("=" * 80)

    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("ERROR: Could not start Bloomberg session")
            return

        if not session.openService("//blp/refdata"):
            print("ERROR: Could not open refdata service")
            return

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for ticker in GENERIC_TREASURIES.values():
            request.append("securities", ticker)

        fields = ["PX_LAST", "NAME", "MATURITY", "CPN", "YLD_YTM_MID"]
        for field in fields:
            request.append("fields", field)

        session.sendRequest(request)

        results = {}
        while True:
            event = session.nextEvent(10000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_array = msg.getElement("securityData")
                    for i in range(sec_array.numValues()):
                        sec = sec_array.getValue(i)
                        ticker = sec.getElementAsString("security")
                        results[ticker] = {"fields": {}, "error": None}

                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            for field in fields:
                                if fd.hasElement(field):
                                    try:
                                        results[ticker]["fields"][field] = fd.getElement(field).getValue()
                                    except Exception:
                                        results[ticker]["fields"][field] = str(fd.getElement(field))

                        if sec.hasElement("securityError"):
                            results[ticker]["error"] = sec.getElement("securityError").getElementAsString("message")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        # Print results
        for name, ticker in GENERIC_TREASURIES.items():
            r = results.get(ticker, {})
            if r.get("error"):
                print(f"\n{name} ({ticker}): ERROR - {r['error']}")
            else:
                f = r.get("fields", {})
                print(f"\n{name} ({ticker}):")
                print(f"  Price: {f.get('PX_LAST', 'N/A')}")
                print(f"  Name: {f.get('NAME', 'N/A')}")
                print(f"  Maturity: {f.get('MATURITY', 'N/A')}")
                print(f"  Coupon: {f.get('CPN', 'N/A')}")
                print(f"  YTM: {f.get('YLD_YTM_MID', 'N/A')}")

    finally:
        session.stop()


def test_conversion_factors():
    """Test if we can get conversion factors for deliverable bonds."""
    print("\n" + "=" * 80)
    print("TEST 2: Bond Conversion Factors")
    print("=" * 80)
    print("\nConversion factors link cash bond prices to futures prices.")
    print("If available, we can calculate basis ourselves.")

    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("ERROR: Could not start Bloomberg session")
            return

        if not session.openService("//blp/refdata"):
            print("ERROR: Could not open refdata service")
            return

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        # Test with generic current 10Y
        test_bonds = ["CT10 Govt", "CT5 Govt", "CT30 Govt"]
        for ticker in test_bonds:
            request.append("securities", ticker)

        conv_factor_fields = [
            "PX_LAST",
            "NAME",
            "MATURITY",
            # Various conversion factor field attempts
            "CONV_FACTOR",
            "FUT_CONV_FACTOR",
            "FUT_TY_CONV_FACTOR",
            "FUT_US_CONV_FACTOR",
            "FUT_CNVS_FACTOR",
            "DELIVERY_CONV_FACTOR",
        ]

        for field in conv_factor_fields:
            request.append("fields", field)

        session.sendRequest(request)

        while True:
            event = session.nextEvent(10000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_array = msg.getElement("securityData")
                    for i in range(sec_array.numValues()):
                        sec = sec_array.getValue(i)
                        ticker = sec.getElementAsString("security")
                        print(f"\n{ticker}:")

                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            for field in conv_factor_fields:
                                if fd.hasElement(field):
                                    val = fd.getElement(field).getValue()
                                    print(f"  {field}: {val}")

                        if sec.hasElement("fieldExceptions"):
                            fe = sec.getElement("fieldExceptions")
                            print("  Field exceptions:")
                            for j in range(min(5, fe.numValues())):
                                exc = fe.getValue(j)
                                field_id = exc.getElementAsString("fieldId")
                                print(f"    {field_id}: not available")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


def test_override_for_basis():
    """Test using overrides to get basis for specific futures contract."""
    print("\n" + "=" * 80)
    print("TEST 3: Override-Based Basis Query")
    print("=" * 80)
    print("\nTrying to get basis using overrides to specify futures contract...")

    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("ERROR: Could not start Bloomberg session")
            return

        if not session.openService("//blp/refdata"):
            print("ERROR: Could not open refdata service")
            return

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        # Query a treasury bond
        request.append("securities", "CT10 Govt")

        # Fields that might give basis info
        request.append("fields", "PX_LAST")
        request.append("fields", "NAME")
        request.append("fields", "BASIS_NET")
        request.append("fields", "IMPLIED_REPO_RATE")
        request.append("fields", "GROSS_BASIS")

        # Try override to specify which futures contract
        overrides = request.getElement("overrides")
        override = overrides.appendElement()
        override.setElement("fieldId", "FUTURES_TICKER")
        override.setElement("value", "TYH6 Comdty")

        session.sendRequest(request)

        while True:
            event = session.nextEvent(10000)
            for msg in event:
                print(f"\nResponse message:")
                if msg.hasElement("securityData"):
                    sec_array = msg.getElement("securityData")
                    for i in range(sec_array.numValues()):
                        sec = sec_array.getValue(i)
                        ticker = sec.getElementAsString("security")
                        print(f"\n{ticker}:")

                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            num_fields = fd.numElements()
                            for j in range(num_fields):
                                elem = fd.getElement(j)
                                print(f"  {elem.name()}: {elem.getValue()}")

                        if sec.hasElement("fieldExceptions"):
                            fe = sec.getElement("fieldExceptions")
                            for j in range(fe.numValues()):
                                exc = fe.getValue(j)
                                print(f"  Exception: {exc.getElementAsString('fieldId')}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


def test_dlv_type_query():
    """Test alternative DLV-style queries."""
    print("\n" + "=" * 80)
    print("TEST 4: DLV-Style Basket Query on Futures")
    print("=" * 80)

    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("ERROR: Could not start Bloomberg session")
            return

        if not session.openService("//blp/refdata"):
            print("ERROR: Could not open refdata service")
            return

        service = session.getService("//blp/refdata")

        # Try bulk data request for deliverable basket
        request = service.createRequest("ReferenceDataRequest")
        request.append("securities", "TYH6 Comdty")

        # These are bulk fields that might return array data
        bulk_fields = [
            "FUT_DELIVERABLE_BONDS",
            "FUT_DLV_BASKET",
            "DELIVERY_BASKET",
            "DELIVERABLE_BASKET",
            "DLVBL_BONDS",
        ]

        for field in bulk_fields:
            request.append("fields", field)

        session.sendRequest(request)

        print("\nTrying bulk fields for deliverable basket on TYH6 Comdty:")

        while True:
            event = session.nextEvent(10000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_array = msg.getElement("securityData")
                    for i in range(sec_array.numValues()):
                        sec = sec_array.getValue(i)

                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            for field in bulk_fields:
                                if fd.hasElement(field):
                                    elem = fd.getElement(field)
                                    print(f"\n  {field}:")
                                    if elem.isArray():
                                        for j in range(min(10, elem.numValues())):
                                            print(f"    [{j}] {elem.getValue(j)}")
                                    else:
                                        print(f"    {elem.getValue()}")

                        if sec.hasElement("fieldExceptions"):
                            fe = sec.getElement("fieldExceptions")
                            print("\n  Field exceptions:")
                            for j in range(fe.numValues()):
                                exc = fe.getValue(j)
                                print(f"    {exc.getElementAsString('fieldId')}: not found")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


def test_yield_curve_treasuries():
    """Test getting full treasury yield curve data."""
    print("\n" + "=" * 80)
    print("TEST 5: Treasury Yield Curve")
    print("=" * 80)

    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("ERROR: Could not start Bloomberg session")
            return

        if not session.openService("//blp/refdata"):
            print("ERROR: Could not open refdata service")
            return

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        # US Treasury yield curve tickers
        yield_tickers = [
            "USGG3M Index",   # 3M
            "USGG6M Index",   # 6M
            "USGG12M Index",  # 1Y
            "USGG2YR Index",  # 2Y
            "USGG3YR Index",  # 3Y
            "USGG5YR Index",  # 5Y
            "USGG7YR Index",  # 7Y
            "USGG10YR Index", # 10Y
            "USGG30YR Index", # 30Y
        ]

        for ticker in yield_tickers:
            request.append("securities", ticker)
        request.append("fields", "PX_LAST")
        request.append("fields", "NAME")

        session.sendRequest(request)

        print("\nUS Treasury Yield Curve:")

        results = {}
        while True:
            event = session.nextEvent(10000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_array = msg.getElement("securityData")
                    for i in range(sec_array.numValues()):
                        sec = sec_array.getValue(i)
                        ticker = sec.getElementAsString("security")
                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            if fd.hasElement("PX_LAST"):
                                results[ticker] = fd.getElementAsFloat("PX_LAST")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        for ticker in yield_tickers:
            yld = results.get(ticker, "N/A")
            label = ticker.replace("USGG", "").replace(" Index", "")
            if isinstance(yld, float):
                print(f"  {label:>4}: {yld:.3f}%")
            else:
                print(f"  {label:>4}: {yld}")

    finally:
        session.stop()


def main():
    """Run all bond-futures basis tests."""
    print("=" * 80)
    print("Bloomberg Bond-Futures Basis Analysis Test")
    print("=" * 80)
    print("\nThis script explores bond-futures basis data at the individual bond level.")

    test_generic_treasuries()
    test_conversion_factors()
    test_override_for_basis()
    test_dlv_type_query()
    test_yield_curve_treasuries()

    print("\n" + "=" * 80)
    print("CONCLUSIONS & NEXT STEPS")
    print("=" * 80)
    print("""
WHAT WE'RE LOOKING FOR:
  - Conversion factors for each deliverable bond
  - Net basis = Cash Price - (Futures Price × Conversion Factor)
  - Implied repo rate for each bond in the basket
  - CTD identification (lowest net basis or highest implied repo)

IF API DOESN'T PROVIDE BASIS DIRECTLY:
  1. Get futures price (PX_LAST on TY1 Comdty)
  2. Get cash bond prices (CT10 Govt or specific CUSIPs)
  3. Get/calculate conversion factors
  4. Calculate basis manually: Basis = Bond Price - (Futures × CF)

TERMINAL-ONLY FUNCTIONS:
  - DLV: Full deliverable basket with all basis analytics
  - BBA: Bond basis analysis with carry calculations
  - CDSW: Cash-deliverable switch

For historical basket composition, track:
  - Treasury issuance dates (new bonds entering basket)
  - Maturity requirements (6.5-10 year remaining for TY)
  - Contract roll dates
""")


if __name__ == "__main__":
    main()
