# Architecture

```text
CLI + validated settings
          |
Instagram engine facade (Post/Reel)
          |-- HTTP prototype: resolve media ID -> cursor pages
          `-- Selenium browser fallback: authorized visible comments
          |
standard CommentRecord objects
          |
shared cleaner and deduplicator
          |
CSV + Excel + run log
```

`src/scrapers/instagram.py` retains the original browser behavior. The facade in `src/scrapers/__init__.py` selects `http`, `browser`, or `auto`; auto falls back only after an explicit HTTP access/platform blocker. `instagram_http.py` uses a normal, bounded request flow: resolve a media ID from the content page and read cursor-bearing comment pages when Instagram makes that path accessible. It does not bypass authentication, CAPTCHA, rate limiting, or platform protections.

Every run carries `RunMetrics` (requested/raw/unique/invalid/duplicate counts, elapsed time, rate, engine, retry count and stop reason). The existing model, cleaner, raw JSONL persistence and exporters remain downstream-compatible.

The scraper uses a dedicated authenticated Chrome profile, scopes DOM work to the active comment surface, extracts atomic username/text rows, caches deterministic IDs, and advances the best scrollable descendant in small steps.
