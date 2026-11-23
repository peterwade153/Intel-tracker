from __future__ import annotations

from tracker.collectors.feeds import FEED_SOURCES, collect_feed
from tracker.collectors.hacker_news import collect_hacker_news
from tracker.storage.db import RawEvent, get_engine, upsert_raw_events

ALL_PHASE1_SOURCES = [*FEED_SOURCES.keys(), "hacker_news"]


def run_source_ingestion(source: str) -> dict[str, int | str]:
    if source in FEED_SOURCES:
        events: list[RawEvent] = collect_feed(source)
    elif source == "hacker_news":
        events = collect_hacker_news()
    else:
        raise ValueError(f"Unsupported Phase 1 source: {source}")

    engine = get_engine()
    stats = upsert_raw_events(engine, events)
    return {"source": source, **stats}
