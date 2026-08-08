# Changelog

## 1.1.0 - 2026-08-08

- Replaced repeated per-element Selenium extraction with one browser-side DOM snapshot per load round.
- Replaced profile-link-count waits with a virtualization-safe tail/scroll progress signal.
- Scrolls the active comment surface to its current bottom to trigger loading sooner.
- Reduced the default no-progress wait from 12 seconds to 4 seconds.
- Added a clear Python 3.14 preflight failure and `scripts/check_environment.py`.
- Preserved raw JSONL, processed CSV/XLSX, recovery, Post/Reel support, and conservative reply handling.

## [1.0.2] - 2026-08-08

### Fixed

- Persist each scraper result to `data/raw/` as lossless UTF-8 JSON Lines before cleaning.
- Report the raw snapshot path in the terminal and run log.

## [1.0.1] - 2026-08-08

### Fixed

- Recover from transient Instagram comment-panel re-renders instead of failing the entire run.
- Preserve and export comments already collected when a panel cannot be recovered.
- Use a lightweight DOM progress check to prevent extraction waits from taking tens of seconds per round.

## 1.0.0 - 2026-08-08

- Added scoped Post/Reel comment-surface handling.
- Reduced parent/reply username mismatches with atomic-row extraction.
- Added incremental scrolling, explicit waits, targets, reply-free fast mode, and stable stopping.
- Added validated configuration, domain errors, per-run rotating logs, and exit codes.
- Added polished CSV/XLSX delivery, automated tests, CI, security guidance, client checklist, demo plan, testing matrix, and roadmap.
- Removed secrets, virtual environments, runtime data, caches, and debug artifacts from distributable packaging.
