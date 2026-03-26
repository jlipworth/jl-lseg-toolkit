#!/usr/bin/env python3
"""Debug FX vol / RR-BF ticker patterns - research only.

See `docs/BLOOMBERG_SCRIPTS.md` for the current research playbook.
"""

import blpapi

from bloomberg_scripts._legacy import legacy_surface_message

# Test various FX vol ticker formats
TEST_TICKERS = [
    # EURUSD - confirmed working pattern
    "EURUSD1M25RR BGN Curncy",
    "EURUSD1M10RR BGN Curncy",
    "EURUSD1M25BF BGN Curncy",
    "EURUSD3M25RR BGN Curncy",
    "EURUSD6M25RR BGN Curncy",
    "EURUSD1Y25RR BGN Curncy",

    # USDJPY - try different formats
    "USDJPY1M25RR BGN Curncy",
    "JPYUSD1M25RR BGN Curncy",
    "JPY1M25RR BGN Curncy",
    "USDJPY1MRR25 BGN Curncy",
    "USDJPY25RR1M BGN Curncy",

    # GBPUSD
    "GBPUSD1M25RR BGN Curncy",
    "GBPUSD1M25BF BGN Curncy",
    "GBP1M25RR BGN Curncy",

    # Alternative EUR formats
    "EUR1M25RR BGN Curncy",
    "EUR1MRR25 BGN Curncy",
    "EURUSD1MRR BGN Curncy",
    "EURUSDV1M BGN Curncy",

    # ATM vol (different from RR/BF)
    "EURUSD1M BGN Curncy",
    "EURUSDV1M BGN Curncy",
    "EURUSD1MATM BGN Curncy",
    "EUR1MO= BGN Curncy",
]

FIELDS = ["PX_LAST", "NAME"]


def test():
    print(
        legacy_surface_message(
            "test_fx_tickers.py",
            note=(
                "This script is research-only and should not be treated as the supported Bloomberg interface."
            ),
        )
    )
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        session.start()
        session.openService("//blp/refdata")

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for ticker in TEST_TICKERS:
            request.append("securities", ticker)
        for field in FIELDS:
            request.append("fields", field)

        session.sendRequest(request)

        print(f"{'Ticker':<35} {'PX_LAST':<12} {'NAME':<40}")
        print("-" * 90)

        while True:
            event = session.nextEvent(10000)

            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data_array = msg.getElement("securityData")

                    for i in range(sec_data_array.numValues()):
                        sec_data = sec_data_array.getValue(i)
                        ticker = sec_data.getElementAsString("security")

                        px = ""
                        name = ""
                        error = ""

                        if sec_data.hasElement("fieldData"):
                            fd = sec_data.getElement("fieldData")
                            if fd.hasElement("PX_LAST"):
                                try:
                                    px = f"{fd.getElementAsFloat('PX_LAST'):.4f}"
                                except Exception:
                                    px = str(fd.getElement("PX_LAST"))
                            if fd.hasElement("NAME"):
                                name = fd.getElementAsString("NAME")[:40]

                        if sec_data.hasElement("securityError"):
                            error = "INVALID"

                        if px:
                            print(f"✅ {ticker:<33} {px:<12} {name}")
                        else:
                            print(f"❌ {ticker:<33} {'':<12} {error}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


if __name__ == "__main__":
    test()
