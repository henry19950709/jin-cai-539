#!/usr/bin/env python3
"""測試 curl_cffi 是否能打通官方 API / CDN。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.http_client import HttpClient  # noqa: E402


def main() -> None:
    client = HttpClient()
    print("backend:", client.backend)
    print("verify:", client.verify)
    if client.backend != "curl_cffi":
        print("請先安裝： python3 -m pip install --user curl_cffi")
        raise SystemExit(1)

    tests = [
        (
            "月 API",
            "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result",
            {
                "period": "",
                "month": "2024-06",
                "endMonth": "2024-06",
                "pageNum": 1,
                "pageSize": 20,
            },
        ),
        (
            "ResultDownload",
            "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/ResultDownload",
            {"year": 2024},
        ),
        (
            "CDN zip",
            "https://cdn.taiwanlottery.com.tw/app/FilesForDownload/Download/LottoResult/2024.zip",
            None,
        ),
    ]

    for name, url, params in tests:
        print(f"\n=== {name} ===")
        try:
            r = client.get(url, params=params)
            print("status", r.status_code, "len", len(r.content))
            ctype = r.headers.get("content-type", "")
            print("content-type", ctype)
            head = r.text[:180].replace("\n", " ")
            print("head", head)
        except Exception as exc:
            print("FAILED", type(exc).__name__, exc)


if __name__ == "__main__":
    main()
