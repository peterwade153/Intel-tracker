from __future__ import annotations

from tracker.pipeline.enrich import run_enrichment


def test_enrichment_pipeline_end_to_end(db_engine, clean_tables):
    """Insert raw events, run enrichment, verify ai_events populated."""
    from sqlalchemy import text

    from tracker.storage.db import RawEvent, get_engine, upsert_raw_events

    engine = get_engine()

    # Insert raw events
    raw_events = [
        RawEvent(
            source="test_source",
            lab="test_lab",
            external_id="ext_1",
            canonical_url="https://example.com/article-1",
            title="Introducing a new AI model",
            raw_summary="A new model has been released",
            published_at="2026-11-20T10:00:00+00:00",
            payload={},
        ),
        RawEvent(
            source="test_source",
            lab="test_lab",
            external_id="ext_2",
            canonical_url="https://example.com/article-2",
            title="Regular news story",
            raw_summary="Some news",
            published_at="2026-11-19T10:00:00+00:00",
            payload={},
        ),
    ]
    upsert_raw_events(engine, raw_events)

    # Run enrichment with mock embedder
    result = run_enrichment(
        embed=lambda text: [0.1, 0.2, 0.3, 0.4] * 192,  # 768-dim vector
        batch_size=100,
    )
    assert result["received"] == 2
    assert result["enriched"] == 2

    # Verify ai_events has rows
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT count(*) FROM ai_events")).scalar()
        assert rows == 2


def test_enrichment_pipeline_idempotent(db_engine, clean_tables):
    """Running enrichment twice on same data doesn't duplicate."""
    from sqlalchemy import text

    from tracker.storage.db import RawEvent, get_engine, upsert_raw_events

    engine = get_engine()

    raw_events = [
        RawEvent(
            source="test_source",
            lab="test_lab",
            external_id="ext_1",
            canonical_url="https://example.com/article-idempotent",
            title="Test Article",
            raw_summary="Summary",
            published_at="2026-11-20T10:00:00+00:00",
            payload={},
        ),
    ]
    upsert_raw_events(engine, raw_events)

    result1 = run_enrichment(
        embed=lambda text: [0.1, 0.2, 0.3, 0.4] * 192,
        batch_size=100,
    )
    assert result1["enriched"] == 1

    result2 = run_enrichment(
        embed=lambda text: [0.1, 0.2, 0.3, 0.4] * 192,
        batch_size=100,
    )
    assert result2["received"] == 0
    assert result2["enriched"] == 0

    # Verify only one row exists
    with engine.begin() as conn:
        count = conn.execute(text("SELECT count(*) FROM ai_events")).scalar()
        assert count == 1


def test_enrichment_pipeline_handles_dead_url(db_engine, clean_tables):
    """Raw event with URL that returns 404 still gets enriched via raw_summary."""
    from sqlalchemy import text

    from tracker.storage.db import RawEvent, get_engine, upsert_raw_events

    engine = get_engine()

    raw_events = [
        RawEvent(
            source="test_source",
            lab="test_lab",
            external_id="ext_dead",
            canonical_url="https://example.com/dead-link",
            title="Dead Link Article",
            raw_summary="This is the raw summary fallback",
            published_at="2026-11-20T10:00:00+00:00",
            payload={},
        ),
    ]
    upsert_raw_events(engine, raw_events)

    result = run_enrichment(
        embed=lambda text: [0.1, 0.2, 0.3, 0.4] * 192,
        batch_size=100,
    )
    assert result["enriched"] == 1

    # Verify summary was stored from raw_summary fallback
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT summary FROM ai_events WHERE canonical_url = 'https://example.com/dead-link'")
        ).scalar()
        assert row == "This is the raw summary fallback"
