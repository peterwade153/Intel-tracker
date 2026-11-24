from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from tracker.config import get_tracker_database_url


class RawEvent(BaseModel):
    source: str
    lab: str
    external_id: str | None = None
    canonical_url: HttpUrl
    title: str
    raw_summary: str | None = None
    raw_content: str | None = None
    published_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        digest_input = f"{self.title}|{self.raw_summary or ''}|{self.raw_content or ''}"
        return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

def get_engine(database_url: str | None = None) -> Engine:
    url = get_tracker_database_url(database_url)
    return create_engine(url, pool_pre_ping=True)

def upsert_raw_events(engine: Engine, events: list[RawEvent], batch_size: int = 500) -> dict[str, int]:
    """Idempotently insert or update raw events keyed by canonical_url.

    Events are processed in batches to avoid large single-transaction payloads.
    """
    if not events:
        return {"received": 0, "upserted": 0}

    sql = text(
        """
        INSERT INTO raw_events (
            source, lab, external_id, canonical_url, title,
            raw_summary, raw_content, content_hash, published_at, payload
        )
        VALUES (
            :source, :lab, :external_id, :canonical_url, :title,
            :raw_summary, :raw_content, :content_hash, :published_at, CAST(:payload AS jsonb)
        )
        ON CONFLICT (canonical_url) DO UPDATE SET
            title = EXCLUDED.title,
            raw_summary = EXCLUDED.raw_summary,
            raw_content = COALESCE(EXCLUDED.raw_content, raw_events.raw_content),
            content_hash = EXCLUDED.content_hash,
            published_at = COALESCE(EXCLUDED.published_at, raw_events.published_at),
            fetched_at = NOW(),
            payload = raw_events.payload || EXCLUDED.payload
        WHERE raw_events.content_hash IS DISTINCT FROM EXCLUDED.content_hash
        """
    )

    rows = [
        {
            "source": e.source,
            "lab": e.lab,
            "external_id": e.external_id,
            "canonical_url": str(e.canonical_url),
            "title": e.title.strip(),
            "raw_summary": e.raw_summary,
            "raw_content": e.raw_content,
            "content_hash": e.content_hash,
            "published_at": e.published_at,
            "payload": json.dumps(e.payload, default=str),
        }
        for e in events
    ]

    upserted = 0
    with engine.begin() as conn:
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            for row in batch:
                result = conn.execute(sql, row)
                upserted += result.rowcount or 0

    return {"received": len(rows), "upserted": upserted}
