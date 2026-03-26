#!/usr/bin/env python3
"""Test different Bloomberg swaption ticker formats to find which works."""

import blpapi

# Different possible ticker formats for USD 1Y into 10Y swaption
TEST_TICKERS = [
    # Original format
    "USSV1Y10Y BGN Curncy",
    # Alternative prefixes
    "USSW1Y10Y BGN Curncy",
    "USSO1Y10Y BGN Curncy",
    "USSN1Y10Y BGN Curncy",
    # With spaces/different structure
    "USSV 1Y10Y BGN Curncy",
    "USD1Y10Y BGN Curncy",
    # VCUB format (vol cube)
    "USDSV1Y10Y BGN Curncy",
    # Receiver/payer specific
    "USSV1Y10YR BGN Curncy",
    "USSV1Y10YP BGN Curncy",
    # ATM vol
    "USSV1Y10Y ATMS Curncy",
    "USSV1Y10Y SMKO Curncy",
    # Index format
    "USSV1Y10Y Index",
    # Different source
    "USSV1Y10Y ICAP Curncy",
    "USSV1Y10Y TPIC Curncy",
    "USSV1Y10Y GFI Curncy",
]

FIELDS = ["PX_LAST", "NAME", "SECURITY_TYP"]


def test_tickers():
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

        print("Testing swaption ticker formats...\n")
        print(f"{'Ticker':<35} {'PX_LAST':<12} {'NAME':<40} {'Error'}")
        print("-" * 100)

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
                                except:
                                    px = str(fd.getElement("PX_LAST"))
                            if fd.hasElement("NAME"):
                                name = fd.getElementAsString("NAME")[:40]

                        if sec_data.hasElement("securityError"):
                            err = sec_data.getElement("securityError")
                            error = err.getElementAsString("message")[:30]

                        # Highlight if we got data
                        if px:
                            print(f">>> {ticker:<31} {px:<12} {name:<40} {error}")
                        else:
                            print(f"    {ticker:<31} {px:<12} {name:<40} {error}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    finally:
        session.stop()


if __name__ == "__main__":
    test_tickers()
