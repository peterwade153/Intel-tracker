from __future__ import annotations

import logging

import httpx
import trafilatura
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
)
def fetch_html(url: str, timeout: float = 20.0) -> str:
    """Fetch raw HTML from a URL with retry on transient errors."""
    headers = {"User-Agent": "AILabTracker/0.1"}
    logger.info("Fetching HTML: %s", url)
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        logger.info("Fetched HTML: %s (status=%d, bytes=%d)", url, resp.status_code, len(resp.text))
        return resp.text


def extract_content(html: str, url: str) -> str | None:
    """Extract the main article body from HTML using trafilatura.

    Returns the cleaned text, or None if extraction fails.
    """
    if not html:
        return None
    try:
        return trafilatura.extract(html, url=url)
    except Exception:  # noqa: BLE001 - graceful fallback for dead URLs
        return None


def extract_and_clean(url: str) -> str | None:
    """Fetch a URL and return its cleaned main-text content.

    Returns None if the page cannot be fetched or parsed, so callers can
    fall back to the raw RSS summary instead of crashing the batch.
    """
    try:
        html = fetch_html(url)
    except Exception:  # noqa: BLE001 - graceful fallback for dead URLs
        logger.warning("Failed to fetch HTML for %s", url)
        return None
    content = extract_content(html, url)
    if content is None:
        logger.warning("Content extraction returned None for %s", url)
    else:
        logger.info("Extracted %d chars of content from %s", len(content), url)
    return content
