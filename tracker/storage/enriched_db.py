from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import text
from sqlalchemy.engine import Engine


class EnrichedEvent(BaseModel):
    raw_event_id: int
    source: str
    lab: str
    canonical_url: HttpUrl
    title: str
    category: str = "uncategorized"
    summary: str | None = None
    impact_score: int | None = None
    published_at: datetime | None = None
    enriched_at: datetime
    embedding: list[float] = Field(default_factory=lambda: [0.0] * 768)


def upsert_enriched_events(engine: Engine, events: list[EnrichedEvent], batch_size: int = 100) -> dict[str, int]:
    """Idempotently insert or update enriched events keyed by canonical_url."""
    if not events:
        return {"received": 0, "upserted": 0}

    sql = text(
        """
        INSERT INTO ai_events (
            raw_event_id, source, lab, canonical_url, title,
            category, summary, impact_score, published_at, enriched_at, embedding
        )
        VALUES (
            :raw_event_id, :source, :lab, :canonical_url, :title,
            :category, :summary, :impact_score, :published_at, :enriched_at,
            CAST(:embedding AS vector)
        )
        ON CONFLICT (canonical_url) DO UPDATE SET
            title = EXCLUDED.title,
            category = EXCLUDED.category,
            summary = EXCLUDED.summary,
            impact_score = EXCLUDED.impact_score,
            published_at = COALESCE(EXCLUDED.published_at, ai_events.published_at),
            enriched_at = EXCLUDED.enriched_at,
            embedding = EXCLUDED.embedding,
            updated_at = NOW()
        WHERE ai_events.embedding IS DISTINCT FROM EXCLUDED.embedding
           OR ai_events.summary IS DISTINCT FROM EXCLUDED.summary
        """
    )

    rows = []
    for e in events:
        rows.append({
            "raw_event_id": e.raw_event_id,
            "source": e.source,
            "lab": e.lab,
            "canonical_url": str(e.canonical_url),
            "title": e.title.strip(),
            "category": e.category,
            "summary": e.summary,
            "impact_score": e.impact_score,
            "published_at": e.published_at,
            "enriched_at": e.enriched_at,
            "embedding": f"[{','.join(str(v) for v in e.embedding)}]",
        })

    upserted = 0
    with engine.begin() as conn:
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            for row in batch:
                result = conn.execute(sql, row)
                upserted += result.rowcount or 0

    return {"received": len(rows), "upserted": upserted}
