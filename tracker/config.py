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


def get_env(key: str, default: str = "") -> str:
    """Return an environment variable, falling back to ``default``."""
    return os.environ.get(key, default).strip()


def get_vector_dim() -> int:
    """Return the vector embedding dimension from env, defaulting to 768.

    Reads ``AI_TRACKER_VECTOR_DIM``. Used to size embedding columns and
    zero-vector fallbacks so the dimension stays consistent with the
    embedding model output (e.g. 768 for nomic-embed-text).
    """
    return int(get_env("AI_TRACKER_VECTOR_DIM", "768"))


def get_enrich_max_iterations() -> int:
    """Return the max enrichment iterations from env, defaulting to 50.

    Reads ``AI_TRACKER_ENRICH_MAX_ITERATIONS``. Caps the number of
    enrichment batch loops in ``run_enrichment`` to prevent runaway tasks.
    """
    return int(get_env("AI_TRACKER_ENRICH_MAX_ITERATIONS", "50"))
