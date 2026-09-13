# HTTP prototype validation status

## Status: PARTIAL (live platform validation pending)

The dual-engine implementation and offline contract tests are complete. A live
claim about comment volume, speed, or 5,000-comment capability has **not** been
made.

## Blocker

This implementation worker was not given an eligible public Post/Reel URL or an
operator-authorized Instagram session for a real platform run. Instagram can
also return HTTP 401, 403, 429, non-JSON, or a page without an exposed media ID
to ordinary requests; the implementation reports these explicitly and starts no
automatic retry loop.

## Evidence

- `python -m pytest -q` passes the mocked media-ID resolution, cursor
  pagination, target stopping, duplicate counting, partial status, engine
  selection/fallback, and metrics tests.
- `python scripts/smoke_test.py` passes the unchanged raw JSONL -> cleaner ->
  CSV/XLSX pipeline.
- No live HTTP request or benchmark result was used to infer throughput.

## What was tried

The HTTP collector was implemented against an ordinary web-data flow:

1. Fetch the canonical content page and resolve an exposed media identifier.
2. Request comment pages with a cursor (`min_id`) when available.
3. Stop at the requested unique target, exhausted source, repeated cursor, page
   limit, or clear access/rate/platform blocker.

All of these steps are exercised with mocked responses. No CAPTCHA bypass,
credential extraction, stealth mechanism, paid proxy, or paid scraping service
was added.

## Next architecture option

Run the bounded real benchmark first:

```bash
python scripts/benchmark.py --url "https://www.instagram.com/p/SHORTCODE/" --engine http --targets 100 500 1000 2500 5000 --max-pages 100
```

If the HTTP route is blocked, retain the current authorized Selenium engine as
the fallback and record its actual result separately with `--engine browser`.
For a future higher-assurance architecture, evaluate an official, authorized
Meta/Instagram API only if the intended account/use case is eligible; do not
replace the prototype with a paid or protection-bypassing service.
