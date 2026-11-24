from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from tracker.embeddings.ollama import OllamaEmbedder


class _MockResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"{self.status_code}")

    def json(self):
        return self._json


def test_ollama_embed_success(mock_ollama_embed_response):
    with patch("httpx.Client") as mock_client:
        mock_resp = _MockResp(mock_ollama_embed_response)
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        embedder = OllamaEmbedder(host="http://ollama:11434", model="test-model")
        vector = embedder("test text")
        assert vector == [0.1, 0.2, 0.3]
        assert len(vector) == 3


def test_ollama_embed_404_model_not_found():
    with patch("httpx.Client") as mock_client:
        mock_resp = _MockResp({}, status_code=404)
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        embedder = OllamaEmbedder(host="http://ollama:11434", model="nonexistent")
        from tenacity import RetryError

        with pytest.raises(RetryError):
            embedder("test text")


def test_ollama_embed_retry_on_503(mock_ollama_embed_response):
    with patch("httpx.Client") as mock_client:
        mock_fail = _MockResp({}, status_code=503)
        mock_ok = _MockResp(mock_ollama_embed_response)
        mock_client.return_value.__enter__.return_value.post.side_effect = [
            mock_fail,
            mock_ok,
        ]
        embedder = OllamaEmbedder(host="http://ollama:11434", model="test-model")
        vector = embedder("test text")
        assert vector == [0.1, 0.2, 0.3]


def test_ollama_embed_empty_embeddings():
    with patch("httpx.Client") as mock_client:
        mock_resp = _MockResp({"embeddings": []})
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        embedder = OllamaEmbedder(host="http://ollama:11434", model="test-model")
        with pytest.raises(ValueError, match="no embeddings"):
            embedder("test text")
