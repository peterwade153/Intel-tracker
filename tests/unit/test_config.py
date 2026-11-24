from __future__ import annotations

import pytest

from tracker.config import get_env, get_tracker_database_url, get_tracker_psycopg_dsn


def test_get_tracker_database_url_from_env(monkeypatch):
    monkeypatch.setenv(
        "TRACKER_DATABASE_URL",
        "postgresql+psycopg://user:pass@host:5432/db",
    )
    monkeypatch.delenv("TRACKER_DB_HOST", raising=False)
    assert get_tracker_database_url() == "postgresql+psycopg://user:pass@host:5432/db"


def test_get_tracker_database_url_from_parts(monkeypatch):
    monkeypatch.delenv("TRACKER_DATABASE_URL", raising=False)
    monkeypatch.setenv("TRACKER_DB_HOST", "localhost")
    monkeypatch.setenv("TRACKER_DB_PORT", "5432")
    monkeypatch.setenv("TRACKER_DB_NAME", "testdb")
    monkeypatch.setenv("TRACKER_DB_USER", "testuser")
    monkeypatch.setenv("TRACKER_DB_PASSWORD", "testpass")
    url = get_tracker_database_url()
    assert url == "postgresql+psycopg://testuser:testpass@localhost:5432/testdb"


def test_get_tracker_database_url_missing(monkeypatch):
    monkeypatch.delenv("TRACKER_DATABASE_URL", raising=False)
    monkeypatch.delenv("TRACKER_DB_HOST", raising=False)
    monkeypatch.delenv("TRACKER_DB_NAME", raising=False)
    monkeypatch.delenv("TRACKER_DB_USER", raising=False)
    monkeypatch.delenv("TRACKER_DB_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="Database configuration missing"):
        get_tracker_database_url()


def test_get_tracker_psycopg_dsn_strips_driver(monkeypatch):
    monkeypatch.setenv(
        "TRACKER_DATABASE_URL",
        "postgresql+psycopg://user:pass@host:5432/db",
    )
    dsn = get_tracker_psycopg_dsn()
    assert dsn == "postgresql://user:pass@host:5432/db"


def test_get_env_default(monkeypatch):
    monkeypatch.delenv("MY_TEST_VAR", raising=False)
    assert get_env("MY_TEST_VAR", "default") == "default"


def test_get_env_value(monkeypatch):
    monkeypatch.setenv("MY_TEST_VAR", "env_value")
    assert get_env("MY_TEST_VAR", "default") == "env_value"
