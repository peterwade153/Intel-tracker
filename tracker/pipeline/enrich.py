from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from tracker.extractors.content import extract_and_clean
from tracker.storage.db import RawEvent, get_engine
from tracker.storage.enriched_db import EnrichedEvent, upsert_enriched_events

Embedder = Callable[[str], list[float]]


def categorize(raw_event: RawEvent) -> str:
    """Heuristically categorize an event based on title, URL, and source."""
    text = f"{raw_event.title} {raw_event.source} {raw_event.lab}".lower()
    if any(k in text for k in ("model", "llm", "lfm", "foundation", "weights", "tokenizer")):
        return "models"
    if any(k in text for k in ("engineering", "tech", "infrastructure", "production", "deploy")):
        return "engineering"
    if any(k in text for k in ("research", "paper", "arxiv", "benchmark", "study")):
        return "research"
    if any(k in text for k in ("news", "partnership", "launch", "announce", "release")):
        return "news"
    return "uncategorized"


def impact_score(raw_event: RawEvent) -> int:
    """Heuristic impact score from 1 to 10 based on title and source signals."""
    text = f"{raw_event.title} {raw_event.source}".lower()
    score = 5
    high_signal = ("introducing", "launch", "release", "state-of-the-art", "best", "first", "new model")
    medium_signal = ("update", "improvement", "optimization", "partnership", "benchmark")
    if any(k in text for k in high_signal):
        score += 3
    if any(k in text for k in medium_signal):
        score += 1
    if raw_event.source == "hacker_news":
        try:
            points = int(raw_event.raw_summary.split("points: ")[1].split(" ")[0])
            if points >= 100:
                score += 2
            elif points >= 50:
                score += 1
        except (ValueError, IndexError):
            pass
    return min(max(score, 1), 10)


def enrich_event(raw_event: RawEvent, raw_event_id: int, embed: Embedder) -> EnrichedEvent:
    """Enrich a single raw event: extract content, categorize, score, embed."""
    content = extract_and_clean(str(raw_event.canonical_url)) or raw_event.raw_summary or ""
    summary = content[:2000] if content else raw_event.raw_summary or ""
    category = categorize(raw_event)
    score = impact_score(raw_event)
    embedding = embed(summary) if summary else [0.0] * 768

    return EnrichedEvent(
        raw_event_id=raw_event_id,
        source=raw_event.source,
        lab=raw_event.lab,
        canonical_url=str(raw_event.canonical_url),
        title=raw_event.title.strip(),
        category=category,
        summary=summary,
        impact_score=score,
        published_at=raw_event.published_at,
        enriched_at=datetime.now(UTC),
        embedding=embedding,
    )


def run_enrichment(embed: Embedder, batch_size: int = 100, max_iterations: int = 50) -> dict[str, int]:
    """Enrich all unprocessed raw events and upsert into ai_events.

    Loops over batches until no unprocessed records remain, capped at
    ``max_iterations`` to prevent runaway tasks. Each iteration fetches up to
    ``batch_size`` rows, enriches them, and upserts to ``ai_events``.
    """
    from sqlalchemy import text

    engine = get_engine()
    sql = text(
        """
        SELECT r.id, r.source, r.lab, r.external_id, r.canonical_url, r.title,
               r.raw_summary, r.raw_content, r.published_at, r.payload
        FROM raw_events r
        LEFT JOIN ai_events e ON e.raw_event_id = r.id
        WHERE e.id IS NULL
        ORDER BY r.fetched_at DESC
        LIMIT :limit
        """
    )

    total_received = 0
    total_enriched = 0

    for _ in range(max_iterations):
        with engine.begin() as conn:
            rows = conn.execute(sql, {"limit": batch_size}).mappings().all()

        if not rows:
            break

        enriched_events = []
        for row in rows:
            raw_event = RawEvent(
                source=row["source"],
                lab=row["lab"],
                external_id=row["external_id"],
                canonical_url=row["canonical_url"],
                title=row["title"],
                raw_summary=row["raw_summary"],
                raw_content=row["raw_content"],
                published_at=row["published_at"],
                payload=row["payload"] if isinstance(row["payload"], dict) else {},
            )
            enriched_events.append(enrich_event(raw_event, row["id"], embed))

        stats = upsert_enriched_events(engine, enriched_events, batch_size=batch_size)
        total_received += len(enriched_events)
        total_enriched += stats["upserted"]

    return {"received": total_received, "enriched": total_enriched}
