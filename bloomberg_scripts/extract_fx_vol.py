#!/usr/bin/env python3
"""Extract FX ATM Implied Volatility - CONFIRMED WORKING.

Pattern: {PAIR}V{TENOR} BGN Curncy
Example: EURUSDV1M BGN Curncy = EUR-USD OPT VOL 1M

Usage:
    python extract_fx_vol.py
    python extract_fx_vol.py --pairs EURUSD USDJPY GBPUSD
    python extract_fx_vol.py --output fx_atm_vol.csv
"""

import argparse
from datetime import date

import blpapi
import pandas as pd


# Confirmed working pairs
PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCHF", "USDCAD"]

# Confirmed working tenors for EURUSD (others may have fewer)
TENORS = ["1W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y"]

FIELDS = ["PX_LAST", "NAME", "LAST_UPDATE"]


def generate_tickers(pairs=None, tenors=None):
    """Generate FX ATM vol tickers.

    Pattern: {PAIR}V{TENOR} BGN Curncy
    """
    if pairs is None:
        pairs = PAIRS
    if tenors is None:
        tenors = TENORS

    tickers = []
    for pair in pairs:
        for tenor in tenors:
            ticker = f"{pair}V{tenor} BGN Curncy"
            tickers.append({
                "ticker": ticker,
                "pair": pair,
                "tenor": tenor,
            })
    return tickers


def extract_fx_atm_vol(pairs=None, tenors=None):
    """Extract FX ATM implied volatility."""
    ticker_info = generate_tickers(pairs, tenors)
    ticker_list = [t["ticker"] for t in ticker_info]
    ticker_map = {t["ticker"]: t for t in ticker_info}

    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        session.start()
        session.openService("//blp/refdata")

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for ticker in ticker_list:
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

                        info = ticker_map.get(ticker, {})
                        row = {
                            "pair": info.get("pair", ""),
                            "tenor": info.get("tenor", ""),
                            "ticker": ticker,
                        }

                        has_data = False
                        if sec_data.hasElement("fieldData"):
                            fd = sec_data.getElement("fieldData")
                            if fd.hasElement("PX_LAST"):
                                try:
                                    row["atm_vol"] = fd.getElementAsFloat("PX_LAST")
                                    has_data = True
                                except:
                                    pass
                            if fd.hasElement("NAME"):
                                row["name"] = fd.getElementAsString("NAME")
                            if fd.hasElement("LAST_UPDATE"):
                                try:
                                    row["last_update"] = fd.getElementAsString("LAST_UPDATE")
                                except:
                                    pass

                        if has_data:
                            results.append(row)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        return pd.DataFrame(results)

    finally:
        session.stop()


def main():
    parser = argparse.ArgumentParser(description="Extract FX ATM Implied Volatility")
    parser.add_argument("--pairs", "-p", nargs="+", default=None,
                        help=f"Currency pairs (default: {', '.join(PAIRS)})")
    parser.add_argument("--tenors", "-t", nargs="+", default=None,
                        help=f"Tenors (default: {', '.join(TENORS)})")
    parser.add_argument("--output", "-o", help="Output CSV file")
    args = parser.parse_args()

    print("Extracting FX ATM Implied Volatility...")
    print(f"Pattern: {{PAIR}}V{{TENOR}} BGN Curncy")
    print()

    df = extract_fx_atm_vol(pairs=args.pairs, tenors=args.tenors)
    df["extract_date"] = date.today().isoformat()

    if df.empty:
        print("No data returned")
        return

    # Show pivot table
    print(f"=== FX ATM Implied Volatility ({len(df)} points) ===\n")
    pivot = df.pivot_table(index="tenor", columns="pair", values="atm_vol", aggfunc="first")

    # Reorder tenors
    tenor_order = ["1W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y", "3Y", "5Y"]
    tenor_order = [t for t in tenor_order if t in pivot.index]
    if tenor_order:
        pivot = pivot.reindex(tenor_order)

    print(pivot.to_string())

    # Raw data
    print(f"\n=== Raw Data ===\n")
    print(df.to_string(index=False))

    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
