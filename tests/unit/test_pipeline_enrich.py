from __future__ import annotations

import pytest

from tracker.pipeline.enrich import categorize, impact_score, run_enrichment
from tracker.storage.db import RawEvent


def test_categorize_models():
    event = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Introducing a new LLM model",
    )
    assert categorize(event) == "models"


def test_categorize_research():
    event = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="New research paper on arxiv",
    )
    assert categorize(event) == "research"


def test_categorize_engineering():
    event = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Engineering infrastructure deployment",
    )
    assert categorize(event) == "engineering"


def test_categorize_news():
    event = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Company announces partnership launch",
    )
    assert categorize(event) == "news"


def test_categorize_uncategorized():
    event = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Random unrelated topic",
    )
    assert categorize(event) == "uncategorized"


def test_impact_score_base():
    event = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Regular news story",
    )
    score = impact_score(event)
    assert 1 <= score <= 10


def test_impact_score_high_signal():
    event = RawEvent(
        source="test",
        lab="test",
        canonical_url="https://example.com/a",
        title="Introducing state-of-the-art new model",
    )
    score = impact_score(event)
    assert score >= 7


def test_impact_score_hn_points():
    event = RawEvent(
        source="hacker_news",
        lab="community",
        canonical_url="https://example.com/a",
        title="HN story",
        raw_summary="HN points: 150 | comments: 10",
    )
    score = impact_score(event)
    assert score == 7  # 5 (base) + 2 (100+ HN points)


def test_impact_score_capped_at_10():
    event = RawEvent(
        source="hacker_news",
        lab="community",
        canonical_url="https://example.com/a",
        title="Introducing state-of-the-art new model launch release best first",
        raw_summary="HN points: 150 | comments: 10",
    )
    score = impact_score(event)
    assert score == 10  # 5 (base) + 3 (high signal) + 2 (100+ HN points) = 10, capped at 10


@pytest.mark.integration
def test_run_enrichment_no_unprocessed(db_engine, clean_tables):
    result = run_enrichment(embed=lambda t: [0.1, 0.2, 0.3], batch_size=100)
    assert result == {"received": 0, "enriched": 0}
