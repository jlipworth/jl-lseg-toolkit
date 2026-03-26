"""Swaption ticker generation utilities."""

from __future__ import annotations

from bloomberg_scripts.common.fields import (
    SWAPTION_CURRENCY_PREFIXES,
    SWAPTION_EXPIRIES,
    SWAPTION_TENORS,
)


def generate_swaption_ticker(
    currency: str,
    expiry: str,
    tenor: str,
    source: str = "BGN",
) -> str:
    """Generate a single swaption ticker.

    Args:
        currency: Currency code (USD, EUR, GBP, etc.)
        expiry: Option expiry (1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y)
        tenor: Underlying swap tenor (2Y, 5Y, 10Y, 30Y)
        source: Price source (BGN, ICAP, etc.)

    Returns:
        Bloomberg ticker string, e.g., "USSV1Y10Y BGN Curncy"
    """
    prefix = SWAPTION_CURRENCY_PREFIXES.get(currency.upper())
    if prefix is None:
        raise ValueError(
            f"Unknown currency: {currency}. "
            f"Valid currencies: {list(SWAPTION_CURRENCY_PREFIXES.keys())}"
        )

    return f"{prefix}{expiry}{tenor} {source} Curncy"


def generate_swaption_tickers(
    currency: str,
    expiries: list[str] | None = None,
    tenors: list[str] | None = None,
    source: str = "BGN",
) -> list[str]:
    """Generate all swaption tickers for a volatility surface grid.

    Args:
        currency: Currency code (USD, EUR, GBP, etc.)
        expiries: List of option expiries (default: standard grid)
        tenors: List of swap tenors (default: standard grid)
        source: Price source (BGN, ICAP, etc.)

    Returns:
        List of Bloomberg tickers for the full grid
    """
    if expiries is None:
        expiries = SWAPTION_EXPIRIES

    if tenors is None:
        tenors = SWAPTION_TENORS

    tickers = []
    for expiry in expiries:
        for tenor in tenors:
            ticker = generate_swaption_ticker(currency, expiry, tenor, source)
            tickers.append(ticker)

    return tickers


def parse_swaption_ticker(ticker: str) -> dict[str, str]:
    """Parse a swaption ticker into components.

    Args:
        ticker: Bloomberg ticker string

    Returns:
        Dictionary with currency, expiry, tenor, source
    """
    parts = ticker.split()
    if len(parts) < 2:
        raise ValueError(f"Invalid ticker format: {ticker}")

    code = parts[0]
    source = parts[1] if len(parts) > 1 else "BGN"

    # Find currency from prefix
    currency = None
    for ccy, prefix in SWAPTION_CURRENCY_PREFIXES.items():
        if code.startswith(prefix):
            currency = ccy
            code = code[len(prefix) :]
            break

    if currency is None:
        raise ValueError(f"Unknown currency prefix in ticker: {ticker}")

    # Parse expiry and tenor from remaining code
    # Format is like "1Y10Y" - need to split at the boundary
    expiry, tenor = _split_expiry_tenor(code)

    return {
        "currency": currency,
        "expiry": expiry,
        "tenor": tenor,
        "source": source,
    }


def _split_expiry_tenor(code: str) -> tuple[str, str]:
    """Split combined expiry-tenor code into parts.

    Args:
        code: Combined code like "1Y10Y" or "3M5Y"

    Returns:
        Tuple of (expiry, tenor)
    """
    # Standard tenors we're looking for
    standard_tenors = ["2Y", "5Y", "10Y", "30Y", "20Y", "7Y", "15Y"]

    for tenor in standard_tenors:
        if code.endswith(tenor):
            expiry = code[: -len(tenor)]
            return expiry, tenor

    raise ValueError(f"Could not parse expiry/tenor from: {code}")
