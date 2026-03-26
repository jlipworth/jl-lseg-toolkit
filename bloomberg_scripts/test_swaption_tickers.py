#!/usr/bin/env python3
"""Comprehensive swaption vol ticker search - research only.

See `docs/BLOOMBERG_SCRIPTS.md` for the current research playbook.
"""

import blpapi

from bloomberg_scripts._legacy import legacy_surface_message

# Try every pattern variation we can think of
TEST_TICKERS = [
    # Pattern 1: Similar to FX vol (V pattern) - most promising given FX success
    "USDSWV1Y10Y BGN Curncy",
    "USDSV1Y10Y BGN Curncy",
    "USDIRV1Y10Y BGN Curncy",
    "USDV1Y10Y BGN Curncy",
    "USDSWAPV1Y10Y BGN Curncy",

    # Pattern 2: USSW base (swap rate prefix)
    "USSWV1Y10Y BGN Curncy",
    "USSWVOL1Y10Y BGN Curncy",
    "USSW1Y10YV BGN Curncy",

    # Pattern 3: Swaption specific
    "USSOPT1Y10Y BGN Curncy",
    "USSWOPT1Y10Y BGN Curncy",
    "USSWPTN1Y10Y BGN Curncy",
    "USSWPTNV1Y10Y BGN Curncy",

    # Pattern 4: Vol suffix variations
    "US1Y10YV BGN Curncy",
    "US1Y10YVOL BGN Curncy",
    "USD1Y10YV BGN Curncy",
    "USD1Y10YVOL BGN Curncy",

    # Pattern 5: Normal vol (N) vs Black vol (B/L)
    "USSN1Y10Y BGN Curncy",
    "USSL1Y10Y BGN Curncy",
    "USSB1Y10Y BGN Curncy",
    "USSNVOL1Y10Y BGN Curncy",

    # Pattern 6: ATM specific
    "USSVATM1Y10Y BGN Curncy",
    "USSWATM1Y10Y BGN Curncy",
    "USD1Y10YATM BGN Curncy",
    "USATMSW1Y10Y BGN Curncy",

    # Pattern 7: Index suffix
    "USSV1Y10Y Index",
    "USSWV1Y10Y Index",
    "USSWVOL1Y10Y Index",
    "USDSV1Y10Y Index",

    # Pattern 8: Different source (ICAP, GFI, etc)
    "USSV1Y10Y ICAP Curncy",
    "USSV1Y10Y GFI Curncy",
    "USSV1Y10Y TPIC Curncy",
    "USSWVOL1Y10Y ICAP Curncy",

    # Pattern 9: Receiver/Payer
    "USSV1Y10YR BGN Curncy",
    "USSV1Y10YP BGN Curncy",
    "USSWV1Y10YR BGN Curncy",
    "USSWV1Y10YP BGN Curncy",

    # Pattern 10: Underscore/space variations
    "USS_V_1Y10Y BGN Curncy",
    "USS V 1Y10Y BGN Curncy",
    "USSV 1Y 10Y BGN Curncy",

    # Pattern 11: Different tenor formats
    "USSV1Y-10Y BGN Curncy",
    "USSV1YX10Y BGN Curncy",
    "USSV1Yx10Y BGN Curncy",
    "USSV01Y10Y BGN Curncy",

    # Pattern 12: SOFR-based swaptions
    "USSOFRSV1Y10Y BGN Curncy",
    "USSOFRV1Y10Y BGN Curncy",
    "SOFRSV1Y10Y BGN Curncy",
    "USOSFRSV1Y10Y BGN Curncy",

    # Pattern 13: EUR swaptions (maybe different pattern)
    "EURSV1Y10Y BGN Curncy",
    "EURSWV1Y10Y BGN Curncy",
    "EUSWV1Y10Y BGN Curncy",
    "EUSV1Y10Y BGN Curncy",

    # Pattern 14: Comdty yellow key (some vols use this)
    "USSV1Y10Y Comdty",
    "USSWVOL1Y10Y Comdty",

    # Pattern 15: BVOL prefix (Bloomberg vol?)
    "BVOLUSSW1Y10Y BGN Curncy",
    "BVOLUSD1Y10Y BGN Curncy",

    # Pattern 16: Simple numeric
    "USSWVOL110 BGN Curncy",
    "USSWV110 BGN Curncy",
    "USSV0110 BGN Curncy",
]

FIELDS = ["PX_LAST", "NAME", "SECURITY_TYP"]


def test():
    print(
        legacy_surface_message(
            "test_swaption_tickers.py",
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

        print("Testing swaption vol ticker patterns...")
        print(f"{'Ticker':<35} {'PX_LAST':<12} {'NAME'}")
        print("-" * 90)

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
                                except Exception:
                                    pass
                            if fd.hasElement("NAME"):
                                name = fd.getElementAsString("NAME")

                        if px is not None:
                            working.append((ticker, px, name))
                            print(f"✅ {ticker:<33} {px:<12.4f} {name}")
                        else:
                            print(f"❌ {ticker:<33}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        print(f"\n{'='*90}")
        print(f"WORKING: {len(working)}")
        if working:
            print("\nWorking tickers:")
            for t, p, n in working:
                print(f"  {t} = {p} ({n})")

    finally:
        session.stop()


if __name__ == "__main__":
    test()
