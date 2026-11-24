from __future__ import annotations

import os
from typing import Any

import pytest
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://airflow:airflow@localhost:5433/ai_tracker_test",
)


@pytest.fixture(scope="session")
def db_engine():
    """SQLAlchemy engine against the test Postgres database."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_tables(db_engine):
    """Truncate test tables before each test to ensure isolation."""
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM ai_events"))
        conn.execute(text("DELETE FROM raw_events"))
        conn.execute(text("DELETE FROM schema_migrations"))
    yield
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM ai_events"))
        conn.execute(text("DELETE FROM raw_events"))
        conn.execute(text("DELETE FROM schema_migrations"))


@pytest.fixture
def mock_hn_response() -> dict[str, Any]:
    """Sample Algolia API response with 2 hits."""
    return {
        "hits": [
            {
                "objectID": "hn_1",
                "title": "Introducing a new AI model",
                "url": "https://example.com/hn-article-1",
                "points": 150,
                "num_comments": 42,
                "created_at": "2026-11-20T10:00:00Z",
            },
            {
                "objectID": "hn_2",
                "title": "Another AI story",
                "url": "https://example.com/hn-article-2",
                "points": 10,
                "num_comments": 5,
                "created_at": "2026-11-19T10:00:00Z",
            },
        ]
    }


@pytest.fixture
def mock_rss_feed() -> str:
    """Sample RSS XML with 3 entries."""
    return """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Test AI Release</title>
      <link>https://example.com/release-1</link>
      <guid>https://example.com/release-1</guid>
      <pubDate>Mon, 23 Nov 2026 10:00:00 GMT</pubDate>
      <description>Summary text for release 1</description>
    </item>
    <item>
      <title>Second Release</title>
      <link>https://example.com/release-2</link>
      <guid>https://example.com/release-2</guid>
      <pubDate>Mon, 23 Nov 2026 09:00:00 GMT</pubDate>
      <description>Summary text for release 2</description>
    </item>
    <item>
      <title>No Link Item</title>
      <guid>https://example.com/no-link</guid>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def mock_ollama_embed_response() -> dict[str, Any]:
    """Mock Ollama /api/embed response with 3-dim vector (test uses small dims)."""
    return {"embeddings": [[0.1, 0.2, 0.3]]}


@pytest.fixture
def sample_raw_event() -> dict[str, Any]:
    """Sample RawEvent constructor kwargs."""
    return {
        "source": "test_source",
        "lab": "test_lab",
        "external_id": "ext_1",
        "canonical_url": "https://example.com/test-article",
        "title": "Test Article Title",
        "raw_summary": "Test summary",
        "raw_content": "Full article content",
        "published_at": "2026-11-20T10:00:00+00:00",
        "payload": {"key": "value"},
    }
