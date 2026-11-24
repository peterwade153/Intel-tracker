from __future__ import annotations

from datetime import UTC, datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from tracker.storage.db import RawEvent

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
AI_QUERY = "OpenAI OR Anthropic OR DeepMind OR Liquid AI OR LLM OR vLLM OR weights"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
)
def _fetch_page(
    client: httpx.Client,
    params: dict,
    page: int,
) -> dict:
    page_params = {**params, "page": page}
    resp = client.get(HN_SEARCH_URL, params=page_params)
    resp.raise_for_status()
    return resp.json()


def collect_hacker_news(
    min_points: int = 25,
    hits_per_page: int = 30,
    max_pages: int = 5,
) -> list[RawEvent]:
    params = {
        "query": AI_QUERY,
        "tags": "story",
        "numericFilters": f"points>={min_points}",
        "hitsPerPage": hits_per_page,
    }

    events: list[RawEvent] = []
    with httpx.Client(timeout=20.0) as client:
        for page in range(max_pages):
            data = _fetch_page(client, params, page)
            hits = data.get("hits", [])
            if not hits:
                break

            for hit in hits:
                object_id = hit.get("objectID")
                title = hit.get("title")
                url = hit.get("url") or (
                    f"https://news.ycombinator.com/item?id={object_id}" if object_id else None
                )
                if not title or not url:
                    continue

                created_at = hit.get("created_at")
                published_at = None
                if created_at:
                    published_at = datetime.fromisoformat(created_at).astimezone(UTC)

                events.append(
                    RawEvent(
                        source="hacker_news",
                        lab="community",
                        external_id=str(object_id) if object_id else None,
                        canonical_url=url,  # type: ignore[arg-type]  # Pydantic coerces str to HttpUrl
                        title=title,
                        raw_summary=f"HN points: {hit.get('points', 0)} | comments: {hit.get('num_comments', 0)}",
                        published_at=published_at,
                        payload={
                            "hn_id": object_id,
                            "hn_url": f"https://news.ycombinator.com/item?id={object_id}",
                            "points": hit.get("points", 0),
                            "num_comments": hit.get("num_comments", 0),
                        },
                    )
                )

            if len(hits) < hits_per_page:
                break

    return events
