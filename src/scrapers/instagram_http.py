"""Bounded, free HTTP prototype for Instagram comment pagination.

This is intentionally a best-effort adapter. Instagram may require login or
change its internal response shape; those cases become explicit access/platform
blockers and are eligible for the Selenium fallback in auto mode.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from time import monotonic
from typing import Any

import requests

from .instagram_base import HTTPAccessBlocked, InstagramURL, RunMetrics, ScrapeRun

logger = logging.getLogger(__name__)


class HTTPInstagramScraper(InstagramURL):
    engine_name = "http"
    PAGE_URL = "https://www.instagram.com/{kind}/{shortcode}/"
    COMMENTS_URL = "https://www.instagram.com/api/v1/media/{media_id}/comments/"
    MEDIA_ID_PATTERNS = (
        re.compile(r'"media_id"\s*:\s*"?(\d+)"?'),
        re.compile(r'"id"\s*:\s*"?(\d{10,})"?'),
        re.compile(r'"pk"\s*:\s*"?(\d{10,})"?'),
    )

    def __init__(self, session: requests.Session | None = None, timeout_seconds: float = 15.0):
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.session.headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; InstagramCommentExporter/1.2)")
        self.session.headers.setdefault("Accept", "application/json, text/plain, */*")

    def resolve_media_id(self, clean_url: str, content_type: str) -> str:
        shortcode = clean_url.rstrip("/").split("/")[-1]
        try:
            response = self.session.get(self.PAGE_URL.format(kind="p" if content_type == "post" else "reel", shortcode=shortcode), timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise HTTPAccessBlocked(f"HTTP content resolution failed without retrying: {exc}") from exc
        self._raise_for_access(response, "content resolution")
        for pattern in self.MEDIA_ID_PATTERNS:
            match = pattern.search(response.text)
            if match:
                return match.group(1)
        # Next.js pages occasionally encode structured JSON inside script tags.
        for script in re.findall(r"<script[^>]*>(.*?)</script>", response.text, flags=re.S | re.I):
            if "media" not in script:
                continue
            try:
                payload = json.loads(script)
            except json.JSONDecodeError:
                continue
            media_id = self._find_media_id(payload)
            if media_id:
                return media_id
        raise HTTPAccessBlocked("Instagram's public page did not expose a media identifier for HTTP collection.")

    def fetch_page(self, media_id: str, cursor: str | None) -> dict[str, Any]:
        params: dict[str, str] = {"can_support_threading": "true", "permalink_enabled": "false"}
        if cursor:
            params["min_id"] = cursor
        try:
            response = self.session.get(self.COMMENTS_URL.format(media_id=media_id), params=params, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise HTTPAccessBlocked(f"HTTP comment pagination failed without retrying: {exc}") from exc
        self._raise_for_access(response, "comment pagination")
        try:
            payload = response.json()
        except ValueError as exc:
            raise HTTPAccessBlocked("Instagram returned a non-JSON comment page to the HTTP collector.") from exc
        if not isinstance(payload, dict):
            raise HTTPAccessBlocked("Instagram returned an unexpected comment page shape to the HTTP collector.")
        return payload

    @staticmethod
    def _find_media_id(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("media_id", "pk", "id"):
                candidate = value.get(key)
                if isinstance(candidate, (str, int)) and str(candidate).isdigit() and len(str(candidate)) >= 10:
                    return str(candidate)
            for child in value.values():
                result = HTTPInstagramScraper._find_media_id(child)
                if result:
                    return result
        elif isinstance(value, list):
            for child in value:
                result = HTTPInstagramScraper._find_media_id(child)
                if result:
                    return result
        return None

    @staticmethod
    def _raise_for_access(response: requests.Response, phase: str) -> None:
        if response.status_code in {401, 403}:
            raise HTTPAccessBlocked(f"Instagram requires an authorized browser session for {phase} (HTTP {response.status_code}).")
        if response.status_code == 429:
            raise HTTPAccessBlocked("Instagram rate-limited the HTTP collector (HTTP 429); no automatic retry loop was started.")
        if response.status_code >= 400:
            raise HTTPAccessBlocked(f"Instagram rejected {phase} (HTTP {response.status_code}).")

    @staticmethod
    def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        items = payload.get("comments") or payload.get("items") or []
        return items if isinstance(items, list) else []

    @staticmethod
    def _next_cursor(payload: dict[str, Any]) -> str | None:
        value = payload.get("next_min_id") or payload.get("next_cursor")
        return str(value) if value else None

    def _normalize_item(self, item: dict[str, Any], url: str, content_type: str) -> dict | None:
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        username = str(user.get("username") or item.get("username") or "").strip()
        comment = str(item.get("text") or item.get("comment_text") or "").strip()
        if not username or not comment:
            return None
        record_id = str(item.get("pk") or item.get("id") or "").strip() or None
        timestamp = item.get("created_at")
        scraped_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat() if isinstance(timestamp, (int, float)) else datetime.now(timezone.utc).isoformat()
        return self.record(url=url, content_type=content_type, username=username, comment=comment, scraped_at_utc=scraped_at, comment_id=record_id).to_dict()

    def run(self, url: str, max_pages: int = 50, max_comments: int | None = None) -> ScrapeRun:
        clean_url, content_type = self.normalize_url(url)
        started_at = monotonic()
        metrics = RunMetrics(requested_comments=max_comments, engine_used=self.engine_name)
        media_id = self.resolve_media_id(clean_url, content_type)
        records: list[dict] = []
        unique_ids: set[str] = set()
        cursor: str | None = None
        seen_cursors: set[str] = set()
        for page_number in range(1, max_pages + 1):
            payload = self.fetch_page(media_id, cursor)
            items = self._items(payload)
            if not items:
                metrics.stop_reason = "source_exhausted"
                break
            for item in items:
                if not isinstance(item, dict):
                    metrics.invalid_records += 1
                    continue
                record = self._normalize_item(item, clean_url, content_type)
                if record is None:
                    metrics.invalid_records += 1
                    continue
                metrics.raw_records += 1
                records.append(record)
                if record["comment_id"] in unique_ids:
                    metrics.duplicate_records += 1
                unique_ids.add(record["comment_id"])
                if max_comments and len(unique_ids) >= max_comments:
                    metrics.unique_records = len(unique_ids)
                    metrics.stop_reason = "target_reached"
                    metrics.finish(started_at)
                    return ScrapeRun(records, metrics)
            metrics.unique_records = len(unique_ids)
            next_cursor = self._next_cursor(payload)
            logger.info("HTTP page %d/%d | items=%d | unique=%d", page_number, max_pages, len(items), len(unique_ids))
            if not next_cursor:
                metrics.stop_reason = "source_exhausted"
                break
            if next_cursor in seen_cursors:
                metrics.stop_reason = "cursor_repeated"
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        else:
            metrics.stop_reason = "page_limit_reached"
        metrics.unique_records = len(unique_ids)
        metrics.finish(started_at)
        return ScrapeRun(records, metrics)
