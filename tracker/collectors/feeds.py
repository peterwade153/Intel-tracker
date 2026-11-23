from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import feedparser
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from tracker.storage.db import RawEvent

FEED_SOURCES: dict[str, tuple[str, str]] = {
    "openai_news": ("openai", "https://openai.com/news/rss.xml"), #
    "google_deepmind": ("google_deepmind", "https://deepmind.google/blog/feed/basic/"),
}


def _parse_published(entry: dict) -> datetime | None:
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
)
def _fetch_xml(url: str) -> str:
    headers = {"User-Agent": "AILabTracker/0.1"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text

def collect_feed(source_key: str) -> list[RawEvent]:
    if source_key not in FEED_SOURCES:
        raise ValueError(f"Unknown feed source: {source_key}")

    lab, url = FEED_SOURCES[source_key]
    xml_text = _fetch_xml(url)
    parsed = feedparser.parse(xml_text)

    events: list[RawEvent] = []
    for entry in parsed.entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue

        summary = entry.get("summary") or entry.get("description")
        events.append(
            RawEvent(
                source=source_key,
                lab=lab,
                external_id=entry.get("id") or entry.get("guid") or link,
                canonical_url=link,
                title=title,
                raw_summary=summary,
                published_at=_parse_published(entry),
                payload={"feed_url": url},
            )
        )
    return events
