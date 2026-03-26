#!/usr/bin/env python3
"""Standalone swaption vol probe - research only.

See `docs/BLOOMBERG_SCRIPTS.md` for the current research playbook.

Copy this file and run:
    python extract_swaptions.py
    python extract_swaptions.py --currency EUR
    python extract_swaptions.py --currency USD --output swaptions.csv
"""

import argparse
from datetime import date

import blpapi
import pandas as pd

from bloomberg_scripts._legacy import legacy_surface_message

# Swaption ticker prefixes by currency
CURRENCY_PREFIXES = {
    "USD": "USSV",
    "EUR": "EUSV",
    "GBP": "BPSV",
    "JPY": "JYSV",
    "CHF": "SFSV",
    "AUD": "ADSV",
}

# Standard grid
EXPIRIES = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"]
TENORS = ["2Y", "5Y", "10Y", "30Y"]

# Fields to request
FIELDS = ["PX_LAST", "PX_BID", "PX_ASK", "LAST_UPDATE"]


def generate_tickers(currency: str) -> list[str]:
    """Generate swaption tickers for a currency."""
    prefix = CURRENCY_PREFIXES.get(currency.upper())
    if not prefix:
        raise ValueError(f"Unknown currency: {currency}")

    tickers = []
    for expiry in EXPIRIES:
        for tenor in TENORS:
            ticker = f"{prefix}{expiry}{tenor} BGN Curncy"
            tickers.append(ticker)
    return tickers


def extract_data(tickers: list[str], fields: list[str]) -> pd.DataFrame:
    """Extract reference data from Bloomberg."""
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            raise RuntimeError("Failed to start Bloomberg session")

        if not session.openService("//blp/refdata"):
            raise RuntimeError("Failed to open refdata service")

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for ticker in tickers:
            request.append("securities", ticker)
        for field in fields:
            request.append("fields", field)

        session.sendRequest(request)

        # Collect results
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
                            field_data = sec_data.getElement("fieldData")
                            for field in fields:
                                if field_data.hasElement(field):
                                    try:
                                        row[field] = field_data.getElementAsFloat(field)
                                    except Exception:
                                        row[field] = field_data.getElementAsString(field)
                                else:
                                    row[field] = None

                        # Check for errors
                        if sec_data.hasElement("fieldExceptions"):
                            exceptions = sec_data.getElement("fieldExceptions")
                            if exceptions.numValues() > 0:
                                row["error"] = str(exceptions)

                        results.append(row)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        return pd.DataFrame(results)

    finally:
        session.stop()


def parse_ticker(ticker: str) -> dict:
    """Parse ticker to extract expiry and tenor."""
    import re
    # Match pattern like USSV1Y10Y
    match = re.search(r"[A-Z]{4}(\d+[MY])(\d+Y)", ticker)
    if match:
        return {"expiry": match.group(1), "tenor": match.group(2)}
    return {"expiry": "", "tenor": ""}


def main():
    print(
        legacy_surface_message(
            "extract_swaptions.py",
            note=(
                "This script is research-only and should not be treated as the supported Bloomberg interface."
            ),
        )
    )
    parser = argparse.ArgumentParser(description="Extract swaption vol surface")
    parser.add_argument("--currency", "-c", default="USD", help="Currency (USD, EUR, GBP, JPY, CHF, AUD)")
    parser.add_argument("--output", "-o", default=None, help="Output CSV file")
    args = parser.parse_args()

    print(f"Extracting {args.currency} swaption surface...")

    tickers = generate_tickers(args.currency)
    print(f"Generated {len(tickers)} tickers")

    df = extract_data(tickers, FIELDS)

    # Add parsed columns
    parsed = df["ticker"].apply(parse_ticker)
    df["expiry"] = parsed.apply(lambda x: x["expiry"])
    df["tenor"] = parsed.apply(lambda x: x["tenor"])
    df["currency"] = args.currency.upper()
    df["extract_date"] = date.today().isoformat()

    # Reorder columns
    cols = ["currency", "expiry", "tenor", "PX_LAST", "PX_BID", "PX_ASK", "LAST_UPDATE", "ticker", "extract_date"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]

    print(f"\nExtracted {len(df)} data points:")
    print(df.to_string(index=False))

    # Create pivot table
    if "PX_LAST" in df.columns:
        print("\n\nVol Surface (PX_LAST):")
        pivot = df.pivot_table(index="expiry", columns="tenor", values="PX_LAST", aggfunc="first")
        # Reorder
        pivot = pivot.reindex(index=EXPIRIES, columns=TENORS)
        print(pivot.to_string())

    # Save if requested
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
