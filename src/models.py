"""Shared records and domain-specific exceptions."""

from dataclasses import asdict, dataclass


class ScraperError(RuntimeError):
    """A user-actionable scraping failure."""


class AuthenticationRequired(ScraperError):
    pass


class ContentUnavailable(ScraperError):
    pass


class LayoutChanged(ScraperError):
    pass


@dataclass(frozen=True)
class CommentRecord:
    platform: str
    content_type: str
    source_url: str
    comment_id: str
    username: str
    comment: str
    scraped_at_utc: str
    is_reply: bool = False
    parent_username: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
