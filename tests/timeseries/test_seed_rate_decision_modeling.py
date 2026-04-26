"""Tests for the seed-rate-decision-modeling subcommand."""

from unittest.mock import MagicMock

from lseg_toolkit.timeseries.scheduler.default_jobs import ensure_rate_decision_jobs


def test_ensure_is_idempotent(monkeypatch):
    from lseg_toolkit.timeseries.scheduler import default_jobs

    def fake_get_job_by_name(conn, name):
        return {"id": 1, "name": name}

    def fake_create_job(*args, **kwargs):
        raise AssertionError("create_job must not be called when job exists")

    monkeypatch.setattr(default_jobs, "get_job_by_name", fake_get_job_by_name)
    monkeypatch.setattr(default_jobs, "create_job", fake_create_job)

    results = ensure_rate_decision_jobs(MagicMock(), skip_eur_ois=False)
    assert all(action == "exists" for action in results.values())


def test_skip_eur_ois_branch(monkeypatch):
    from lseg_toolkit.timeseries.scheduler import default_jobs

    monkeypatch.setattr(default_jobs, "get_job_by_name", lambda c, n: None)
    monkeypatch.setattr(default_jobs, "create_job", lambda *a, **k: 1)

    results = ensure_rate_decision_jobs(MagicMock(), skip_eur_ois=True)
    assert results["ois_eur_daily"] == "skipped"
    assert results["ois_usd_daily"] == "created"


def test_auto_skip_when_eur_tenors_missing(monkeypatch):
    from lseg_toolkit.timeseries.scheduler import default_jobs

    monkeypatch.setattr(default_jobs, "_eur_ois_unwired", lambda: True)
    monkeypatch.setattr(default_jobs, "get_job_by_name", lambda c, n: None)
    monkeypatch.setattr(default_jobs, "create_job", lambda *a, **k: 1)

    results = ensure_rate_decision_jobs(MagicMock())
    assert results["ois_eur_daily"] == "skipped"


def test_eur_ois_now_wired():
    """Regression guard: EUR_OIS_TENORS should be populated after 2026-04-25 wiring."""
    from lseg_toolkit.timeseries.constants import EUR_OIS_TENORS, get_eur_ois_ric
    from lseg_toolkit.timeseries.scheduler.default_jobs import _eur_ois_unwired

    assert EUR_OIS_TENORS, "EUR_OIS_TENORS should not be empty"
    assert get_eur_ois_ric("3M") == "EUREST3M="
    assert _eur_ois_unwired() is False
