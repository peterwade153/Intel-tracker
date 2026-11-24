from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from tracker.collectors.hacker_news import collect_hacker_news


class _MockResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"{self.status_code}")

    def json(self):
        return self._json


@pytest.fixture
def mock_hn_client(mock_hn_response):
    with patch("httpx.Client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_hn_response
        mock_resp.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        yield


def test_collect_hacker_news_basic(mock_hn_client, mock_hn_response):
    events = collect_hacker_news(min_points=0)
    assert len(events) == 2
    for event in events:
        assert event.source == "hacker_news"
        assert event.lab == "community"


def test_collect_hacker_news_min_points_filter():
    mock_hn_response = {
        "hits": [
            {
                "objectID": "hn_high",
                "title": "High points AI story",
                "url": "https://example.com/high",
                "points": 150,
                "num_comments": 10,
                "created_at": "2026-11-20T10:00:00Z",
            }
        ]
    }
    with patch("httpx.Client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_hn_response
        mock_resp.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        events = collect_hacker_news(min_points=100)
        assert len(events) == 1
        assert events[0].title == "High points AI story"


def test_collect_hacker_news_no_url(mock_hn_client):
    mock_hn_response = {
        "hits": [
            {
                "objectID": "no_url",
                "title": "Story without URL",
                "points": 50,
                "num_comments": 5,
                "created_at": "2026-11-20T10:00:00Z",
            }
        ]
    }
    with patch("httpx.Client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_hn_response
        mock_resp.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        events = collect_hacker_news(min_points=0)
        assert len(events) == 1
        assert str(events[0].canonical_url) == "https://news.ycombinator.com/item?id=no_url"


def test_collect_hacker_news_empty_page():
    with patch("httpx.Client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": []}
        mock_resp.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        events = collect_hacker_news(min_points=0)
        assert len(events) == 0
