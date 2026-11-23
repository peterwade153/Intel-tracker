from __future__ import annotations

import os
from urllib.parse import quote_plus


def get_tracker_database_url(database_url: str | None = None) -> str:
    """Resolve the SQLAlchemy database URL for the tracker database."""
    if database_url and database_url.strip():
        return database_url.strip()

    env_url = os.environ.get("TRACKER_DATABASE_URL", "").strip()
    if env_url:
        return env_url

    host = os.environ.get("TRACKER_DB_HOST", "").strip()
    name = os.environ.get("TRACKER_DB_NAME", "").strip()
    user = os.environ.get("TRACKER_DB_USER", "").strip()
    password = os.environ.get("TRACKER_DB_PASSWORD", "")
    port = os.environ.get("TRACKER_DB_PORT", "5432").strip() or "5432"

    if all([host, name, user]) and password:
        encoded_user = quote_plus(user)
        encoded_password = quote_plus(password)
        return f"postgresql+psycopg://{encoded_user}:{encoded_password}@{host}:{port}/{name}"

    raise RuntimeError(
        "Database configuration missing: set TRACKER_DATABASE_URL or "
        "TRACKER_DB_HOST, TRACKER_DB_PORT, TRACKER_DB_NAME, TRACKER_DB_USER, and TRACKER_DB_PASSWORD."
    )


def get_tracker_psycopg_dsn(database_url: str | None = None) -> str:
    """Return a standard libpq/psycopg DSN without SQLAlchemy driver prefix."""
    url = get_tracker_database_url(database_url)
    return url.replace("postgresql+psycopg://", "postgresql://", 1)
