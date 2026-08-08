import pytest

from src.scrapers.instagram import InstagramScraper


@pytest.mark.parametrize(("url", "clean", "kind"), [
    ("https://www.instagram.com/p/Dbtxr6hsgOC/", "https://www.instagram.com/p/Dbtxr6hsgOC/", "post"),
    ("https://instagram.com/reel/ABC_123", "https://www.instagram.com/reel/ABC_123/", "reel"),
    ("[https://www.instagram.com/reel/ABC/](https://www.instagram.com/reel/ABC/)", "https://www.instagram.com/reel/ABC/", "reel"),
])
def test_normalizes_supported_urls(url, clean, kind):
    assert InstagramScraper.normalize_url(url) == (clean, kind)


@pytest.mark.parametrize("url", ["https://example.com/p/ABC/", "http://www.instagram.com/p/ABC/", "https://www.instagram.com/explore/", ""])
def test_rejects_unsupported_urls(url):
    with pytest.raises(ValueError, match="Instagram Post or Reel"):
        InstagramScraper.normalize_url(url)


@pytest.mark.parametrize(("href", "username"), [
    ("/demo.user/", "demo.user"),
    ("https://www.instagram.com/demo_user/", "demo_user"),
    ("/reel/", None),
    ("/bad user/", None),
])
def test_extracts_only_profile_usernames(href, username):
    assert InstagramScraper._username_from_href(href) == username


def test_comment_ids_are_stable_and_user_specific():
    first = InstagramScraper._comment_id("alice", "Hello", "https://www.instagram.com/p/X/")
    assert first == InstagramScraper._comment_id("alice", "Hello", "https://www.instagram.com/p/X/")
    assert first != InstagramScraper._comment_id("bob", "Hello", "https://www.instagram.com/p/X/")


@pytest.mark.parametrize("text", ["510 likes", "View all 30 replies", "2w · Edited", "1 day ago"])
def test_filters_interface_metadata(settings, text):
    scraper = InstagramScraper(settings)
    assert not scraper._text_is_comment(text, "alice")


def test_keeps_normal_comment(settings):
    assert InstagramScraper(settings)._text_is_comment("Great analysis!", "alice")


def test_recovery_succeeds_when_surface_reappears(settings, monkeypatch):
    scraper = InstagramScraper(settings)
    surfaces = iter([None, None, object()])
    monkeypatch.setattr(scraper, "_comment_surface", lambda driver: next(surfaces))
    monkeypatch.setattr(scraper, "_check_access", lambda driver: None)
    monkeypatch.setattr(scraper, "_open_comment_surface", lambda driver, kind: None)
    monkeypatch.setattr("src.scrapers.instagram.time.sleep", lambda seconds: None)
    assert scraper._recover_comment_surface(object(), "reel") is True


def test_recovery_is_bounded_when_surface_stays_missing(settings, monkeypatch):
    scraper = InstagramScraper(settings)
    attempts = []
    monkeypatch.setattr(scraper, "_comment_surface", lambda driver: None)
    monkeypatch.setattr(scraper, "_check_access", lambda driver: None)
    monkeypatch.setattr(scraper, "_open_comment_surface", lambda driver, kind: attempts.append(kind))
    monkeypatch.setattr("src.scrapers.instagram.time.sleep", lambda seconds: None)
    assert scraper._recover_comment_surface(object(), "reel") is False
    assert len(attempts) == settings.surface_recovery_attempts


def test_fast_snapshot_builds_records_in_one_browser_call(settings, monkeypatch):
    scraper = InstagramScraper(settings)

    class Driver:
        def execute_script(self, script, surface, selector):
            return [{"username": "alice", "texts": ["alice", "Fast and accurate!"], "ownerCount": 1}]

    monkeypatch.setattr(scraper, "_comment_surface", lambda driver: object())
    records = scraper._extract_snapshot(Driver(), "https://www.instagram.com/reel/ABC/", "reel")
    record = next(iter(records.values()))
    assert record.username == "alice"
    assert record.comment == "Fast and accurate!"


def test_fast_snapshot_still_filters_interface_metadata(settings, monkeypatch):
    scraper = InstagramScraper(settings)

    class Driver:
        def execute_script(self, script, surface, selector):
            return [{"username": "alice", "texts": ["510 likes"], "ownerCount": 1}]

    monkeypatch.setattr(scraper, "_comment_surface", lambda driver: object())
    assert scraper._extract_snapshot(Driver(), "https://www.instagram.com/p/ABC/", "post") == {}
