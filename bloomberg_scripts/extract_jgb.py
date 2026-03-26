#!/usr/bin/env python3
"""Extract JGB yields - CONFIRMED WORKING.

Usage:
    python extract_jgb.py
    python extract_jgb.py --output jgb_yields.csv
"""

import argparse
from datetime import date

import blpapi
import pandas as pd


JGB_TICKERS = {
    "1Y": "GJGB1 Index",
    "2Y": "GJGB2 Index",
    "3Y": "GJGB3 Index",
    "4Y": "GJGB4 Index",
    "5Y": "GJGB5 Index",
    "6Y": "GJGB6 Index",
    "7Y": "GJGB7 Index",
    "8Y": "GJGB8 Index",
    "9Y": "GJGB9 Index",
    "10Y": "GJGB10 Index",
    "15Y": "GJGB15 Index",
    "20Y": "GJGB20 Index",
    "25Y": "GJGB25 Index",
    "30Y": "GJGB30 Index",
    "40Y": "GJGB40 Index",
}

FIELDS = ["PX_LAST", "NAME", "LAST_UPDATE"]


def extract_jgb():
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        session.start()
        session.openService("//blp/refdata")

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for ticker in JGB_TICKERS.values():
            request.append("securities", ticker)
        for field in FIELDS:
            request.append("fields", field)

        session.sendRequest(request)

        results = []

        while True:
            event = session.nextEvent(10000)

            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data_array = msg.getElement("securityData")

                    for i in range(sec_data_array.numValues()):
                        sec_data = sec_data_array.getValue(i)
                        ticker = sec_data.getElementAsString("security")

                        row = {"ticker": ticker}

                        if sec_data.hasElement("fieldData"):
                            fd = sec_data.getElement("fieldData")
                            for field in FIELDS:
                                if fd.hasElement(field):
                                    try:
                                        row[field] = fd.getElementAsFloat(field)
                                    except:
                                        row[field] = fd.getElementAsString(field)

                        results.append(row)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        return pd.DataFrame(results)

    finally:
        session.stop()


def main():
    parser = argparse.ArgumentParser(description="Extract JGB yields")
    parser.add_argument("--output", "-o", help="Output CSV file")
    args = parser.parse_args()

    print("Extracting JGB yields...")

    df = extract_jgb()

    # Add tenor from ticker mapping
    reverse_map = {v: k for k, v in JGB_TICKERS.items()}
    df["tenor"] = df["ticker"].map(reverse_map)
    df["extract_date"] = date.today().isoformat()

    # Reorder
    cols = ["tenor", "PX_LAST", "NAME", "LAST_UPDATE", "ticker", "extract_date"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]

    print(f"\nJGB Yields ({date.today()}):")
    print(df.to_string(index=False))

    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
