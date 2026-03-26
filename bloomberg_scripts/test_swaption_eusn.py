#!/usr/bin/env python3
"""Test swaption pattern: EUSN0110 BVOL Curncy"""

import blpapi

# Pattern: {CCY}SN{EXPIRY}{TENOR} BVOL/NVOL Curncy
# EUSN0110 = EU Swaption Normal? 01Y expiry, 10Y tenor
# Test variations

TEST_TICKERS = [
    # EUR - the discovered pattern
    "EUSN0110 BVOL Curncy",
    "EUSN0110 NVOL Curncy",
    "EUSN0110 Curncy",

    # EUR - other expiry/tenor combos
    "EUSN0102 BVOL Curncy",  # 1Y into 2Y
    "EUSN0105 BVOL Curncy",  # 1Y into 5Y
    "EUSN0130 BVOL Curncy",  # 1Y into 30Y
    "EUSN0310 BVOL Curncy",  # 3M into 10Y
    "EUSN0610 BVOL Curncy",  # 6M into 10Y
    "EUSN0210 BVOL Curncy",  # 2Y into 10Y
    "EUSN0510 BVOL Curncy",  # 5Y into 10Y
    "EUSN1010 BVOL Curncy",  # 10Y into 10Y

    # EUR - NVOL (normal vol) versions
    "EUSN0102 NVOL Curncy",
    "EUSN0105 NVOL Curncy",
    "EUSN0110 NVOL Curncy",
    "EUSN0130 NVOL Curncy",

    # USD equivalent - guess the prefix
    "USSN0110 BVOL Curncy",
    "USSN0110 NVOL Curncy",
    "USSN0105 BVOL Curncy",
    "USSN0102 BVOL Curncy",
    "USSN0130 BVOL Curncy",

    # Alternative USD prefixes
    "UDSN0110 BVOL Curncy",
    "USDSN0110 BVOL Curncy",
    "SWUSN0110 BVOL Curncy",

    # GBP
    "BPSN0110 BVOL Curncy",
    "GBSN0110 BVOL Curncy",
    "GBPSN0110 BVOL Curncy",

    # JPY
    "JYSN0110 BVOL Curncy",
    "JPSN0110 BVOL Curncy",

    # Try BGN source
    "EUSN0110 BGN BVOL Curncy",
    "USSN0110 BGN BVOL Curncy",

    # Try without BVOL/NVOL
    "EUSN0110 BGN Curncy",
    "USSN0110 BGN Curncy",
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

        print("Testing swaption EUSN pattern...")
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
                        sec_type = ""

                        if sec_data.hasElement("fieldData"):
                            fd = sec_data.getElement("fieldData")
                            if fd.hasElement("PX_LAST"):
                                try:
                                    px = fd.getElementAsFloat("PX_LAST")
                                except:
                                    pass
                            if fd.hasElement("NAME"):
                                name = fd.getElementAsString("NAME")
                            if fd.hasElement("SECURITY_TYP"):
                                sec_type = fd.getElementAsString("SECURITY_TYP")

                        if px is not None:
                            working.append((ticker, px, name, sec_type))
                            print(f"✅ {ticker:<33} {px:<12.4f} {name} [{sec_type}]")
                        else:
                            print(f"❌ {ticker:<33}")

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        print(f"\n{'='*90}")
        print(f"WORKING: {len(working)}")
        if working:
            print("\n*** WORKING TICKERS: ***")
            for t, p, n, st in working:
                print(f"  {t} = {p} ({n}) [{st}]")

    finally:
        session.stop()


if __name__ == "__main__":
    test()
