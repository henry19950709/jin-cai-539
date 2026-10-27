#!/usr/bin/env python3
"""只測本機 data/manual 年檔能否解析。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.crawler import Daily539Crawler  # noqa: E402


def main() -> None:
    manual = ROOT / "data" / "manual"
    files = [
        p
        for p in manual.iterdir()
        if p.is_file() and p.suffix.lower() in {".zip", ".csv", ".txt"}
    ] if manual.exists() else []

    if not files:
        print("data/manual/ 目前沒有 zip/csv。")
        print("請先用瀏覽器下載官網年檔放到：", manual)
        print("下載頁：https://www.taiwanlottery.com/lotto/history/result_download/")
        raise SystemExit(1)

    crawler = Daily539Crawler(ROOT / "data" / "daily539_cache.json")

    def progress(msg: str, cur: int, total: int) -> None:
        print(f"[{cur}/{total}] {msg}")

    draws = crawler.load_from_local_dir(manual, progress=progress)
    print(f"got {len(draws)} draws")
    if draws:
        print("first", draws[0])
        print("last", draws[-1])
        crawler.save_cache(draws)
        print("cache saved:", crawler.cache_path)
    else:
        print("解析結果為 0，請確認 zip 內是否含今彩539 CSV")


if __name__ == "__main__":
    main()
