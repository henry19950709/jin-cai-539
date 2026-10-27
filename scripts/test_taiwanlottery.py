#!/usr/bin/env python3
"""單測 taiwanlottery 套件能否抓到今彩539。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    try:
        from TaiwanLottery import TaiwanLotteryCrawler
    except ImportError:
        print("尚未安裝 taiwanlottery，請先執行：")
        print("  python3 -m pip install --user taiwanlottery")
        raise SystemExit(1)

    lottery = TaiwanLotteryCrawler()
    # 先測最近一個月，確認是否也被 WAF 擋
    for year, month in (("2024", "06"), ("2026", "07"), ("2023", "01")):
        print(f"\n=== daily_cash([{year!r}, {month!r}]) ===")
        try:
            rows = lottery.daily_cash([year, month])
            print("count", len(rows) if rows else 0)
            if rows:
                print("sample", rows[0])
                break
        except Exception as exc:
            print("FAILED:", type(exc).__name__, exc)


if __name__ == "__main__":
    main()
