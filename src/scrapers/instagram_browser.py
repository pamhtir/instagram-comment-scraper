"""Compatibility adapter for the existing Selenium implementation."""

from __future__ import annotations

from time import monotonic

from src.config import Settings

from .instagram import InstagramScraper as _LegacySeleniumScraper
from .instagram_base import RunMetrics, ScrapeRun


class BrowserInstagramScraper(_LegacySeleniumScraper):
    """The unchanged Selenium collector exposed through the engine contract."""

    engine_name = "browser"

    def run(self, url: str, max_pages: int = 50, max_comments: int | None = None) -> ScrapeRun:
        started_at = monotonic()
        records = super().scrape(url, max_pages, max_comments)
        unique_records = len({record["comment_id"] for record in records})
        metrics = RunMetrics(
            requested_comments=max_comments,
            raw_records=len(records),
            unique_records=unique_records,
            duplicate_records=len(records) - unique_records,
            engine_used=self.engine_name,
            stop_reason="target_reached" if max_comments and unique_records >= max_comments else "browser_complete",
        )
        metrics.finish(started_at)
        return ScrapeRun(records, metrics)
