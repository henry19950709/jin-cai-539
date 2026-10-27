#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""今彩539 合數 / 尾數分析工具入口。"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from src.error_log import log_error
from src.gui.main_window import MainWindow


def _install_excepthook() -> None:
    def _hook(exc_type, exc, tb):
        try:
            log_error("uncaught exception", exc, context="sys.excepthook")
        except Exception:  # noqa: BLE001
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook


def main() -> int:
    _install_excepthook()
    base_dir = Path(__file__).resolve().parent
    cache_path = base_dir / "data" / "daily539_cache.json"

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("今彩539 Analyzer")
        window = MainWindow(cache_path=cache_path)
        # 啟動時先確保 disk cache 覆蓋 2007-01-01 到今日的完整歷史
        window.crawler.ensure_cache_complete()
        window.show()
        window.start_crawl()
        return app.exec_()
    except Exception as exc:  # noqa: BLE001
        log_path = log_error("main() crashed", exc, context="main")
        print(f"Fatal error. Details written to: {log_path}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
