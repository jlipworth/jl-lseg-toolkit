#!/usr/bin/env python3
"""Test swaption NVOL pattern based on terminal discovery."""

import blpapi

# Pattern found: "EUR SWPT NVOL 1Y10Y"
# Try variations for EUR and USD
TEST_TICKERS = [
    # EUR patterns based on discovery
    "EUR SWPT NVOL 1Y10Y Curncy",
    "EURSWPTNVOL1Y10Y Curncy",
    "EURSWPTNVOL1Y10Y BGN Curncy",
    "EUR SWPT NVOL 1Y10Y BGN Curncy",
    "EURSWPTNVOL 1Y10Y Curncy",
    "EURSWNVOL1Y10Y Curncy",
    "EURSWNVOL1Y10Y BGN Curncy",
    "EURSWPTNNVOL1Y10Y Curncy",

    # With different spacing
    "EURSWPT NVOL 1Y10Y Curncy",
    "EUR SWPTNVOL 1Y10Y Curncy",
    "EUR SWPTNVOL1Y10Y Curncy",

    # USD equivalents
    "USD SWPT NVOL 1Y10Y Curncy",
    "USDSWPTNVOL1Y10Y Curncy",
    "USDSWPTNVOL1Y10Y BGN Curncy",
    "USD SWPT NVOL 1Y10Y BGN Curncy",
    "USDSWNVOL1Y10Y Curncy",
    "USDSWNVOL1Y10Y BGN Curncy",

    # Try BVOL (Black vol) vs NVOL (Normal vol)
    "EUR SWPT BVOL 1Y10Y Curncy",
    "EURSWPTBVOL1Y10Y Curncy",
    "USD SWPT BVOL 1Y10Y Curncy",
    "USDSWPTBVOL1Y10Y Curncy",

    # Try without SWPT
    "EUR NVOL 1Y10Y Curncy",
    "EURNVOL1Y10Y Curncy",
    "USD NVOL 1Y10Y Curncy",
    "USDNVOL1Y10Y Curncy",

    # Try Index instead of Curncy
    "EURSWPTNVOL1Y10Y Index",
    "EUR SWPT NVOL 1Y10Y Index",
    "USDSWPTNVOL1Y10Y Index",
    "USD SWPT NVOL 1Y10Y Index",

    # GBP for completeness
    "GBP SWPT NVOL 1Y10Y Curncy",
    "GBPSWPTNVOL1Y10Y Curncy",
    "GBPSWPTNVOL1Y10Y BGN Curncy",

    # Different tenor formats
    "EURSWPTNVOL1YX10Y Curncy",
    "EURSWPTNVOL01Y10Y Curncy",
    "EUR SWPT NVOL 1Yx10Y Curncy",
]

FIELDS = ["PX_LAST", "NAME", "SECURITY_TYP"]


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

        print("Testing swaption NVOL patterns...")
        print(f"{'Ticker':<45} {'PX_LAST':<12} {'NAME'}")
        print("-" * 100)

        working = []

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
                            print(f"✅ {ticker:<43} {px:<12.4f} {name}")
                        else:
                            print(f"❌ {ticker:<43}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        print(f"\n{'='*100}")
        print(f"WORKING: {len(working)}")
        if working:
            print("\n*** WORKING TICKERS: ***")
            for t, p, n in working:
                print(f"  {t} = {p} ({n})")

    finally:
        session.stop()


if __name__ == "__main__":
    test()
