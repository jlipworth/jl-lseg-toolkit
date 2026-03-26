#!/usr/bin/env python3
"""Search Bloomberg securities - research/probe only.

See `docs/BLOOMBERG_SCRIPTS.md` for the current research playbook.

Usage:
    python search_securities.py "swaption USD"
    python search_securities.py "cap floor USD SOFR"
    python search_securities.py "JGB yield"
    python search_securities.py "risk reversal EUR"

    # Save to file
    python search_securities.py "swaption USD" > results.txt
    python search_securities.py "swaption USD" --output results.txt
"""

import sys

import blpapi

from bloomberg_scripts._legacy import legacy_surface_message


def search_securities(query: str, max_results: int = 50):
    """Search for securities matching query."""
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("Failed to start session")
            return

        # Try instruments service for search
        if not session.openService("//blp/instruments"):
            print("Failed to open //blp/instruments service")
            print("Trying //blp/refdata instead...")

            # Fallback - can't really search, but show this
            return

        service = session.getService("//blp/instruments")

        # Create instrument list request
        request = service.createRequest("instrumentListRequest")
        request.set("query", query)
        request.set("maxResults", max_results)

        # Optional filters
        # request.set("yellowKeyFilter", "YK_FILTER_CURNCY")  # Currency/rates
        # request.set("languageOverride", "LANG_ID_EN")

        print(f"Searching for: {query}")
        print("-" * 80)

        session.sendRequest(request)

        while True:
            event = session.nextEvent(10000)

            for msg in event:
                print(f"\nMessage type: {msg.messageType()}")

                if msg.hasElement("results"):
                    results = msg.getElement("results")
                    print(f"\nFound {results.numValues()} results:\n")

                    for i in range(results.numValues()):
                        result = results.getValue(i)
                        security = result.getElementAsString("security") if result.hasElement("security") else "N/A"
                        description = result.getElementAsString("description") if result.hasElement("description") else ""

                        print(f"  {security:<40} {description}")

                elif msg.hasElement("securityData"):
                    # Response from refdata
                    print(msg)

                else:
                    # Print raw message for debugging
                    print(msg)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

    except Exception as e:
        print(f"Error: {e}")

    finally:
        session.stop()


def main():
    print(
        legacy_surface_message(
            "search_securities.py",
            note=(
                "This script is research-only and should not be treated as the supported Bloomberg interface."
            ),
        )
    )
    if len(sys.argv) < 2:
        # Default searches to try
        searches = [
            "USD swaption vol",
            "swaption volatility",
            "USD cap floor",
            "SOFR cap",
            "JGB",
            "risk reversal EURUSD",
        ]
        print("No query provided. Running default searches...\n")
        for q in searches:
            print("\n" + "=" * 80)
            search_securities(q, max_results=10)
    else:
        query = " ".join(sys.argv[1:])
        search_securities(query)


if __name__ == "__main__":
    main()
