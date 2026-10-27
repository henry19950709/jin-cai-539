from __future__ import annotations

import csv
import io
import json
import re
import time
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from .error_log import log_error
from .http_client import HttpClient
from .models import Draw

API_BASE = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery"
DAILY539_URL = f"{API_BASE}/Daily539Result"
RESULT_DOWNLOAD_URL = f"{API_BASE}/ResultDownload"
GOV_D423F_URL = "https://gaze.nta.gov.tw/dntmb/OpenData/csvDw?ntaCode=D423F"

# 今彩539 約自 2007 年起開獎
START_YEAR = 2007
START_MONTH = 1

ProgressCallback = Callable[[str, int, int], None]


class Daily539Crawler:
    """用模擬瀏覽器的 HTTP 客戶端爬官方今彩539資料。"""

    def __init__(self, cache_path: Path, timeout: float = 30.0):
        self.cache_path = Path(cache_path)
        self.timeout = timeout
        self.http = HttpClient(timeout=timeout)

    def fetch_month(self, year: int, month: int) -> List[Draw]:
        params = {
            "period": "",
            "month": f"{year}-{month:02d}",
            "endMonth": f"{year}-{month:02d}",
            "pageNum": 1,
            "pageSize": 100,
        }
        resp = self.http.get(
            DAILY539_URL,
            params=params,
            headers={
                "Referer": "https://www.taiwanlottery.com/lotto/result/daily_cash/",
            },
        )
        if resp.status_code == 403:
            raise RuntimeError(
                f"403 Forbidden for {getattr(resp, 'url', DAILY539_URL)}; "
                f"body={resp.text[:200]!r}"
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code} for Daily539Result")
        # 若仍拿到 HTML，不是 JSON
        text = resp.text.lstrip()
        if text.startswith("<") or text.startswith("<!"):
            raise RuntimeError(f"non-JSON response (likely WAF): {text[:200]!r}")
        payload = resp.json()
        content = payload.get("content") or {}
        rows = content.get("daily539Res") or []
        return [self._row_to_draw(row) for row in rows if row]

    @staticmethod
    def _row_to_draw(row: dict) -> Draw:
        numbers = [int(n) for n in (row.get("drawNumberSize") or [])]
        if len(numbers) > 5:
            numbers = numbers[:5]
        date_raw = str(row.get("lotteryDate") or "")
        return Draw(
            period=int(row["period"]),
            date=date_raw[:10],
            numbers=sorted(numbers),
        )

    def crawl_all(
        self,
        progress: Optional[ProgressCallback] = None,
        sleep_sec: float = 0.08,
    ) -> List[Draw]:
        """線上爬蟲：優先用本機快取，沒有再抓官方資料。"""
        cached = self.load_cache()
        if cached:
            if progress:
                progress("發現本機快取，直接載入已爬資料…", 0, 1)
            log_error(f"using cached draws from {self.cache_path}", context="crawl_all")
            return cached

        if progress:
            progress(f"HTTP backend={self.http.backend}，開始爬官方資料…", 0, 1)

        api_draws = self._crawl_via_monthly_api(progress=progress, sleep_sec=sleep_sec)
        if api_draws:
            self.save_cache(api_draws)
            return api_draws

        if progress:
            progress("月 API 失敗，改抓官方年檔 / 開放資料…", 0, 1)
        log_error(
            "monthly crawl produced 0 draws; switching to yearly/open-data fallback",
            context="crawl_all",
        )

        fallback_draws = self._crawl_via_fallback(progress=progress)
        if fallback_draws:
            self.save_cache(fallback_draws)
            return fallback_draws

        manual_dir = self.cache_path.parent / "manual"
        manual_draws = self.load_from_local_dir(manual_dir, progress=progress)
        if manual_draws:
            self.save_cache(manual_draws)
            return manual_draws

        cached = self.load_cache()
        if cached:
            log_error("online sources empty; using existing local cache", context="crawl_all")
            return cached
        return []

    def load_from_local_dir(
        self,
        directory: Path,
        progress: Optional[ProgressCallback] = None,
    ) -> List[Draw]:
        """從本機目錄讀取手動下載的 zip/csv（瀏覽器下載後放到 data/manual）。"""
        directory = Path(directory)
        if not directory.exists():
            return []

        files = sorted(
            [
                p
                for p in directory.iterdir()
                if p.is_file() and p.suffix.lower() in {".zip", ".csv", ".txt"}
            ]
        )
        if not files:
            return []

        all_draws: List[Draw] = []
        total = len(files)
        for idx, path in enumerate(files, start=1):
            if progress:
                progress(f"讀取本機檔 {path.name}", idx, total)
            try:
                data = path.read_bytes()
                parsed = list(self._parse_bytes_as_draws(data, path.name))
                all_draws.extend(parsed)
            except Exception as exc:  # noqa: BLE001
                log_error(f"failed parsing local file: {path}", exc)

        by_period = {d.period: d for d in all_draws}
        draws = sorted(by_period.values(), key=lambda d: d.period)
        if draws:
            log_error(
                f"loaded {len(draws)} draws from local dir {directory}",
                context="load_from_local_dir",
            )
        return draws

    def _crawl_via_monthly_api(
        self,
        progress: Optional[ProgressCallback],
        sleep_sec: float,
    ) -> List[Draw]:
        now = datetime.now()
        months: List[tuple] = []
        y, m = START_YEAR, START_MONTH
        while (y < now.year) or (y == now.year and m <= now.month):
            months.append((y, m))
            m += 1
            if m > 12:
                m = 1
                y += 1

        all_draws: List[Draw] = []
        total = len(months)
        consecutive_fail = 0
        logged_failures = 0

        for idx, (year, month) in enumerate(months, start=1):
            label = f"爬取 {year}-{month:02d}"
            if progress:
                progress(label, idx, total)
            try:
                month_draws = self.fetch_month(year, month)
                all_draws.extend(month_draws)
                consecutive_fail = 0
            except Exception as exc:  # noqa: BLE001
                consecutive_fail += 1
                if logged_failures < 3:
                    log_error(
                        f"crawl month failed: {year}-{month:02d}",
                        exc,
                        context=f"{label} ({idx}/{total})",
                    )
                    logged_failures += 1
                if progress:
                    progress(f"{label} 失敗: {exc}", idx, total)
                # 連續失敗太多次，多半是 API 全面擋，改走 fallback
                if consecutive_fail >= 3 and not all_draws:
                    log_error(
                        f"abort monthly API after {consecutive_fail} consecutive failures",
                        context="crawl_all",
                    )
                    return []
            if sleep_sec:
                time.sleep(sleep_sec)

        by_period = {d.period: d for d in all_draws}
        return sorted(by_period.values(), key=lambda d: d.period)

    def _crawl_via_fallback(self, progress: Optional[ProgressCallback]) -> List[Draw]:
        draws: List[Draw] = []
        try:
            draws = self._crawl_via_result_download(progress=progress)
        except Exception as exc:  # noqa: BLE001
            log_error("ResultDownload fallback failed", exc, context="fallback")

        if draws:
            return draws

        try:
            draws = self._crawl_via_gov_d423f(progress=progress)
        except Exception as exc:  # noqa: BLE001
            log_error("D423F open-data fallback failed", exc, context="fallback")
        return draws

    def _crawl_via_result_download(
        self,
        progress: Optional[ProgressCallback],
    ) -> List[Draw]:
        """台灣彩券 ResultDownload：逐年抓 ZIP/CSV。"""
        now_year = datetime.now().year
        all_draws: List[Draw] = []
        years = list(range(START_YEAR, now_year + 1))
        total = len(years)

        for idx, year in enumerate(years, start=1):
            if progress:
                progress(f"嘗試年檔 {year}…", idx, total)
            meta = self._resolve_result_download(year)
            if not meta:
                if progress:
                    progress(f"年檔 {year} 無可用下載（或被擋）", idx, total)
                # 之後年份可能尚未上架，提早結束
                if year > START_YEAR + 1 and not all_draws:
                    continue
                if year > now_year - 1:
                    break
                continue

            path = (meta.get("path") or "").strip()
            if not path:
                continue
            try:
                resp = self.http.get(path)
                if not resp.ok:
                    if progress:
                        progress(f"年檔 {year} 下載失敗 HTTP {resp.status_code}", idx, total)
                    continue
                file_bytes = resp.content
            except Exception as exc:  # noqa: BLE001
                if progress:
                    progress(f"年檔 {year} 下載失敗: {exc}", idx, total)
                continue
            file_name = meta.get("fileName") or f"{year}.zip"
            parsed = list(self._parse_bytes_as_draws(file_bytes, file_name))
            if progress:
                progress(f"年檔 {year} 解析到 {len(parsed)} 期", idx, total)
            all_draws.extend(parsed)

        by_period = {d.period: d for d in all_draws}
        return sorted(by_period.values(), key=lambda d: d.period)

    def _resolve_result_download(self, year: int) -> Optional[dict]:
        resp = self.http.get(
            RESULT_DOWNLOAD_URL,
            params={"year": year},
        )
        if not resp.ok:
            return None
        try:
            payload = resp.json()
        except Exception:  # noqa: BLE001
            return None
        content = payload.get("content")
        if isinstance(content, dict) and (content.get("path") or "").strip():
            return content
        return None

    def _crawl_via_gov_d423f(
        self,
        progress: Optional[ProgressCallback],
    ) -> List[Draw]:
        """政府開放資料 D423F：先抓索引 CSV，再下載裡面的連結。"""
        if progress:
            progress("下載政府開放資料索引 D423F…", 0, 1)
        index_bytes = self.http.get(GOV_D423F_URL).content
        links = self._extract_http_links(index_bytes)
        if not links:
            raise RuntimeError("D423F index has no download links")

        all_draws: List[Draw] = []
        total = len(links)
        for idx, link in enumerate(links, start=1):
            if progress:
                progress(f"嘗試開放資料 {idx}/{total}", idx, total)
            try:
                resp = self.http.get(link)
                if resp.status_code >= 400:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                name = link.rsplit("/", 1)[-1] or f"file_{idx}"
                parsed = list(self._parse_bytes_as_draws(resp.content, name))
                if progress:
                    progress(f"開放資料 {idx}/{total} 解析到 {len(parsed)} 期", idx, total)
                all_draws.extend(parsed)
            except Exception as exc:  # noqa: BLE001
                if progress:
                    progress(f"開放資料 {idx}/{total} 失敗: {exc}", idx, total)
                log_error(f"failed downloading open-data link: {link}", exc)

        by_period = {d.period: d for d in all_draws}
        return sorted(by_period.values(), key=lambda d: d.period)

    @staticmethod
    def _extract_http_links(csv_bytes: bytes) -> List[str]:
        text = Daily539Crawler._decode_text(csv_bytes)
        links: List[str] = []
        seen = set()
        for match in re.findall(r"https?://[^\s,\"']+", text):
            url = match.rstrip(").,;")
            if url not in seen:
                seen.add(url)
                links.append(url)
        return links

    def _parse_bytes_as_draws(self, data: bytes, file_name: str) -> Iterable[Draw]:
        lower = file_name.lower()
        if lower.endswith(".zip") or data[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    if not info.filename.lower().endswith((".csv", ".txt")):
                        continue
                    with zf.open(info) as fh:
                        yield from self._parse_csv_draws(fh.read())
            return
        yield from self._parse_csv_draws(data)

    def _parse_csv_draws(self, raw: bytes) -> Iterable[Draw]:
        text = self._decode_text(raw)
        # 去掉 UTF-8 BOM
        if text.startswith("\ufeff"):
            text = text[1:]
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return

        header = [h.strip() for h in rows[0]]
        # 官方年檔通常第一列是欄位名
        start_idx = 1
        colmap = {name: i for i, name in enumerate(header)}

        def find_col(*names: str) -> Optional[int]:
            for name in names:
                if name in colmap:
                    return colmap[name]
            # 模糊比對
            for key, idx in colmap.items():
                for name in names:
                    if name in key:
                        return idx
            return None

        game_i = find_col("遊戲名稱", "遊戲")
        period_i = find_col("期別")
        date_i = find_col("開獎日期")
        num_cols = [
            find_col(f"獎號{i}", f"號碼{i}") for i in range(1, 7)
        ]
        # 若第一列不像 header，當作資料列
        if period_i is None or date_i is None:
            start_idx = 0
            game_i, period_i, date_i = 0, 1, 2
            num_cols = [6, 7, 8, 9, 10]

        for row in rows[start_idx:]:
            if not row or len(row) <= max(x for x in [period_i, date_i] if x is not None):
                continue
            game = row[game_i].strip() if game_i is not None and game_i < len(row) else ""
            if game and ("今彩539" not in game) and ("539" not in game):
                # 年檔常含多種遊戲，只留 539
                continue
            try:
                period = int(str(row[period_i]).strip())
            except (TypeError, ValueError, IndexError):
                continue
            date_raw = str(row[date_i]).strip().replace("/", "-")
            date = self._normalize_date(date_raw)
            numbers: List[int] = []
            for ci in num_cols:
                if ci is None or ci >= len(row):
                    continue
                cell = str(row[ci]).strip()
                if not cell:
                    continue
                try:
                    numbers.append(int(float(cell)))
                except ValueError:
                    continue
            numbers = sorted(n for n in numbers if 1 <= n <= 39)[:5]
            if len(numbers) < 5:
                continue
            yield Draw(period=period, date=date, numbers=numbers)

    @staticmethod
    def _normalize_date(raw: str) -> str:
        raw = raw.strip()
        # 已是西元
        m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", raw)
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        # 民國 yyy/mm/dd
        m = re.match(r"^(\d{2,3})[-/](\d{1,2})[-/](\d{1,2})", raw)
        if m:
            year = int(m.group(1)) + 1911
            return f"{year:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return raw[:10]

    @staticmethod
    def _decode_text(raw: bytes) -> str:
        for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _add_months(source: date, month_offset: int) -> date:
        year = source.year + (source.month - 1 + month_offset) // 12
        month = (source.month - 1 + month_offset) % 12 + 1
        day = min(source.day, 28)
        return date(year, month, day)

    @staticmethod
    def _months_between(start: date, end: date) -> List[date]:
        months: List[date] = []
        current = date(start.year, start.month, 1)
        final = date(end.year, end.month, 1)
        while current <= final:
            months.append(current)
            current = Daily539Crawler._add_months(current, 1)
        return months

    def _cache_has_month_coverage(self, draws: List[Draw], start: date, end: date) -> bool:
        if not draws:
            return False
        dates = {draw.date for draw in draws}
        months = {d.strftime("%Y-%m") for d in self._months_between(start, end)}
        present_months = {d[:7] for d in dates}
        if start.isoformat() not in dates and min(dates) > start.isoformat():
            return False
        if end.isoformat() not in dates and max(dates) < end.isoformat():
            return False
        return months.issubset(present_months)

    def refresh_to_latest(self) -> List[Draw]:
        """總是同步到最新月份，並將最新 cache 與 memory 更新到 disk。"""
        cached = self.load_cache()
        latest_date = max((draw.date for draw in cached), default=None)
        if latest_date:
            latest_year, latest_month = map(int, latest_date[:7].split('-'))
        else:
            latest_year, latest_month = START_YEAR, START_MONTH

        today = datetime.now().date()
        current_year, current_month = today.year, today.month
        merged = {draw.period: draw for draw in cached}

        for year in range(latest_year, current_year + 1):
            start_month = 1 if year > latest_year else latest_month
            end_month = current_month if year == current_year else 12
            for month in range(start_month, end_month + 1):
                try:
                    month_draws = self.fetch_month(year, month)
                except Exception as exc:  # noqa: BLE001
                    log_error(f"refresh_to_latest fetch_month failed: {year}-{month:02d}", exc)
                    continue
                for draw in month_draws:
                    merged[draw.period] = draw

        final = sorted(merged.values(), key=lambda d: d.period)
        if final != cached:
            self.save_cache(final)
        return final

    def ensure_cache_complete(self) -> List[Draw]:
        """確保 cache 至少涵蓋 2007-01-01 到今天的每個月份。"""
        return self.refresh_to_latest()

    def save_cache(self, draws: List[Draw]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "count": len(draws),
            "draws": [d.to_dict() for d in draws],
        }
        self.cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_cache(self) -> List[Draw]:
        if not self.cache_path.exists():
            return []
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return []
        draws = payload.get("draws", [])
        if not draws:
            return []
        return [Draw.from_dict(row) for row in draws]
