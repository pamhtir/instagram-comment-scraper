"""Run bounded staged Instagram collection benchmarks.

Each target is attempted once by default. This records what the currently
available platform path actually delivers; it is not a retry-until-success tool.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from src.cleaners import clean_comments
from src.config import Settings
from src.scrapers import InstagramScraper
from src.models import ScraperError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one bounded attempt per Instagram comment target.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--targets", nargs="+", type=int, default=[100, 500, 1000, 2500, 5000])
    parser.add_argument("--engine", choices=["auto", "http", "browser"], default="auto")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum HTTP pages or Selenium loading rounds per attempt")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-replies", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/benchmarks"))
    args = parser.parse_args()
    if any(target < 1 or target > 100_000 for target in args.targets):
        parser.error("targets must be between 1 and 100000")
    if not 1 <= args.max_pages <= 500:
        parser.error("--max-pages must be between 1 and 500")
    return args


def main() -> int:
    load_dotenv()
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for target in args.targets:
        try:
            scraper = InstagramScraper(Settings.from_env(), args.headless, not args.no_replies, args.engine)
            run = scraper.run(args.url, args.max_pages, target)
            _, clean = clean_comments(run.records)
            metrics = run.metrics.to_dict()
            metrics.update({"raw_records": clean["raw"], "unique_records": clean["final"], "invalid_records": clean["invalid"], "duplicate_records": clean["duplicates"]})
            results.append({"target": target, "status": metrics["status"], "metrics": metrics})
        except (ScraperError, ValueError) as exc:
            results.append({"target": target, "status": "blocked", "error": str(exc)})
    path = args.output / f"instagram_benchmark_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
