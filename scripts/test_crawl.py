#!/usr/bin/env python3
"""手動測試爬蟲（在一般終端機執行）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.crawler import Daily539Crawler  # noqa: E402


def main() -> None:
    cache = ROOT / "data" / "daily539_cache.json"
    crawler = Daily539Crawler(cache)

    def progress(msg: str, cur: int, total: int) -> None:
        print(f"[{cur}/{total}] {msg}")

    draws = crawler.crawl_all(progress=progress)
    print(f"got {len(draws)} draws")
    if draws:
        print("first", draws[0])
        print("last", draws[-1])
    else:
        print("no draws; check error.log")


if __name__ == "__main__":
    main()
