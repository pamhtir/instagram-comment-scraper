"""Instagram engine selection with a transparent browser fallback."""

from __future__ import annotations

from src.config import Settings

from .instagram_base import HTTPAccessBlocked, ScrapeRun
from .instagram_browser import BrowserInstagramScraper
from .instagram_http import HTTPInstagramScraper


class InstagramScraper:
    """Facade preserving ``scrape`` while exposing ``run`` metrics."""

    def __init__(self, settings: Settings, headless: bool = False, replies: bool = True, engine: str = "auto"):
        if engine not in {"auto", "http", "browser"}:
            raise ValueError("engine must be auto, http, or browser")
        self.settings = settings
        self.headless = headless
        self.replies = replies
        self.engine = engine
        self.last_run: ScrapeRun | None = None

    def run(self, url: str, max_loads: int = 50, max_comments: int | None = None) -> ScrapeRun:
        if self.engine == "browser":
            run = BrowserInstagramScraper(self.settings, self.headless, self.replies).run(url, max_loads, max_comments)
        elif self.engine == "http":
            run = HTTPInstagramScraper().run(url, max_loads, max_comments)
        else:
            try:
                run = HTTPInstagramScraper().run(url, max_loads, max_comments)
            except HTTPAccessBlocked:
                run = BrowserInstagramScraper(self.settings, self.headless, self.replies).run(url, max_loads, max_comments)
                run.metrics.engine_used = "browser_fallback"
        self.last_run = run
        return run

    def scrape(self, url: str, max_loads: int = 50, max_comments: int | None = None) -> list[dict]:
        return self.run(url, max_loads, max_comments).records


__all__ = ["InstagramScraper", "BrowserInstagramScraper", "HTTPInstagramScraper", "HTTPAccessBlocked"]
