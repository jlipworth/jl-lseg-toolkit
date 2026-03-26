#!/usr/bin/env python3
"""Test all instrument types we planned to extract."""

import blpapi

# All instruments from our plan
TEST_INSTRUMENTS = {
    # JGB Yields - these should work
    "JGB 2Y": "GJGB2 Index",
    "JGB 5Y": "GJGB5 Index",
    "JGB 10Y": "GJGB10 Index",
    "JGB 30Y": "GJGB30 Index",

    # FX Risk Reversals
    "EURUSD 1M 25D RR": "EURUSD1M25RR BGN Curncy",
    "USDJPY 1M 25D RR": "USDJPY1M25RR BGN Curncy",
    "EURUSD 3M 25D RR": "EURUSD3M25RR BGN Curncy",

    # FX Butterflies
    "EURUSD 1M 25D BF": "EURUSD1M25BF BGN Curncy",
    "USDJPY 1M 25D BF": "USDJPY1M25BF BGN Curncy",

    # Alternative FX vol formats
    "EUR 1M RR": "EUR1MRR BGN Curncy",
    "EUR 1M BF": "EUR1MBF BGN Curncy",
    "JPY 1M RR": "JPY1MRR BGN Curncy",

    # Caps/Floors - various formats
    "USD 5Y Cap ATM": "USCP5YA ICAP Curncy",
    "USD 5Y Cap +150": "USCP5Y+150 ICAP Curncy",
    "EUR 5Y Cap ATM": "EUCP5YA ICAP Curncy",

    # Alternative cap formats
    "USD SOFR Cap 5Y": "USDSRCAP5Y ICAP Curncy",
    "USD Cap Vol 5Y": "USCPVOL5Y BGN Curncy",

    # Swaption alternatives
    "USD Swap Vol 1Y10Y": "USSV1Y10Y Curncy",
    "USD Swaption 1Y10Y": "USSWPTN1Y10Y BGN Curncy",

    # Known working instruments for comparison
    "IBM Equity": "IBM US Equity",
    "SPX Index": "SPX Index",
    "US 10Y Yield": "USGG10YR Index",
    "EUR 10Y Swap": "EUSA10 Curncy",
    "USD 10Y Swap": "USSW10 Curncy",
    "VIX": "VIX Index",

    # SOFR
    "SOFR": "SOFRRATE Index",
    "SOFR OIS 1Y": "USOSFR1 Curncy",
}

FIELDS = ["PX_LAST", "NAME"]


def test_all():
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        session.start()
        session.openService("//blp/refdata")

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for ticker in TEST_INSTRUMENTS.values():
            request.append("securities", ticker)
        for field in FIELDS:
            request.append("fields", field)

        session.sendRequest(request)

        results = {}

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
                        error = ""

                        if sec_data.hasElement("fieldData"):
                            fd = sec_data.getElement("fieldData")
                            if fd.hasElement("PX_LAST"):
                                try:
                                    px = fd.getElementAsFloat("PX_LAST")
                                except:
                                    px = str(fd.getElement("PX_LAST"))
                            if fd.hasElement("NAME"):
                                name = fd.getElementAsString("NAME")

                        if sec_data.hasElement("securityError"):
                            err = sec_data.getElement("securityError")
                            error = err.getElementAsString("message")

                        results[ticker] = {"px": px, "name": name, "error": error}

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        # Print results grouped by success/failure
        print("\n" + "=" * 80)
        print("WORKING INSTRUMENTS")
        print("=" * 80)

        working = []
        failed = []

        for desc, ticker in TEST_INSTRUMENTS.items():
            r = results.get(ticker, {})
            if r.get("px") is not None:
                working.append((desc, ticker, r))
            else:
                failed.append((desc, ticker, r))

        for desc, ticker, r in working:
            print(f"  {desc:<25} {ticker:<30} = {r['px']}")
            if r['name']:
                print(f"  {'':<25} Name: {r['name'][:50]}")

        print("\n" + "=" * 80)
        print("FAILED INSTRUMENTS")
        print("=" * 80)

        for desc, ticker, r in failed:
            err = r.get('error', 'No data')[:40]
            print(f"  {desc:<25} {ticker:<30} - {err}")

        print("\n" + "=" * 80)
        print(f"SUMMARY: {len(working)} working, {len(failed)} failed")
        print("=" * 80)

    finally:
        session.stop()


if __name__ == "__main__":
    test_all()
