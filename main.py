"""Command-line entry point for the Instagram comment export pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

if not (sys.version_info[:2] >= (3, 11) and sys.version_info[:2] < (3, 14)):
    raise SystemExit(
        "This project requires Python 3.11-3.13. You are running "
        f"Python {sys.version_info.major}.{sys.version_info.minor}. "
        "On Windows, install Python 3.13 and run: py -3.13 -m venv .venv"
    )

from dotenv import load_dotenv

from src.cleaners import clean_comments
from src.config import Settings
from src.exporters import export_raw_records, export_results
from src.models import ScraperError
from src.scrapers import InstagramScraper


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect visible Instagram Post/Reel comments and export CSV/XLSX.")
    parser.add_argument("--url", required=True, help="Plain Instagram /p/ or /reel/ URL")
    parser.add_argument("--max-loads", type=int, default=30, help="Maximum loading rounds (1-500)")
    parser.add_argument("--max-comments", type=int, default=None, help="Stop after this many unique comments")
    parser.add_argument("--output", type=Path, default=None, help="Output filename stem")
    parser.add_argument("--headless", action="store_true", help="Run Chrome without a visible window (after login is established)")
    parser.add_argument("--no-replies", action="store_true", help="Skip reply expansion for a faster run")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args(argv)
    if not 1 <= args.max_loads <= 500:
        parser.error("--max-loads must be between 1 and 500")
    if args.max_comments is not None and not 1 <= args.max_comments <= 100_000:
        parser.error("--max-comments must be between 1 and 100000")
    return args


def setup_logging(level: str, run_id: str) -> Path:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"scraper_{run_id}.log"
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    stream_handler = logging.StreamHandler()
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logging.basicConfig(level=getattr(logging, level), handlers=[file_handler, stream_handler], force=True)
    return log_path


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = setup_logging(args.log_level, run_id)
    logger = logging.getLogger(__name__)
    output = (args.output or Path("data/processed") / f"instagram_comments_{run_id}").with_suffix("")
    raw_output = Path("data/raw") / f"instagram_comments_raw_{run_id}.jsonl"
    try:
        settings = Settings.from_env()
        raw = InstagramScraper(settings, headless=args.headless, replies=not args.no_replies).scrape(
            args.url, args.max_loads, args.max_comments
        )
        raw_path = export_raw_records(raw, raw_output)
        cleaned, metrics = clean_comments(raw)
        csv_path, xlsx_path = export_results(cleaned, metrics, output)
        logger.info("Complete | raw=%d invalid=%d duplicates=%d final=%d", metrics["raw"], metrics["invalid"], metrics["duplicates"], metrics["final"])
        logger.info("Raw: %s", raw_path)
        logger.info("CSV: %s", csv_path)
        logger.info("Excel: %s", xlsx_path)
        logger.info("Log: %s", log_path)
        if cleaned.empty:
            logger.warning("No visible comments were collected. See docs/troubleshooting.md.")
            return 2
        return 0
    except (ValueError, ScraperError) as exc:
        logger.error("%s", exc)
        logger.info("Troubleshooting: docs/troubleshooting.md")
        return 2
    except KeyboardInterrupt:
        logger.warning("Stopped by user. The browser will close safely.")
        return 130
    except PermissionError as exc:
        logger.error("Could not write the output. Close the CSV/XLSX if it is open and retry: %s", exc)
        return 3
    except Exception:
        logger.exception("Unexpected pipeline failure")
        return 1


if __name__ == "__main__":
    sys.exit(main())
