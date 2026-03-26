"""Helpers for quarantined legacy Bloomberg codepaths."""

from __future__ import annotations

import warnings

DOCS_HINT = "See docs/instruments/BLOOMBERG.md for the current support matrix."


def legacy_surface_message(
    surface: str,
    *,
    replacement: str | None = None,
    note: str | None = None,
) -> str:
    """Return a standard warning for legacy Bloomberg codepaths."""
    parts = [
        f"`{surface}` is a legacy/research Bloomberg path retained for exploratory work only.",
    ]
    if note:
        parts.append(note)
    if replacement:
        parts.append(f"Use `{replacement}` for supported workflows.")
    parts.append(DOCS_HINT)
    return " ".join(parts)


def warn_legacy_surface(
    surface: str,
    *,
    replacement: str | None = None,
    note: str | None = None,
    stacklevel: int = 2,
) -> str:
    """Emit a warning for a quarantined legacy Bloomberg codepath."""
    message = legacy_surface_message(
        surface,
        replacement=replacement,
        note=note,
    )
    warnings.warn(message, stacklevel=stacklevel)
    return message
