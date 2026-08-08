# Architecture

```text
CLI + validated settings
          |
Instagram adapter (Post/Reel)
          |
standard CommentRecord objects
          |
shared cleaner and deduplicator
          |
CSV + Excel + run log
```

Platform-specific browser behavior stays in `src/scrapers/instagram.py`. The model, cleaner, and exporters are platform-neutral enough to reuse later. A future network should receive its own adapter and tests; only the requested adapter should be instantiated, so adding adapters does not inherently slow an Instagram run.

The scraper uses a dedicated authenticated Chrome profile, scopes DOM work to the active comment surface, extracts atomic username/text rows, caches deterministic IDs, and advances the best scrollable descendant in small steps.
