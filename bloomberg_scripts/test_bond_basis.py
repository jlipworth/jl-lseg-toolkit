#!/usr/bin/env python3
"""Test Bloomberg bond basis and deliverable basket data for Treasury futures.

This script explores:
1. Treasury futures contracts (TY, US, FV, TU, WN, UXY)
2. Bond basis market data (CTD, basis, net basis, implied repo)
3. Deliverable basket data and historical availability

Usage:
    python test_bond_basis.py
"""

from __future__ import annotations

import blpapi
from datetime import date, timedelta


# Treasury futures contracts - front month generic tickers
TREASURY_FUTURES = {
    "2Y Note (TU)": "TU1 Comdty",      # 2-Year Treasury Note
    "5Y Note (FV)": "FV1 Comdty",      # 5-Year Treasury Note
    "10Y Note (TY)": "TY1 Comdty",     # 10-Year Treasury Note
    "Ultra 10Y (UXY)": "UXY1 Comdty",  # Ultra 10-Year Treasury Note
    "T-Bond (US)": "US1 Comdty",       # Treasury Bond (classic long bond)
    "Ultra Bond (WN)": "WN1 Comdty",   # Ultra Treasury Bond
}

# Active contract tickers (specific month - March 2026)
ACTIVE_CONTRACTS = {
    "TY Mar26": "TYH6 Comdty",
    "US Mar26": "USH6 Comdty",
    "FV Mar26": "FVH6 Comdty",
    "TU Mar26": "TUH6 Comdty",
}

# Basic futures fields
BASIC_FIELDS = [
    "PX_LAST",
    "NAME",
    "FUT_CONT_SIZE",
    "FUT_FIRST_TRADE_DT",
    "LAST_TRADEABLE_DT",
    "FUT_DLV_DT_FIRST",
    "FUT_DLV_DT_LAST",
]

# Bond basis / CTD related fields (may or may not work via API)
BASIS_FIELDS = [
    "FUT_CTD_ISIN",           # CTD bond ISIN
    "FUT_CTD_CUSIP",          # CTD bond CUSIP
    "FUT_CTD_TICKER",         # CTD bond ticker
    "FUT_CTD_CONV_FACTOR",    # CTD conversion factor
    "FUT_CTD_NET_BASIS",      # CTD net basis
    "FUT_CTD_GROSS_BASIS",    # CTD gross basis
    "FUT_CTD_IMPLIED_REPO",   # CTD implied repo rate
    "FUT_DLVRY_BSKT_SIZE",    # Number of bonds in basket
    "CHEAPEST_TO_DELIVER",    # CTD identifier
    "IMPLIED_REPO_RATE",      # Implied repo
]

# Deliverable basket fields (bulk data)
BASKET_FIELDS = [
    "FUT_DLVRBL_BNDS_CUSIP",    # All deliverable bonds CUSIPs
    "FUT_DLVRBL_BNDS_TICKER",   # All deliverable bonds tickers
    "FUT_DLVRBL_BNDS_ISIN",     # All deliverable bonds ISINs
    "FUT_DLVRBL_BNDS_CONV_FAC", # Conversion factors
]

# Additional analytics fields
ANALYTICS_FIELDS = [
    "FUT_DLVRY_CTD_TICKER",
    "FUT_DLVRY_CTD_CUSIP",
    "DELIVERY_BASKET",
    "BASIS_NET",
    "BASIS_GROSS",
]


def test_basic_futures_data():
    """Test basic futures data retrieval."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Treasury Futures Data")
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

        all_tickers = list(TREASURY_FUTURES.values()) + list(ACTIVE_CONTRACTS.values())
        for ticker in all_tickers:
            request.append("securities", ticker)
        for field in BASIC_FIELDS:
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
                            for field in BASIC_FIELDS:
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
        for desc, ticker in {**TREASURY_FUTURES, **ACTIVE_CONTRACTS}.items():
            r = results.get(ticker, {})
            if r.get("error"):
                print(f"\n{desc} ({ticker}): ERROR - {r['error']}")
            else:
                fields = r.get("fields", {})
                px = fields.get("PX_LAST", "N/A")
                name = fields.get("NAME", "N/A")
                print(f"\n{desc} ({ticker}):")
                print(f"  Price: {px}")
                print(f"  Name: {name}")
                for f in BASIC_FIELDS[2:]:  # Skip PX_LAST and NAME
                    if f in fields and fields[f]:
                        print(f"  {f}: {fields[f]}")

    finally:
        session.stop()


def test_basis_fields():
    """Test CTD and basis related fields."""
    print("\n" + "=" * 80)
    print("TEST 2: Bond Basis / CTD Fields")
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

        # Test on TY1 (10Y generic) and TYH6 (specific contract)
        test_tickers = ["TY1 Comdty", "TYH6 Comdty", "US1 Comdty"]
        for ticker in test_tickers:
            request.append("securities", ticker)
        for field in BASIS_FIELDS + ANALYTICS_FIELDS:
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
                        results[ticker] = {"fields": {}, "errors": []}

                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            for field in BASIS_FIELDS + ANALYTICS_FIELDS:
                                if fd.hasElement(field):
                                    try:
                                        results[ticker]["fields"][field] = fd.getElement(field).getValue()
                                    except Exception:
                                        results[ticker]["fields"][field] = str(fd.getElement(field))

                        if sec.hasElement("fieldExceptions"):
                            fe = sec.getElement("fieldExceptions")
                            for j in range(fe.numValues()):
                                exc = fe.getValue(j)
                                field_id = exc.getElementAsString("fieldId")
                                err_info = exc.getElement("errorInfo")
                                err_msg = err_info.getElementAsString("message")
                                results[ticker]["errors"].append(f"{field_id}: {err_msg}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        # Print results
        for ticker in test_tickers:
            r = results.get(ticker, {})
            fields = r.get("fields", {})
            errors = r.get("errors", [])

            print(f"\n{ticker}:")
            print("  Working fields:")
            for field, value in fields.items():
                if value is not None:
                    print(f"    {field}: {value}")

            if not fields:
                print("    (none)")

            if errors:
                print("  Field errors (first 5):")
                for err in errors[:5]:
                    print(f"    {err}")

    finally:
        session.stop()


def test_deliverable_basket():
    """Test deliverable basket bulk data retrieval."""
    print("\n" + "=" * 80)
    print("TEST 3: Deliverable Basket (Bulk Data)")
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

        request.append("securities", "TYH6 Comdty")
        for field in BASKET_FIELDS:
            request.append("fields", field)

        session.sendRequest(request)

        print("\nQuerying TYH6 Comdty for deliverable basket fields...")

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
                            for field in BASKET_FIELDS:
                                if fd.hasElement(field):
                                    elem = fd.getElement(field)
                                    print(f"\n  {field}:")
                                    if elem.isArray():
                                        for j in range(min(5, elem.numValues())):  # First 5
                                            print(f"    [{j}] {elem.getValue(j)}")
                                        if elem.numValues() > 5:
                                            print(f"    ... and {elem.numValues() - 5} more")
                                    else:
                                        print(f"    {elem.getValue()}")

                        if sec.hasElement("fieldExceptions"):
                            fe = sec.getElement("fieldExceptions")
                            print("\n  Field exceptions:")
                            for j in range(fe.numValues()):
                                exc = fe.getValue(j)
                                field_id = exc.getElementAsString("fieldId")
                                print(f"    {field_id}: not available")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


def test_historical_basket():
    """Test historical deliverable basket / basis data."""
    print("\n" + "=" * 80)
    print("TEST 4: Historical Data (Futures price history)")
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
        request = service.createRequest("HistoricalDataRequest")

        request.append("securities", "TY1 Comdty")
        request.append("fields", "PX_LAST")

        # Last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        request.set("startDate", start_date.strftime("%Y%m%d"))
        request.set("endDate", end_date.strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")

        session.sendRequest(request)

        print(f"\nHistorical TY1 prices ({start_date} to {end_date}):")

        while True:
            event = session.nextEvent(10000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    ticker = sec_data.getElementAsString("security")

                    if sec_data.hasElement("fieldData"):
                        fd = sec_data.getElement("fieldData")
                        for i in range(min(10, fd.numValues())):  # Show first 10
                            row = fd.getValue(i)
                            dt = row.getElementAsDatetime("date")
                            px = row.getElementAsFloat("PX_LAST")
                            print(f"  {dt}: {px:.4f}")

                        if fd.numValues() > 10:
                            print(f"  ... ({fd.numValues()} total data points)")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


def test_ctd_historical():
    """Test if CTD fields can be retrieved historically."""
    print("\n" + "=" * 80)
    print("TEST 5: Historical CTD / Basis Fields")
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
        request = service.createRequest("HistoricalDataRequest")

        request.append("securities", "TY1 Comdty")

        # Try these fields historically
        hist_basis_fields = [
            "FUT_CTD_IMPLIED_REPO",
            "FUT_CTD_NET_BASIS",
            "FUT_CTD_GROSS_BASIS",
        ]

        for field in hist_basis_fields:
            request.append("fields", field)

        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        request.set("startDate", start_date.strftime("%Y%m%d"))
        request.set("endDate", end_date.strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")

        session.sendRequest(request)

        print(f"\nHistorical basis fields for TY1 ({start_date} to {end_date}):")

        while True:
            event = session.nextEvent(10000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")

                    if sec_data.hasElement("fieldData"):
                        fd = sec_data.getElement("fieldData")
                        if fd.numValues() > 0:
                            print("\n  Date | Implied Repo | Net Basis | Gross Basis")
                            print("  " + "-" * 55)
                            for i in range(min(10, fd.numValues())):
                                row = fd.getValue(i)
                                dt = row.getElementAsDatetime("date")
                                vals = []
                                for field in hist_basis_fields:
                                    if row.hasElement(field):
                                        vals.append(f"{row.getElementAsFloat(field):.4f}")
                                    else:
                                        vals.append("N/A")
                                print(f"  {dt} | {vals[0]:>12} | {vals[1]:>9} | {vals[2]:>11}")
                        else:
                            print("  No historical data returned for these fields")

                    if sec_data.hasElement("fieldExceptions"):
                        fe = sec_data.getElement("fieldExceptions")
                        print("\n  Field exceptions:")
                        for j in range(fe.numValues()):
                            exc = fe.getValue(j)
                            field_id = exc.getElementAsString("fieldId")
                            print(f"    {field_id}: not available historically")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


def test_field_search():
    """Search for DLV-related fields using field search."""
    print("\n" + "=" * 80)
    print("TEST 6: Field Search (DLV/BASIS/CTD related)")
    print("=" * 80)
    print("\nNote: Field search requires //blp/apiflds service")

    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("ERROR: Could not start Bloomberg session")
            return

        # Try to open the field info service
        if not session.openService("//blp/apiflds"):
            print("Could not open //blp/apiflds service")
            print("Field search not available via API")
            return

        service = session.getService("//blp/apiflds")

        # Search for fields containing "DLV" or "BASIS"
        for search_term in ["DLV", "CTD", "BASIS", "DELIVERABLE"]:
            request = service.createRequest("FieldSearchRequest")
            request.set("searchSpec", search_term)

            session.sendRequest(request)

            print(f"\nSearching for fields containing '{search_term}':")

            while True:
                event = session.nextEvent(10000)
                for msg in event:
                    if msg.hasElement("fieldData"):
                        fd = msg.getElement("fieldData")
                        count = 0
                        for i in range(fd.numValues()):
                            if count >= 10:  # Limit output
                                break
                            field = fd.getValue(i)
                            # Field search returns different element names
                            try:
                                field_id = field.getElementAsString("id")
                                # Try different possible element names
                                if field.hasElement("mnemonic"):
                                    mnemonic = field.getElementAsString("mnemonic")
                                elif field.hasElement("fieldMnemonic"):
                                    mnemonic = field.getElementAsString("fieldMnemonic")
                                else:
                                    mnemonic = field_id
                                if field.hasElement("description"):
                                    desc = field.getElementAsString("description")[:50]
                                elif field.hasElement("fieldDescription"):
                                    desc = field.getElementAsString("fieldDescription")[:50]
                                else:
                                    desc = ""
                                print(f"  {mnemonic}: {desc}")
                                count += 1
                            except Exception as e:
                                # Print raw field structure to understand format
                                print(f"  Field {i}: {field}")
                                count += 1
                        if fd.numValues() > 10:
                            print(f"  ... and {fd.numValues() - 10} more")

                if event.eventType() == blpapi.Event.RESPONSE:
                    break

    finally:
        session.stop()


def main():
    """Run all bond basis tests."""
    print("=" * 80)
    print("Bloomberg Bond Basis & Deliverable Basket Test")
    print("=" * 80)
    print("\nThis script tests Bloomberg API access to:")
    print("  1. Treasury futures basic data")
    print("  2. CTD (cheapest-to-deliver) and basis fields")
    print("  3. Deliverable basket composition")
    print("  4. Historical futures data")
    print("  5. Historical CTD/basis fields")
    print("  6. Field search for related fields")

    # Run tests
    test_basic_futures_data()
    test_basis_fields()
    test_deliverable_basket()
    test_historical_basket()
    test_ctd_historical()
    test_field_search()

    print("\n" + "=" * 80)
    print("SUMMARY & NOTES")
    print("=" * 80)
    print("""
Key findings will show which of these work via API:

1. BASIC FUTURES DATA: Should work (PX_LAST, contract dates, etc.)

2. CTD/BASIS FIELDS: May work for snapshot data. Look for:
   - FUT_CTD_TICKER: Identifies the cheapest-to-deliver bond
   - FUT_CTD_CONV_FACTOR: Conversion factor
   - FUT_CTD_IMPLIED_REPO: Implied repo rate
   - FUT_CTD_NET_BASIS: Net basis in 32nds

3. DELIVERABLE BASKET: Bulk fields (FUT_DLVRBL_BNDS_*) may provide
   the full basket composition.

4. HISTORICAL DATA: Basic price history should work.
   Historical CTD/basis may require terminal-only DLV function.

TERMINAL ALTERNATIVES (if API doesn't work):
   - DLV <GO>: Full deliverable basket with basis analytics
   - CDSW <GO>: Cash-deliverable switch analysis
   - BBA <GO>: Bond basis analysis

If you need historical basket composition, you may need to:
   1. Track issuance dates and maturity requirements
   2. Reconstruct eligible bonds for each historical date
   3. Pull basis data for specific bond-futures pairs
""")


if __name__ == "__main__":
    main()
