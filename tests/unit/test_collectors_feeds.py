from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from tracker.collectors.feeds import FEED_SOURCES, collect_feed


class _MockEntry:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _MockFeed:
    def __init__(self, entries):
        self.entries = [_MockEntry(e) for e in entries]


@pytest.fixture
def mock_rss_response(mock_rss_feed):
    with patch("feedparser.parse") as mock_parse:
        mock_parse.return_value = _MockFeed(
            [
                {
                    "title": "Test AI Release",
                    "link": "https://example.com/release-1",
                    "guid": "https://example.com/release-1",
                    "published": "Mon, 23 Nov 2026 10:00:00 GMT",
                    "summary": "Summary text for release 1",
                },
                {
                    "title": "Second Release",
                    "link": "https://example.com/release-2",
                    "guid": "https://example.com/release-2",
                    "published": "Mon, 23 Nov 2026 09:00:00 GMT",
                    "summary": "Summary text for release 2",
                },
                {
                    "title": "No Link Item",
                    "guid": "https://example.com/no-link",
                },
            ]
        )
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.text = mock_rss_feed
            mock_resp.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            yield


def test_feed_sources_contains_expected_keys():
    assert "openai_news" in FEED_SOURCES
    assert "google_deepmind" in FEED_SOURCES
    assert "liquid_ai" in FEED_SOURCES


def test_collect_feed_openai(mock_rss_response):
    events = collect_feed("openai_news")
    assert len(events) == 2  # Third entry has no link, skipped
    for event in events:
        assert event.source == "openai_news"
        assert event.lab == "openai"


def test_collect_feed_google_deepmind(mock_rss_response):
    events = collect_feed("google_deepmind")
    assert len(events) == 2
    for event in events:
        assert event.source == "google_deepmind"
        assert event.lab == "google_deepmind"


def test_collect_feed_liquid_ai(mock_rss_response):
    events = collect_feed("liquid_ai")
    assert len(events) == 2
    for event in events:
        assert event.source == "liquid_ai"
        assert event.lab == "liquid_ai"


def test_collect_feed_unknown_source():
    with pytest.raises(ValueError, match="Unknown feed source"):
        collect_feed("nonexistent_source")


def test_collect_feed_http_retry(mock_rss_feed):
    with patch("feedparser.parse") as mock_parse:
        mock_parse.return_value = _MockFeed([])
        with patch("httpx.Client") as mock_client:
            # First call raises, second succeeds
            mock_resp_fail = MagicMock()
            mock_resp_fail.raise_for_status.side_effect = httpx.HTTPError("503")
            mock_resp_ok = MagicMock()
            mock_resp_ok.text = mock_rss_feed
            mock_resp_ok.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get.side_effect = [
                mock_resp_fail,
                mock_resp_ok,
            ]
            events = collect_feed("openai_news")
            assert len(events) == 0  # No entries in mock feed
