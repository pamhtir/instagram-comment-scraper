# Instagram Comment Scraper & Excel Automation

[![Tests](https://img.shields.io/badge/tests-30%2B_pass-brightgreen)](#quality-assurance) [![Python](https://img.shields.io/badge/Python-3.11--3.13-blue)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A portfolio-grade Python workflow that collects comments visibly loaded from an authorized Instagram Post or Reel, validates and deduplicates the records, and creates client-ready UTF-8 CSV and formatted Excel reports.

> Honest scope: this tool collects comments visible to the authenticated browser session. It does not bypass private accounts, CAPTCHAs, verification, rate limits, or platform access controls, and it cannot guarantee every comment.

## Business problem

Manual comment collection is slow and error-prone. Marketing teams, researchers, and small businesses often need structured data for feedback review, campaign reporting, giveaway administration, or qualitative analysis.

## Solution and proof of work

One command runs an auditable pipeline:

```text
Instagram Post/Reel -> raw JSONL snapshot -> validation -> deduplication -> CSV + Excel + run log
```

The project demonstrates browser automation, defensive extraction, multilingual fallbacks, clean data modeling, spreadsheet automation, tests, logging, privacy-aware packaging, and client-facing documentation.

## Key features

- Supports canonical Instagram `/p/` and `/reel/` URLs.
- Repairs accidentally pasted Markdown links such as `[URL](URL)`, while the documented command always uses a plain URL.
- Uses a dedicated local Chrome profile; credentials are never stored in code.
- Opens Reel comment dialogs and detects inline Post comments.
- Scopes extraction and scrolling to the active comment surface so the Reel feed does not change.
- Uses the smallest owner row to reduce parent-comment/reply username mismatches.
- Prefers language-independent DOM structure, filters common English/Vietnamese metadata, and includes expansion-label fallbacks for English, Vietnamese, Spanish, French, German, Portuguese, and Indonesian.
- Stops on a comment target or configurable stable rounds.
- Offers faster `--no-replies` mode.
- Produces per-run rotating logs and actionable error messages.
- Preserves each run's untouched scraper output as UTF-8 JSONL in `data/raw/`.
- Exports cleaned UTF-8 CSV and a styled XLSX with `Summary` and `Comments` sheets to `data/processed/`.
- Includes offline unit tests; live Instagram is not contacted by the test suite.

## Quick start (Windows + Git Bash)

Use Python 3.11–3.13. This release intentionally stops with a clear message on Python 3.14 instead of failing later inside pandas or pytest.

```bash
py -3.13 -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python scripts/check_environment.py
```

Your prompt must begin with `(.venv)`. If it does not, run `source .venv/Scripts/activate` before scraping or testing. `python -m pytest` uses the active Python; global Python 3.14 cannot see packages installed in this project environment.

Edit `IG_PROFILE_DIR` in `.env`. On the first visible run, sign in manually in the Chrome window. Do not share the profile.

```bash
python main.py --url "https://www.instagram.com/reel/SHORTCODE/" --max-loads 30 --max-comments 500
python main.py --url "https://www.instagram.com/p/SHORTCODE/" --max-loads 30
```

Fast mode without reply expansion:

```bash
python main.py --url "URL" --max-comments 250 --no-replies
```

Run `python main.py --help` for all options. Exit code `0` means success; `2` means user-actionable input/access/no-data; `3` means output permission failure.

## Output schema

| Column | Meaning |
|---|---|
| `platform` | Source platform |
| `content_type` | `post` or `reel` |
| `source_url` | Normalized source URL |
| `comment_id` | Deterministic deduplication key |
| `username` | Visible profile username |
| `comment` | Normalized comment text |
| `is_reply` | Reply flag when confidently detectable |
| `parent_username` | Parent username when confidently detectable |
| `scraped_at_utc` | ISO 8601 UTC collection timestamp |

## Project structure

```text
social-media-comment-scraper/
├── .github/workflows/tests.yml
├── assets/                 # Place the final GIF/screenshot here
├── data/raw/               # Untouched per-run JSONL snapshots, ignored
├── data/processed/         # Cleaned CSV/XLSX exports, ignored
├── demo/                   # Anonymized sample deliverables
├── docs/                   # Architecture, demo, client and support guides
├── logs/                   # Per-run logs, ignored
├── scripts/check_environment.py
├── scripts/smoke_test.py
├── src/
│   ├── scrapers/instagram.py
│   ├── cleaners.py
│   ├── config.py
│   ├── exporters.py
│   └── models.py
├── tests/
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── SECURITY.md
├── main.py
├── pyproject.toml
└── requirements.txt
```

## Quality assurance

```bash
python -m pytest -q
python -m compileall -q main.py src tests
python scripts/smoke_test.py
```

The automated suite validates URL normalization, language-independent metadata filtering, settings validation, stable IDs, cleaning, deduplication, empty results, and both export formats. Because Instagram's DOM changes, complete acceptance also requires the manual matrix in [`docs/testing.md`](docs/testing.md).

## Reliability, language, and speed

The extractor prefers structure (`role`, link shape, dialog/article boundaries, scroll containers) over visible text. English and Vietnamese cover metadata filtering; common expansion labels also cover Spanish, French, German, Portuguese, and Indonesian. No DOM scraper can honestly guarantee every Instagram locale or experiment, so additional languages remain acceptance-test items rather than an unsupported “all languages” claim.

Version 1.1 uses one in-browser DOM snapshot per round and a virtualization-safe progress signal. It jumps the comment panel to its current bottom and waits only briefly for the visible tail or scroll geometry to change. For speed, use `--max-comments`, `--no-replies`, lower stable rounds only after testing, and a dedicated Chrome profile. Accuracy and account safety take priority over parallel tabs. See [`docs/performance.md`](docs/performance.md).

## Security and client-first design

- `.env`, cookies, browser profiles, logs, debug HTML, screenshots, and runtime data are excluded from Git.
- Public samples are synthetic or anonymized.
- Source URL and UTC timestamp make deliveries traceable.
- Invalid and duplicate counts are reported instead of hidden.
- Limitations and acceptance criteria are agreed before work starts.
- Collection requires authorization and must follow applicable terms, privacy requirements, and laws.

Use the [`client handoff checklist`](docs/client-handoff.md) before delivery and read [`SECURITY.md`](SECURITY.md).

## Demo

The repository contains a polished demo script, privacy checklist, shot list, and narration in [`docs/demo-guide.md`](docs/demo-guide.md). Record the real 45–60 second GIF/video only after the manual Post/Reel matrix passes on your own account; a fabricated browser demo is intentionally not included.

## Known limitations

- Instagram can change DOM structure without notice.
- Results vary with ranking, visibility, login state, region, experiments, hidden/deleted comments, and throttling.
- `is_reply` and `parent_username` remain conservative until the DOM exposes a confident relationship.
- Headless mode may behave differently; establish login visibly first.
- This is not an official API client and is not affiliated with Meta or Instagram.

## Roadmap

Completed now and intentionally deferred items are separated in [`docs/roadmap.md`](docs/roadmap.md). The next project should add YouTube as a separate adapter sharing the model, cleaner, and exporters—not mix several immature platform scrapers into this first portfolio release.

## License

MIT. See [`LICENSE`](LICENSE). Responsible use remains the operator's obligation.
