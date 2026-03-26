#!/usr/bin/env python3
"""Test FX vol tickers - V pattern discovered."""

import blpapi

# EURUSDV pattern works - test more tenors and pairs
TEST_TICKERS = [
    # EURUSD ATM Vol - V pattern (confirmed working)
    "EURUSDV1W BGN Curncy",
    "EURUSDV1M BGN Curncy",
    "EURUSDV2M BGN Curncy",
    "EURUSDV3M BGN Curncy",
    "EURUSDV6M BGN Curncy",
    "EURUSDV9M BGN Curncy",
    "EURUSDV1Y BGN Curncy",
    "EURUSDV2Y BGN Curncy",

    # USDJPY ATM Vol - try V pattern
    "USDJPYV1M BGN Curncy",
    "USDJPYV3M BGN Curncy",
    "USDJPYV1Y BGN Curncy",

    # GBPUSD ATM Vol
    "GBPUSDV1M BGN Curncy",
    "GBPUSDV3M BGN Curncy",

    # AUDUSD ATM Vol
    "AUDUSDV1M BGN Curncy",

    # USDCHF ATM Vol
    "USDCHFV1M BGN Curncy",

    # USDCAD ATM Vol
    "USDCADV1M BGN Curncy",

    # Try RR with V pattern
    "EURUSDRR1M BGN Curncy",
    "EURUSDVRR1M BGN Curncy",
    "EURUSD25RR1M BGN Curncy",
    "EURUSDV1M25R BGN Curncy",

    # Try BF with V pattern
    "EURUSDBF1M BGN Curncy",
    "EURUSDVBF1M BGN Curncy",
    "EURUSD25BF1M BGN Curncy",
]

FIELDS = ["PX_LAST", "NAME"]


def test():
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

        print(f"{'Ticker':<35} {'PX_LAST':<12} {'NAME'}")
        print("-" * 90)

        working = []
        failed = []

        while True:
            event = session.nextEvent(10000)

            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data_array = msg.getElement("securityData")

                    for i in range(sec_data_array.numValues()):
                        sec_data = sec_data_array.getValue(i)
                        ticker = sec_data.getElementAsString("security")

                        px = None
                        name = ""

                        if sec_data.hasElement("fieldData"):
                            fd = sec_data.getElement("fieldData")
                            if fd.hasElement("PX_LAST"):
                                try:
                                    px = fd.getElementAsFloat("PX_LAST")
                                except:
                                    pass
                            if fd.hasElement("NAME"):
                                name = fd.getElementAsString("NAME")

                        if px is not None:
                            working.append((ticker, px, name))
                            print(f"✅ {ticker:<33} {px:<12.4f} {name}")
                        else:
                            failed.append(ticker)
                            print(f"❌ {ticker:<33}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        print(f"\n{'='*90}")
        print(f"WORKING: {len(working)} | FAILED: {len(failed)}")

    finally:
        session.stop()


if __name__ == "__main__":
    test()
