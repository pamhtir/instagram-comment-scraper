from __future__ import annotations

import pytest

from src.scrapers import InstagramScraper
from src.scrapers.instagram_base import HTTPAccessBlocked, RunMetrics, ScrapeRun
from src.scrapers.instagram_http import HTTPInstagramScraper


def _item(identifier: str, username: str = "alice", text: str = "hello") -> dict:
    return {"pk": identifier, "text": text, "user": {"username": username}, "created_at": 1_700_000_000}


def test_http_resolves_media_identifier_from_mocked_content_page(monkeypatch):
    class Response:
        status_code = 200
        text = '<html><script>{"media_id":"123456789012"}</script></html>'

    scraper = HTTPInstagramScraper()
    monkeypatch.setattr(scraper.session, "get", lambda *args, **kwargs: Response())
    assert scraper.resolve_media_id("https://www.instagram.com/p/ABC/", "post") == "123456789012"


def test_http_paginates_with_cursor_and_records_metrics(monkeypatch):
    scraper = HTTPInstagramScraper()
    pages = iter([
        {"comments": [_item("1"), _item("2", "bob")], "next_min_id": "cursor-2"},
        {"comments": [_item("3", "carol")], "next_min_id": None},
    ])
    cursors = []
    monkeypatch.setattr(scraper, "resolve_media_id", lambda url, kind: "123456789012")
    monkeypatch.setattr(scraper, "fetch_page", lambda media_id, cursor: cursors.append(cursor) or next(pages))

    run = scraper.run("https://www.instagram.com/p/ABC/", max_pages=10)

    assert cursors == [None, "cursor-2"]
    assert len(run.records) == 3
    assert run.metrics.raw_records == 3
    assert run.metrics.unique_records == 3
    assert run.metrics.stop_reason == "source_exhausted"
    assert run.metrics.engine_used == "http"


def test_http_stops_immediately_at_unique_target(monkeypatch):
    scraper = HTTPInstagramScraper()
    monkeypatch.setattr(scraper, "resolve_media_id", lambda url, kind: "123456789012")
    monkeypatch.setattr(scraper, "fetch_page", lambda media_id, cursor: {"comments": [_item("1"), _item("2"), _item("3")], "next_min_id": "next"})

    run = scraper.run("https://www.instagram.com/reel/ABC/", max_pages=10, max_comments=2)

    assert len(run.records) == 2
    assert run.metrics.unique_records == 2
    assert run.metrics.stop_reason == "target_reached"


def test_http_counts_duplicate_raw_records_and_prevents_cursor_loop(monkeypatch):
    scraper = HTTPInstagramScraper()
    pages = iter([
        {"comments": [_item("1"), _item("1")], "next_min_id": "same"},
        {"comments": [_item("2")], "next_min_id": "same"},
    ])
    monkeypatch.setattr(scraper, "resolve_media_id", lambda url, kind: "123456789012")
    monkeypatch.setattr(scraper, "fetch_page", lambda media_id, cursor: next(pages))

    run = scraper.run("https://www.instagram.com/p/ABC/", max_pages=10)

    assert run.metrics.raw_records == 3
    assert run.metrics.unique_records == 2
    assert run.metrics.duplicate_records == 1
    assert run.metrics.stop_reason == "cursor_repeated"


def test_unmet_target_has_explicit_partial_status(monkeypatch):
    scraper = HTTPInstagramScraper()
    monkeypatch.setattr(scraper, "resolve_media_id", lambda url, kind: "123456789012")
    monkeypatch.setattr(scraper, "fetch_page", lambda media_id, cursor: {"comments": [_item("1")], "next_min_id": None})

    run = scraper.run("https://www.instagram.com/p/ABC/", max_pages=1, max_comments=100)

    assert run.metrics.stop_reason == "source_exhausted"
    assert run.metrics.status == "partial"
    assert run.metrics.to_dict()["status"] == "partial"


def test_auto_engine_falls_back_only_after_clear_http_blocker(settings, monkeypatch):
    class BlockedHTTP:
        def run(self, *args, **kwargs):
            raise HTTPAccessBlocked("HTTP 403")

    class Browser:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, *args, **kwargs):
            return ScrapeRun([], RunMetrics(requested_comments=None, engine_used="browser", stop_reason="browser_complete"))

    monkeypatch.setattr("src.scrapers.HTTPInstagramScraper", BlockedHTTP)
    monkeypatch.setattr("src.scrapers.BrowserInstagramScraper", Browser)
    run = InstagramScraper(settings, engine="auto").run("https://www.instagram.com/p/ABC/")
    assert run.metrics.engine_used == "browser_fallback"


def test_explicit_http_does_not_silently_switch_to_browser(settings, monkeypatch):
    class BlockedHTTP:
        def run(self, *args, **kwargs):
            raise HTTPAccessBlocked("HTTP 403")

    monkeypatch.setattr("src.scrapers.HTTPInstagramScraper", BlockedHTTP)
    with pytest.raises(HTTPAccessBlocked):
        InstagramScraper(settings, engine="http").run("https://www.instagram.com/p/ABC/")
