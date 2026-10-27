#!/usr/bin/env python3
"""診斷備援資料來源：把回傳內容存下來並嘗試解析。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.crawler import (  # noqa: E402
    GOV_D423F_URL,
    RESULT_DOWNLOAD_URL,
    Daily539Crawler,
)

OUT = ROOT / "data" / "debug"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    crawler = Daily539Crawler(ROOT / "data" / "daily539_cache.json")

    # 1) ResultDownload metadata for a recent year
    for year in (2024, 2023, 2014):
        print(f"\n=== ResultDownload year={year} ===")
        resp = crawler.session.get(RESULT_DOWNLOAD_URL, params={"year": year}, timeout=30)
        print("status", resp.status_code, "ctype", resp.headers.get("content-type"))
        meta_path = OUT / f"result_download_{year}.json"
        meta_path.write_bytes(resp.content)
        print("saved", meta_path)
        try:
            payload = resp.json()
            print("json keys", list(payload.keys())[:10])
            print("snippet", json.dumps(payload, ensure_ascii=False)[:500])
            content = payload.get("content")
            if isinstance(content, dict):
                print("content keys", content.keys())
                print("path", content.get("path"))
                print("fileName", content.get("fileName"))
                path = (content.get("path") or "").strip()
                if path:
                    file_resp = crawler.session.get(path, timeout=60)
                    print("file status", file_resp.status_code, "len", len(file_resp.content))
                    fname = content.get("fileName") or f"{year}.bin"
                    fpath = OUT / fname
                    fpath.write_bytes(file_resp.content)
                    print("saved file", fpath)
                    draws = list(crawler._parse_bytes_as_draws(file_resp.content, fname))
                    print("parsed draws", len(draws))
                    if draws:
                        print("sample", draws[0], draws[-1])
        except Exception as exc:
            print("parse meta failed", exc)
            print("body head", resp.text[:400])

    # 2) D423F index
    print("\n=== D423F index ===")
    idx = crawler.session.get(GOV_D423F_URL, timeout=60)
    print("status", idx.status_code, "len", len(idx.content))
    (OUT / "d423f_index.csv").write_bytes(idx.content)
    text = crawler._decode_text(idx.content)
    print("index head:\n", text[:800])
    links = crawler._extract_http_links(idx.content)
    print("links", len(links))
    for i, link in enumerate(links[:3], 1):
        print(f"\n--- link {i}: {link}")
        r = crawler.session.get(link, timeout=60)
        print("status", r.status_code, "ctype", r.headers.get("content-type"), "len", len(r.content))
        name = f"d423f_file_{i}.bin"
        (OUT / name).write_bytes(r.content)
        # peek
        head = r.content[:200]
        print("magic/head", head[:80])
        draws = list(crawler._parse_bytes_as_draws(r.content, name))
        print("parsed draws", len(draws))
        if draws[:1]:
            print("sample", draws[0])
        else:
            # if looks like text/csv show header
            try:
                print("text head:\n", crawler._decode_text(r.content)[:500])
            except Exception:
                pass

    print("\nDone. Inspect files under", OUT)


if __name__ == "__main__":
    main()
