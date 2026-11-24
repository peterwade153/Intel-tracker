from __future__ import annotations

from tracker.storage.db import RawEvent


def test_raw_event_content_hash_deterministic():
    e1 = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Title",
        raw_summary="Summary",
    )
    e2 = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Title",
        raw_summary="Summary",
    )
    assert e1.content_hash == e2.content_hash


def test_raw_event_content_hash_changes_with_content():
    e1 = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Title",
        raw_summary="Summary A",
    )
    e2 = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Title",
        raw_summary="Summary B",
    )
    assert e1.content_hash != e2.content_hash


def test_raw_event_defaults():
    e = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Title",
    )
    assert e.external_id is None
    assert e.raw_summary is None
    assert e.raw_content is None
    assert e.published_at is None
    assert e.payload == {}
