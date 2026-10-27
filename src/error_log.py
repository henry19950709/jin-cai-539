from __future__ import annotations

import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

# 專案根目錄下的錯誤日誌檔
LOG_PATH = Path(__file__).resolve().parent.parent / "error.log"


def _proxy_env_snapshot() -> str:
    keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "NO_PROXY",
        "no_proxy",
        "SOCKS_PROXY",
        "SOCKS5_PROXY",
    ]
    lines = []
    for key in keys:
        val = os.environ.get(key)
        if val:
            lines.append(f"  {key}={val}")
    return "\n".join(lines) if lines else "  (none)"


def log_error(
    message: str,
    exc: Optional[BaseException] = None,
    *,
    context: str = "",
) -> Path:
    """把錯誤 append 到 error.log，回傳日誌路徑。"""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    parts = [
        "=" * 72,
        f"[{stamp}] {message}",
    ]
    if context:
        parts.append(f"context: {context}")
    parts.append("proxy env:")
    parts.append(_proxy_env_snapshot())
    if exc is not None:
        parts.append(f"exception: {type(exc).__name__}: {exc}")
        parts.append("traceback:")
        parts.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    parts.append("")
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return LOG_PATH
