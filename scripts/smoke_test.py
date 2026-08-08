"""Fast offline installation check for beginners."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cleaners import ORDERED_COLUMNS, clean_comments
from src.exporters import export_raw_records, export_results
from src.scrapers.instagram import InstagramScraper


def main() -> None:
    url, kind = InstagramScraper.normalize_url("https://www.instagram.com/reel/DEMO/")
    record = dict(zip(ORDERED_COLUMNS, ["instagram", kind, url, "demo-id", "demo.user", "Synthetic portfolio sample", False, "", "2026-08-08T00:00:00+00:00"]))
    frame, metrics = clean_comments([record])
    with TemporaryDirectory() as temp:
        raw_path = export_raw_records([record], Path(temp) / "raw.jsonl")
        csv_path, xlsx_path = export_results(frame, metrics, Path(temp) / "smoke")
        assert raw_path.exists() and csv_path.exists() and xlsx_path.exists()
        assert len(pd.read_csv(csv_path)) == 1
    print("Smoke test passed: URL, raw snapshot, cleaning, CSV, and Excel pipeline are ready.")


if __name__ == "__main__":
    main()
