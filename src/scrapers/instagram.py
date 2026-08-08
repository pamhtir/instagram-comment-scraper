"""Selenium adapter for authenticated, publicly visible Instagram comments.

Selectors are deliberately scoped to the active comment surface. Extraction uses
the smallest row containing a profile link, preventing a reply username from
being paired with the parent comment's text.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    SessionNotCreatedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Settings
from src.models import AuthenticationRequired, CommentRecord, ContentUnavailable, LayoutChanged

logger = logging.getLogger(__name__)


class InstagramScraper:
    """Collect comments visible in one authenticated browser session."""

    MARKDOWN_URL_RE = re.compile(r"\[(https://(?:www\.)?instagram\.com/(?:p|reel)/[^\s\]/?]+/?)\]\([^)]*\)", re.I)
    PROFILE_LINKS = "a[href^='/'], a[href^='https://www.instagram.com/'], a[href^='https://instagram.com/']"
    META_RE = re.compile(
        r"^(?:[\d,.]+\s*(?:likes?|lượt thích)|view all\s+\d+\s+repl(?:y|ies)|"
        r"xem tất cả\s+\d+\s+(?:câu trả lời|phản hồi)|\d+[smhdw](?:\s*·\s*edited)?|"
        r"\d+\s*(?:giây|phút|giờ|ngày|tuần|second|minute|hour|day|week)s?(?:\s*(?:ago|trước))?)$",
        re.I,
    )
    UI_TEXT = {
        "reply", "like", "likes", "see translation", "follow", "following", "edited",
        "trả lời", "thích", "lượt thích", "xem bản dịch", "theo dõi", "đã chỉnh sửa",
    }
    EXPAND_XPATH = (
        ".//*[@role='button' or self::button]["
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more comments') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'view all comments') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'view replies') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more replies') or "
        "contains(normalize-space(.),'Xem thêm bình luận') or contains(normalize-space(.),'Xem câu trả lời') or "
        "contains(normalize-space(.),'Xem thêm câu trả lời') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ver respuestas') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ver comentarios') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'afficher les réponses') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'afficher les commentaires') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'antworten anzeigen') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'kommentare anzeigen') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ver respostas') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ver comentários') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'lihat balasan') or "
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'lihat komentar')]"
    )

    def __init__(self, settings: Settings, headless: bool = False, replies: bool = True):
        self.settings = settings
        self.headless = headless
        self.replies = replies

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

    def _driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-background-networking")
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={self.settings.profile_dir}")
        options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        try:
            return webdriver.Chrome(options=options)
        except SessionNotCreatedException as exc:
            raise AuthenticationRequired(
                "Chrome could not start. Close other Chrome windows using the scraper profile, then retry."
            ) from exc

    def _pause(self) -> None:
        time.sleep(random.uniform(self.settings.pause_min_seconds, self.settings.pause_max_seconds))

    @staticmethod
    def _visible_text(driver) -> str:
        try:
            return driver.find_element(By.TAG_NAME, "body").text.casefold()
        except Exception:
            return ""

    def _check_access(self, driver) -> None:
        current_url = (driver.current_url or "").casefold()
        text = self._visible_text(driver)
        if "/challenge/" in current_url or "/checkpoint/" in current_url or "confirm it's you" in text:
            raise AuthenticationRequired("Instagram requires verification. Complete it manually in the visible browser and retry.")
        if "log in" in text and "sign up" in text:
            raise AuthenticationRequired("Instagram login is required. Run without --headless and sign in to the dedicated browser profile.")
        unavailable = ("sorry, this page isn't available", "page isn't available", "rất tiếc, trang này hiện không khả dụng")
        if any(message in text for message in unavailable):
            raise ContentUnavailable("The content is private, deleted, invalid, or unavailable to this account.")

    @staticmethod
    def _username_from_href(href: str) -> str | None:
        path = urlparse(href).path if href.startswith("http") else href
        match = re.fullmatch(r"/([A-Za-z0-9._]{1,30})/?", path or "")
        if not match or match.group(1).casefold() in {"p", "reel", "explore", "accounts", "direct", "stories", "about"}:
            return None
        return match.group(1)

    @staticmethod
    def _comment_id(username: str, comment: str, url: str) -> str:
        value = f"instagram|{url}|{username.casefold()}|{comment.strip()}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]

    def _text_is_comment(self, value: str, username: str) -> bool:
        value = " ".join(value.split())
        return bool(value and value.casefold() != username.casefold() and value.casefold() not in self.UI_TEXT and not self.META_RE.fullmatch(value))

    @staticmethod
    def _visible_dialog(driver):
        dialogs = driver.find_elements(By.CSS_SELECTOR, "[role='dialog']")
        for dialog in reversed(dialogs):
            try:
                if dialog.is_displayed():
                    return dialog
            except StaleElementReferenceException:
                pass
        return None

    @classmethod
    def _comment_surface(cls, driver):
        dialog = cls._visible_dialog(driver)
        if dialog is not None:
            return dialog
        # Post pages may expose comments inline instead of in a dialog.
        articles = driver.find_elements(By.TAG_NAME, "article")
        return articles[-1] if articles else None

    def _open_comment_surface(self, driver, content_type: str) -> None:
        if self._comment_surface(driver) is not None and content_type == "post":
            logger.info("Inline Post comments detected")
            return
        buttons = driver.find_elements(
            By.XPATH,
            "//*[name()='svg' and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'comment')]/ancestor::*[@role='button' or self::button][1]",
        )
        for button in buttons:
            try:
                if button.is_displayed():
                    driver.execute_script("arguments[0].click()", button)
                    target = self._visible_dialog if content_type == "reel" else self._comment_surface
                    WebDriverWait(driver, self.settings.wait_seconds).until(lambda d: target(d) is not None)
                    logger.info("Comment surface opened")
                    return
            except Exception as exc:
                logger.debug("Comment button skipped: %s", exc)
        if self._comment_surface(driver) is None:
            raise LayoutChanged("The content opened, but its comment surface was not found. Instagram may have changed its layout.")

    def _recover_comment_surface(self, driver, content_type: str) -> bool:
        """Reacquire a surface replaced by Instagram's client-side rendering."""
        if self._comment_surface(driver) is not None:
            return True
        for attempt in range(1, self.settings.surface_recovery_attempts + 1):
            logger.warning(
                "Comment surface temporarily unavailable; recovery attempt %d/%d",
                attempt,
                self.settings.surface_recovery_attempts,
            )
            try:
                self._check_access(driver)
                self._open_comment_surface(driver, content_type)
                if self._comment_surface(driver) is not None:
                    logger.info("Comment surface recovered")
                    return True
            except (LayoutChanged, StaleElementReferenceException, WebDriverException) as exc:
                logger.debug("Comment surface recovery attempt failed: %s", exc)
            time.sleep(min(1.5 * attempt, 4.0))
        return False

    def _row_for_anchor(self, anchor, username: str):
        """Return the smallest ancestor that owns this username and useful text."""
        node = anchor
        best = None
        for _ in range(9):
            try:
                node = node.find_element(By.XPATH, "..")
                links = node.find_elements(By.CSS_SELECTOR, self.PROFILE_LINKS)
                owners = []
                for link in links:
                    owner = self._username_from_href(link.get_attribute("href") or "")
                    if owner:
                        owners.append(owner.casefold())
                texts = [" ".join((span.text or "").split()) for span in node.find_elements(By.CSS_SELECTOR, "span[dir='auto']")]
                useful = [text for text in texts if self._text_is_comment(text, username)]
                if useful and owners and owners[0] == username.casefold():
                    best = (node, useful)
                    # One owner means an atomic row. Multiple owners usually means a parent + nested replies.
                    if len(set(owners)) == 1:
                        return best
                if len(set(owners)) > 4:
                    break
            except StaleElementReferenceException:
                return None
            except Exception:
                continue
        return best

    def _extract_snapshot(self, driver, url: str, content_type: str) -> dict[str, CommentRecord]:
        surface = self._comment_surface(driver)
        if surface is None:
            raise LayoutChanged("The comment surface disappeared during extraction.")
        found: dict[str, CommentRecord] = {}
        scraped_at = datetime.now(timezone.utc).isoformat()
        # One browser round-trip replaces hundreds of nested Selenium calls. The
        # browser only returns candidate text; validation and IDs stay in Python.
        try:
            candidates = driver.execute_script(
                r"""
            const root=arguments[0], selector=arguments[1], result=[], seen=new Set();
            const usernameFromHref=(href)=>{
              try {
                const path=new URL(href, location.origin).pathname;
                const m=path.match(/^\/([A-Za-z0-9._]{1,30})\/?$/);
                if(!m || ['p','reel','explore','accounts','direct','stories','about'].includes(m[1].toLowerCase())) return null;
                return m[1];
              } catch (_) { return null; }
            };
            for(const anchor of root.querySelectorAll(selector)) {
              if(!anchor.getClientRects().length) continue;
              const username=usernameFromHref(anchor.href || anchor.getAttribute('href') || '');
              if(!username) continue;
              const label=(anchor.innerText || '').trim();
              if(label && label.toLowerCase() !== username.toLowerCase()) continue;
              let node=anchor, best=null;
              for(let depth=0; depth<9 && node.parentElement; depth++) {
                node=node.parentElement;
                const owners=[...node.querySelectorAll(selector)].map(a=>usernameFromHref(a.href || a.getAttribute('href') || '')).filter(Boolean);
                const texts=[...node.querySelectorAll("span[dir='auto']")].map(s=>(s.innerText || '').replace(/\s+/g,' ').trim()).filter(Boolean);
                if(texts.length && owners.length && owners[0].toLowerCase()===username.toLowerCase()) {
                  best={username, texts, ownerCount:new Set(owners.map(x=>x.toLowerCase())).size};
                  if(best.ownerCount===1) break;
                }
                if(new Set(owners.map(x=>x.toLowerCase())).size>4) break;
              }
              if(!best) continue;
              const key=best.username.toLowerCase()+'\u0000'+best.texts.join('\u0001');
              if(!seen.has(key)) { seen.add(key); result.push(best); }
            }
            return result;
                """,
                surface,
                self.PROFILE_LINKS,
            ) or []
        except WebDriverException as exc:
            logger.warning("Fast DOM snapshot unavailable; using compatibility extraction: %s", exc)
            return self._extract_snapshot_legacy(driver, url, content_type)
        for candidate in candidates:
            try:
                username = candidate.get("username")
                if not username:
                    continue
                texts = [" ".join(str(text).split()) for text in candidate.get("texts", [])]
                comment = next((text for text in texts if self._text_is_comment(text, username)), None)
                if not comment:
                    continue
                comment_id = self._comment_id(username, comment, url)
                found[comment_id] = CommentRecord(
                    platform="instagram", content_type=content_type, source_url=url,
                    comment_id=comment_id, username=username, comment=comment,
                    scraped_at_utc=scraped_at, is_reply=False, parent_username="",
                )
            except Exception as exc:
                logger.debug("Comment row skipped: %s", exc)
        return found

    def _extract_snapshot_legacy(self, driver, url: str, content_type: str) -> dict[str, CommentRecord]:
        """Slower Selenium fallback retained for unusual Chrome/DOM variants."""
        surface = self._comment_surface(driver)
        if surface is None:
            raise LayoutChanged("The comment surface disappeared during extraction.")
        found: dict[str, CommentRecord] = {}
        seen_rows: set[str] = set()
        scraped_at = datetime.now(timezone.utc).isoformat()
        for anchor in surface.find_elements(By.CSS_SELECTOR, self.PROFILE_LINKS):
            try:
                if not anchor.is_displayed():
                    continue
                username = self._username_from_href(anchor.get_attribute("href") or "")
                if not username:
                    continue
                label = " ".join((anchor.text or "").split())
                if label and label.casefold() != username.casefold():
                    continue
                row_result = self._row_for_anchor(anchor, username)
                if not row_result:
                    continue
                row, texts = row_result
                row_key = getattr(row, "id", "") or f"{username}:{texts[0]}"
                if row_key in seen_rows:
                    continue
                seen_rows.add(row_key)
                comment = next((text for text in texts if self._text_is_comment(text, username)), None)
                if not comment:
                    continue
                comment_id = self._comment_id(username, comment, url)
                found[comment_id] = CommentRecord(
                    platform="instagram", content_type=content_type, source_url=url,
                    comment_id=comment_id, username=username, comment=comment,
                    scraped_at_utc=scraped_at, is_reply=False, parent_username="",
                )
            except (StaleElementReferenceException, WebDriverException):
                continue
            except Exception as exc:
                logger.debug("Compatibility comment row skipped: %s", exc)
        return found

    def _expand_visible(self, driver) -> int:
        if not self.replies:
            return 0
        surface = self._comment_surface(driver)
        if surface is None:
            return 0
        clicked = 0
        for element in surface.find_elements(By.XPATH, self.EXPAND_XPATH):
            try:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].click()", element)
                    clicked += 1
                    self._pause()
            except Exception as exc:
                logger.debug("Expansion control skipped: %s", exc)
        return clicked

    def _scroll_surface(self, driver) -> dict:
        surface = self._comment_surface(driver)
        if surface is None:
            return {"moved": False}
        return driver.execute_script(
            """
            const root=arguments[0], nodes=[root,...root.querySelectorAll('*')];
            const candidates=nodes.filter(e=>e.scrollHeight>e.clientHeight+80);
            candidates.sort((a,b)=>(b.scrollHeight-b.clientHeight)-(a.scrollHeight-a.clientHeight));
            const target=candidates[0]; if(!target) return {moved:false};
            const before=target.scrollTop, beforeHeight=target.scrollHeight;
            target.scrollTop=target.scrollHeight;
            target.dispatchEvent(new Event('scroll',{bubbles:true}));
            target.dispatchEvent(new WheelEvent('wheel',{deltaY:Math.max(700,target.clientHeight),bubbles:true}));
            return {moved:target.scrollTop!==before, before, after:target.scrollTop, height:beforeHeight};
            """, surface
        ) or {"moved": False}

    def _surface_state(self, driver) -> str | None:
        """Cheap virtualization-safe signal: visible tail content plus scroll geometry."""
        surface = self._comment_surface(driver)
        if surface is None:
            return None
        try:
            return driver.execute_script(
                """
                const root=arguments[0], selector=arguments[1];
                const links=[...root.querySelectorAll(selector)].filter(a=>a.getClientRects().length);
                const tail=links.slice(-4).map(a=>(a.getAttribute('href')||'')+'|'+((a.parentElement?.innerText)||'').slice(0,160)).join('~');
                const scroll=[root,...root.querySelectorAll('*')].filter(e=>e.scrollHeight>e.clientHeight+80).sort((a,b)=>(b.scrollHeight-b.clientHeight)-(a.scrollHeight-a.clientHeight))[0];
                return [links.length,tail,scroll?.scrollTop||0,scroll?.scrollHeight||0].join('::');
                """,
                surface,
                self.PROFILE_LINKS,
            )
        except (StaleElementReferenceException, WebDriverException):
            return None

    def _wait_for_progress(self, driver, previous_state: str | None) -> bool:
        deadline = time.monotonic() + self.settings.load_timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(0.25)
            state = self._surface_state(driver)
            if state is not None and state != previous_state:
                return True
        return False

    def scrape(self, url: str, max_loads: int = 50, max_comments: int | None = None) -> list[dict]:
        clean_url, content_type = self.normalize_url(url)
        driver = self._driver()
        records: dict[str, CommentRecord] = {}
        stable = 0
        try:
            logger.info("Opening %s", clean_url)
            driver.get(clean_url)
            WebDriverWait(driver, self.settings.wait_seconds).until(lambda d: bool(self._visible_text(d).strip()))
            self._check_access(driver)
            self._open_comment_surface(driver, content_type)
            self._pause()
            for round_number in range(1, max_loads + 1):
                self._check_access(driver)
                if not self._recover_comment_surface(driver, content_type):
                    if records:
                        logger.warning(
                            "Comment surface could not be recovered; exporting %d comments already collected",
                            len(records),
                        )
                        break
                    raise LayoutChanged("The comment surface disappeared before any comments could be collected.")
                clicked = self._expand_visible(driver)
                try:
                    snapshot = self._extract_snapshot(driver, clean_url, content_type)
                except LayoutChanged:
                    if self._recover_comment_surface(driver, content_type):
                        snapshot = self._extract_snapshot(driver, clean_url, content_type)
                    elif records:
                        logger.warning(
                            "Comment surface disappeared during extraction; exporting %d comments already collected",
                            len(records),
                        )
                        break
                    else:
                        raise
                before = len(records)
                records.update(snapshot)
                added = len(records) - before
                stable = stable + 1 if added == 0 else 0
                logger.info("Load %d/%d | clicked=%d | new=%d | unique=%d | stable=%d", round_number, max_loads, clicked, added, len(records), stable)
                if max_comments and len(records) >= max_comments:
                    logger.info("Stopping after reaching --max-comments=%d", max_comments)
                    break
                if stable >= self.settings.stable_rounds:
                    logger.info("Stopping after %d stable rounds", stable)
                    break
                previous_state = self._surface_state(driver)
                scroll = self._scroll_surface(driver)
                if scroll.get("moved") and not self._wait_for_progress(driver, previous_state):
                    logger.debug("No DOM/scroll progress before the short load timeout")
                self._pause()
            return [record.to_dict() for record in list(records.values())[:max_comments]]
        except TimeoutException as exc:
            raise ContentUnavailable("Instagram did not finish loading. Check the connection, login, and content visibility.") from exc
        finally:
            driver.quit()
