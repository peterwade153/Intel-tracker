from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from tracker.config import get_env


class OllamaEmbedder:
    """Client for Ollama embedding API.

    Calls POST {host}/api/embed with {"model": <model>, "input": <text>} and
    returns the first embedding vector.
    """

    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        self.host = (host or get_env("OLLAMA_HOST", "http://ollama:11434")).rstrip("/")
        self.model = model or get_env("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
    )
    def __call__(self, text: str) -> list[float]:
        """Return the embedding vector for ``text``."""
        payload = {"model": self.model, "input": text}
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{self.host}/api/embed", json=payload)
            resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if not embeddings:
            raise ValueError(f"Ollama returned no embeddings for model {self.model}")
        return embeddings[0]
