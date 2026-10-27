"""Fetch recent draws before exporting the static PWA data."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from src.crawler import Daily539Crawler  # noqa: E402


def main() -> None:
    crawler = Daily539Crawler(ROOT / "data" / "daily539_cache.json")
    before = crawler.load_cache()
    updated = crawler.refresh_to_latest()
    if not updated:
        raise RuntimeError("No historical draw data available")
    latest_date = max(draw.date for draw in updated)
    print(f"Latest draw: {latest_date} ({len(updated)} draws)")
    if before and latest_date == max(draw.date for draw in before):
        print("No new draws were found")
    if (date.today() - date.fromisoformat(latest_date)).days > 14:
        raise RuntimeError("Published draw data is more than 14 days old; check the data source")


if __name__ == "__main__":
    main()
