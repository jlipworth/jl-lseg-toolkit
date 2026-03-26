#!/usr/bin/env python3
"""Search Bloomberg instruments service - research/probe only.

See `docs/BLOOMBERG_SCRIPTS.md` for the current research playbook.
"""

import sys

import blpapi

from bloomberg_scripts._legacy import legacy_surface_message


def search(query: str, max_results: int = 100, yellow_key: str = None):
    """Search for securities using //blp/instruments service."""
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)

    session = blpapi.Session(options)

    try:
        if not session.start():
            print("Failed to start session")
            return

        # Try instruments service
        if not session.openService("//blp/instruments"):
            print("Failed to open //blp/instruments service")
            print("\nTrying alternative: govtListRequest on //blp/refdata...")
            return

        service = session.getService("//blp/instruments")

        # Try instrumentListRequest
        request = service.createRequest("instrumentListRequest")
        request.set("query", query)
        request.set("maxResults", max_results)

        # Optional: filter by yellow key
        if yellow_key:
            request.set("yellowKeyFilter", yellow_key)

        print(f"Searching for: '{query}'")
        if yellow_key:
            print(f"Yellow key filter: {yellow_key}")
        print("-" * 80)

        session.sendRequest(request)

        total_results = 0

        while True:
            event = session.nextEvent(10000)

            for msg in event:
                # Print message type for debugging
                msg_type = msg.messageType()

                if msg.hasElement("results"):
                    results = msg.getElement("results")
                    count = results.numValues()
                    total_results += count

                    for i in range(count):
                        result = results.getValue(i)
                        security = result.getElementAsString("security") if result.hasElement("security") else "N/A"
                        desc = result.getElementAsString("description") if result.hasElement("description") else ""
                        print(f"{security:<45} {desc}")

                elif msg.hasElement("responseError"):
                    err = msg.getElement("responseError")
                    print(f"Error: {err}")

                else:
                    # Print raw message for debugging
                    print(f"Message type: {msg_type}")
                    print(msg)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        print(f"\nTotal results: {total_results}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.stop()


def main():
    print(
        legacy_surface_message(
            "search_instruments.py",
            note=(
                "This script is research-only and should not be treated as the supported Bloomberg interface."
            ),
        )
    )
    # Default searches for swaption vol
    searches = [
        ("swaption", None),
        ("swaption vol", None),
        ("swaption volatility", None),
        ("USD swaption", None),
        ("swap vol", None),
        ("USSV", None),
        ("interest rate vol", None),
        ("ir vol", None),
        ("rate volatility", None),
    ]

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        search(query)
    else:
        print("Running default swaption searches...\n")
        for query, yk in searches:
            print(f"\n{'='*80}")
            search(query, max_results=20, yellow_key=yk)


if __name__ == "__main__":
    main()
