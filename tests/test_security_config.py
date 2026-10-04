"""Offline regressions for credential storage and configuration handling."""

import json
import os
import stat

import pytest
from psycopg.conninfo import conninfo_to_dict

from lseg_toolkit import setup_app_key
from lseg_toolkit.client.config import _load_config_file
from lseg_toolkit.timeseries.config import DatabaseConfig


@pytest.mark.parametrize(
    "password", ["test password", "a+b", "quote'\\slash", "@:/?#%", ""]
)
def test_database_credentials_round_trip(password):
    config = DatabaseConfig(
        user="user @name", database="database /name", password=password
    )
    parsed = conninfo_to_dict(config.dsn)
    assert parsed["password"] == password
    assert parsed["user"] == config.user
    assert parsed["dbname"] == config.database


def test_database_config_repr_hides_password():
    assert "synthetic-secret" not in repr(DatabaseConfig(password="synthetic-secret"))


@pytest.mark.parametrize(
    "value",
    [None, [], 123, "text", {"app_key": None}, {"app_key": 123}, {"app_key": []}],
)
def test_wrong_shape_app_config_is_ignored(tmp_path, value):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(value))
    assert _load_config_file(path) is None


def test_app_key_is_trimmed(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"app_key": "  synthetic-key  "}))
    assert _load_config_file(path) == "synthetic-key"


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
@pytest.mark.parametrize("location", ["1", "2"])
@pytest.mark.parametrize("overwrite", [False, True])
def test_setup_restricts_new_and_existing_credentials(
    tmp_path, monkeypatch, location, overwrite
):
    monkeypatch.setattr(setup_app_key.Path, "home", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    path = tmp_path / (".lseg/config.json" if location == "1" else ".lseg-config.json")
    if overwrite:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("old content" * 100)
        path.chmod(0o644)
        path.parent.chmod(0o755)
    original_directory_mode = stat.S_IMODE(tmp_path.stat().st_mode)
    responses = iter(["a" * 40, location, "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    previous_umask = os.umask(0o022)
    try:
        setup_app_key.main()
    finally:
        os.umask(previous_umask)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {"app_key": "a" * 40}
    if location == "1":
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    else:
        assert stat.S_IMODE(tmp_path.stat().st_mode) == original_directory_mode


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="Requires no-follow support")
def test_setup_does_not_overwrite_symlink_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "target"
    target.write_text("unchanged")
    (tmp_path / ".lseg-config.json").symlink_to(target)
    responses = iter(["a" * 40, "2", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    with pytest.raises(SystemExit) as error:
        setup_app_key.main()
    assert error.value.code == 1
    assert target.read_text() == "unchanged"
