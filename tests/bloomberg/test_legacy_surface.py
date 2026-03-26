from bloomberg_scripts._legacy import legacy_surface_message


def test_legacy_surface_message_points_to_supported_cli():
    message = legacy_surface_message(
        "bloomberg_scripts.jgb_yields",
        replacement="bbg-extract jgb",
        note="This path is retained for archaeology.",
    )

    assert "legacy/research Bloomberg path" in message
    assert "bbg-extract jgb" in message
    assert "docs/instruments/BLOOMBERG.md" in message
