"""Shared contracts for Instagram collection engines.

The HTTP engine deliberately uses only ordinary requests to Instagram's web
surfaces.  It does not create credentials, solve challenges, or attempt to
evade access controls.  The browser engine remains the supported fallback for
an operator's already-authorized session.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from time import monotonic
from typing import Protocol
from urllib.parse import urlparse

from src.models import CommentRecord, ScraperError


class HTTPAccessBlocked(ScraperError):
    """Instagram denied an ordinary unauthenticated HTTP request."""


@dataclass
class RunMetrics:
    requested_comments: int | None
    raw_records: int = 0
    unique_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    elapsed_seconds: float = 0.0
    comments_per_second: float = 0.0
    engine_used: str = ""
    retry_count: int = 0
    stop_reason: str = ""

    @property
    def status(self) -> str:
        """``partial`` makes an unmet requested target explicit to callers."""
        if self.requested_comments is not None and self.unique_records < self.requested_comments:
            return "partial"
        return "complete"

    def finish(self, started_at: float) -> None:
        self.elapsed_seconds = round(monotonic() - started_at, 3)
        self.comments_per_second = round(self.unique_records / self.elapsed_seconds, 3) if self.elapsed_seconds else 0.0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["status"] = self.status
        return payload


@dataclass
class ScrapeRun:
    records: list[dict]
    metrics: RunMetrics


class InstagramEngine(Protocol):
    engine_name: str

    def run(self, url: str, max_pages: int, max_comments: int | None) -> ScrapeRun:
        """Collect a bounded run and return raw records plus transparent metrics."""


class InstagramURL:
    """Canonical URL and stable comment-ID helpers shared by both engines."""

    MARKDOWN_URL_RE = re.compile(r"\[(https://(?:www\.)?instagram\.com/(?:p|reel)/[^\s\]/?]+/?)\]\([^)]*\)", re.I)

    @classmethod
    def normalize_url(cls, value: str) -> tuple[str, str]:
        if not isinstance(value, str):
            raise ValueError("URL must be text")
        value = value.strip()
        match = cls.MARKDOWN_URL_RE.search(value)
        if match:
            value = match.group(1)
        parsed = urlparse(value)
        path = re.fullmatch(r"/(p|reel)/([A-Za-z0-9_-]+)/?", parsed.path)
        if parsed.scheme != "https" or parsed.netloc.casefold() not in {"instagram.com", "www.instagram.com"} or not path:
            raise ValueError("Use a plain Instagram Post or Reel URL, for example https://www.instagram.com/reel/SHORTCODE/")
        kind, shortcode = path.groups()
        return f"https://www.instagram.com/{kind}/{shortcode}/", "post" if kind == "p" else "reel"

    @classmethod
    def validate_url(cls, value: str) -> str:
        return cls.normalize_url(value)[1]

    @staticmethod
    def comment_id(username: str, comment: str, url: str) -> str:
        value = f"instagram|{url}|{username.casefold()}|{comment.strip()}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def record(
        *, url: str, content_type: str, username: str, comment: str, scraped_at_utc: str, comment_id: str | None = None,
        is_reply: bool = False, parent_username: str = "",
    ) -> CommentRecord:
        return CommentRecord(
            platform="instagram", content_type=content_type, source_url=url,
            comment_id=comment_id or InstagramURL.comment_id(username, comment, url),
            username=username, comment=comment, scraped_at_utc=scraped_at_utc,
            is_reply=is_reply, parent_username=parent_username,
        )
