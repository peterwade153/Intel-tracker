from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from tracker.extractors.content import extract_and_clean, extract_content, fetch_html


class _MockResp:
    def __init__(self, text="<html><body>Article content</body></html>", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"{self.status_code}")


def test_fetch_html_success():
    with patch("httpx.Client") as mock_client:
        mock_resp = _MockResp()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        html = fetch_html("https://example.com/article")
        assert "Article content" in html


def test_fetch_html_404():
    with patch("httpx.Client") as mock_client:
        mock_resp = _MockResp(status_code=404)
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        with pytest.raises(httpx.HTTPError):
            fetch_html("https://example.com/missing")


def test_extract_content_success():
    html = "<html><body><article>Main article text here</article></body></html>"
    result = extract_content(html, "https://example.com/article")
    assert result is not None
    assert "Main article text" in result


def test_extract_content_empty_html():
    assert extract_content("", "https://example.com/article") is None


def test_extract_and_clean_success():
    with patch("tracker.extractors.content.fetch_html") as mock_fetch:
        mock_fetch.return_value = "<html><body>Article body</body></html>"
        with patch(
            "tracker.extractors.content.trafilatura.extract", return_value="Article body"
        ):
            result = extract_and_clean("https://example.com/article")
            assert result == "Article body"


def test_extract_and_clean_404_returns_none():
    with patch("tracker.extractors.content.fetch_html") as mock_fetch:
        mock_fetch.side_effect = httpx.HTTPError("404")
        result = extract_and_clean("https://example.com/missing")
        assert result is None


def test_extract_and_clean_timeout_returns_none():
    with patch("tracker.extractors.content.fetch_html") as mock_fetch:
        mock_fetch.side_effect = httpx.TimeoutException("timeout")
        result = extract_and_clean("https://example.com/slow")
        assert result is None
