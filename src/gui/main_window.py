from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..analyzer import Analyzer
from ..crawler import Daily539Crawler
from ..error_log import LOG_PATH, log_error
from ..models import Draw, SearchFilter
from .charts import DistChart


class CrawlWorker(QThread):
    progress = pyqtSignal(str, int, int)
    finished_ok = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, crawler: Daily539Crawler):
        super().__init__()
        self.crawler = crawler

    def run(self) -> None:
        try:
            draws = self.crawler.crawl_all(progress=self._on_progress)
            self.finished_ok.emit(draws)
        except Exception as exc:  # noqa: BLE001
            log_error("crawl_all crashed", exc, context="CrawlWorker.run")
            self.failed.emit(str(exc))

    def _on_progress(self, message: str, current: int, total: int) -> None:
        self.progress.emit(message, current, total)


SEARCH_MODES = [
    "全部歷史",
    "依年份",
    "依年月",
    "依期數區間",
    "依合數篩選期別",
    "依尾數篩選期別",
    "綜合條件",
    "只統計符合合數/尾數的號碼",
]


class MainWindow(QMainWindow):
    def __init__(self, cache_path: Path):
        super().__init__()
        self.setWindowTitle("今彩539 合數 / 尾數分析")
        self.resize(1280, 820)

        self.cache_path = Path(cache_path)
        self.crawler = Daily539Crawler(self.cache_path)
        self.analyzer = Analyzer()
        self.worker: Optional[CrawlWorker] = None

        self._build_ui()
        self._apply_mode("全部歷史")
        self.statusBar().showMessage("準備載入歷史資料…")

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)

        # --- top: crawl status ---
        top = QHBoxLayout()
        self.status_label = QLabel("尚未載入資料")
        self.status_label.setFont(QFont("", 11, QFont.Bold))
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.reload_btn = QPushButton("重新爬取")
        self.reload_btn.clicked.connect(self.start_crawl)
        self.manual_btn = QPushButton("載入本機年檔")
        self.manual_btn.clicked.connect(self.load_manual)
        top.addWidget(self.status_label, stretch=2)
        top.addWidget(self.progress_bar, stretch=3)
        top.addWidget(self.manual_btn)
        top.addWidget(self.reload_btn)
        root_layout.addLayout(top)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)

        self.main_tab = QWidget()
        self.search_tab = QWidget()
        self.tabs.addTab(self.main_tab, "主要")
        self.tabs.addTab(self.search_tab, "搜尋")

        self._build_main_tab(self.main_tab)
        self._build_search_tab(self.search_tab)

    def _build_search_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # --- left: filters ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        filter_box = QGroupBox("搜尋條件")
        form = QFormLayout(filter_box)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(SEARCH_MODES)
        self.mode_combo.currentTextChanged.connect(self._apply_mode)
        form.addRow("搜尋方式", self.mode_combo)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2007, 2100)
        self.year_spin.setValue(2024)
        self.year_spin.setSpecialValueText("不限")
        self.year_enable = QCheckBox("啟用")
        self.year_row = QWidget()
        year_layout = QHBoxLayout(self.year_row)
        year_layout.setContentsMargins(0, 0, 0, 0)
        year_layout.addWidget(self.year_spin)
        year_layout.addWidget(self.year_enable)
        form.addRow("年", self.year_row)

        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(1)
        self.month_enable = QCheckBox("啟用")
        self.month_row = QWidget()
        month_layout = QHBoxLayout(self.month_row)
        month_layout.setContentsMargins(0, 0, 0, 0)
        month_layout.addWidget(self.month_spin)
        month_layout.addWidget(self.month_enable)
        form.addRow("月份", self.month_row)

        self.period_from = QSpinBox()
        self.period_from.setRange(0, 999999999)
        self.period_from.setValue(0)
        self.period_to = QSpinBox()
        self.period_to.setRange(0, 999999999)
        self.period_to.setValue(0)
        self.period_enable = QCheckBox("啟用")
        period_wrap = QWidget()
        period_layout = QHBoxLayout(period_wrap)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.addWidget(QLabel("起"))
        period_layout.addWidget(self.period_from)
        period_layout.addWidget(QLabel("迄"))
        period_layout.addWidget(self.period_to)
        period_layout.addWidget(self.period_enable)
        form.addRow("期數", period_wrap)

        self.he_table = self._make_multi_table(list(range(1, 13)), "合數")
        form.addRow("合數 (1~12)", self.he_table)

        self.wei_table = self._make_multi_table(list(range(0, 10)), "尾數")
        form.addRow("尾數 (0~9)", self.wei_table)

        self.match_numbers_only = QCheckBox("只統計勾選合數/尾數對應的號碼")
        form.addRow(self.match_numbers_only)

        left_layout.addWidget(filter_box)

        btn_row = QHBoxLayout()
        self.search_btn = QPushButton("搜尋 / 統計")
        self.search_btn.setEnabled(False)
        self.search_btn.clicked.connect(self.run_search)
        self.clear_btn = QPushButton("清除條件")
        self.clear_btn.clicked.connect(self.clear_filters)
        btn_row.addWidget(self.search_btn)
        btn_row.addWidget(self.clear_btn)
        left_layout.addLayout(btn_row)

        tip = QLabel(
            "合數：各位數字相加（19→10、28→10）。\n"
            "預設用合數/尾數篩「期別」；勾選下方選項則只統計符合的號碼。"
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #555;")
        left_layout.addWidget(tip)
        left_layout.addStretch(1)
        splitter.addWidget(left)

        # --- right: results ---
        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.summary_label = QLabel("結果摘要：—")
        right_layout.addWidget(self.summary_label)

        charts_row = QHBoxLayout()
        self.he_chart = DistChart("合數分布（次數 / 百分比）")
        self.wei_chart = DistChart("尾數分布（次數 / 百分比）")
        charts_row.addWidget(self.he_chart)
        charts_row.addWidget(self.wei_chart)
        right_layout.addLayout(charts_row, stretch=3)

        tables_row = QHBoxLayout()
        self.he_stat_table = self._make_stat_table(["合數", "次數", "百分比"])
        self.wei_stat_table = self._make_stat_table(["尾數", "次數", "百分比"])
        tables_row.addWidget(self.he_stat_table)
        tables_row.addWidget(self.wei_stat_table)
        right_layout.addLayout(tables_row, stretch=2)

        self.draw_table = QTableWidget(0, 4)
        self.draw_table.setHorizontalHeaderLabels(["期別", "開獎日期", "獎號", "合數 / 尾數"])
        self.draw_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.draw_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.draw_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        right_layout.addWidget(self.draw_table, stretch=3)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

    def _build_main_tab(self, parent: QWidget) -> None:
        container = QVBoxLayout(parent)
        form_box = QGroupBox("基準期輸入")
        form = QFormLayout(form_box)

        self.main_year_spin = QSpinBox()
        self.main_year_spin.setRange(2007, 2100)
        self.main_year_spin.setValue(2024)
        form.addRow("年", self.main_year_spin)

        self.main_month_spin = QSpinBox()
        self.main_month_spin.setRange(1, 12)
        self.main_month_spin.setValue(1)
        form.addRow("月", self.main_month_spin)

        self.main_day_spin = QSpinBox()
        self.main_day_spin.setRange(1, 31)
        self.main_day_spin.setValue(1)
        form.addRow("日", self.main_day_spin)

        self.main_period_edit = QLineEdit()
        self.main_period_edit.setPlaceholderText("可填期數，例：1234")
        self.main_period_edit.returnPressed.connect(self.run_main_analysis)
        form.addRow("期數（可選）", self.main_period_edit)

        self.main_analyze_btn = QPushButton("分析")
        self.main_analyze_btn.clicked.connect(self.run_main_analysis)
        self.main_year_spin.editingFinished.connect(self.run_main_analysis)
        self.main_month_spin.editingFinished.connect(self.run_main_analysis)
        self.main_day_spin.editingFinished.connect(self.run_main_analysis)
        form.addRow("", self.main_analyze_btn)

        container.addWidget(form_box)

        self.main_info_label = QLabel("請先選擇基準期。")
        self.main_info_label.setWordWrap(True)
        self.main_info_label.setStyleSheet("color: #2563EB;")
        container.addWidget(self.main_info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        output_widget = QWidget()
        self.main_output_layout = QVBoxLayout(output_widget)
        scroll.setWidget(output_widget)
        container.addWidget(scroll, stretch=1)

        self.main_output_layout.addWidget(QLabel("尚未分析"))

    def _make_multi_table(self, values: List[int], _name: str) -> QTableWidget:
        table = QTableWidget(1, len(values))
        table.setHorizontalHeaderLabels([str(v) for v in values])
        table.setVerticalHeaderLabels(["選"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(True)
        table.setFixedHeight(70)
        for col, _v in enumerate(values):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            table.setItem(0, col, item)
        return table

    def _make_stat_table(self, headers: List[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return table

    def _selected_values(self, table: QTableWidget) -> List[int]:
        values: List[int] = []
        for col in range(table.columnCount()):
            item = table.item(0, col)
            if item and item.checkState() == Qt.Checked:
                values.append(int(table.horizontalHeaderItem(col).text()))
        return values

    def _clear_multi(self, table: QTableWidget) -> None:
        for col in range(table.columnCount()):
            item = table.item(0, col)
            if item:
                item.setCheckState(Qt.Unchecked)

    def _apply_mode(self, mode: str) -> None:
        # reset enables according to preset
        self.year_enable.setChecked(False)
        self.month_enable.setChecked(False)
        self.period_enable.setChecked(False)
        self.match_numbers_only.setChecked(False)

        if mode == "全部歷史":
            pass
        elif mode == "依年份":
            self.year_enable.setChecked(True)
        elif mode == "依年月":
            self.year_enable.setChecked(True)
            self.month_enable.setChecked(True)
        elif mode == "依期數區間":
            self.period_enable.setChecked(True)
        elif mode == "依合數篩選期別":
            pass
        elif mode == "依尾數篩選期別":
            pass
        elif mode == "綜合條件":
            self.year_enable.setChecked(True)
        elif mode == "只統計符合合數/尾數的號碼":
            self.match_numbers_only.setChecked(True)

    def clear_filters(self) -> None:
        self.mode_combo.setCurrentText("全部歷史")
        self.year_enable.setChecked(False)
        self.month_enable.setChecked(False)
        self.period_enable.setChecked(False)
        self.period_from.setValue(0)
        self.period_to.setValue(0)
        self._clear_multi(self.he_table)
        self._clear_multi(self.wei_table)
        self.match_numbers_only.setChecked(False)

    def build_filter(self) -> SearchFilter:
        flt = SearchFilter()
        if self.year_enable.isChecked():
            flt.year = int(self.year_spin.value())
        if self.month_enable.isChecked():
            flt.month = int(self.month_spin.value())
        if self.period_enable.isChecked():
            p0 = int(self.period_from.value())
            p1 = int(self.period_to.value())
            if p0 > 0:
                flt.period_from = p0
            if p1 > 0:
                flt.period_to = p1
        flt.he_values = self._selected_values(self.he_table)
        flt.wei_values = self._selected_values(self.wei_table)
        flt.match_numbers_only = self.match_numbers_only.isChecked()
        return flt

    def start_crawl(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.search_btn.setEnabled(False)
        self.reload_btn.setEnabled(False)
        self.manual_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在載入歷史資料…")
        self.statusBar().showMessage("載入中，請稍候")

        self.worker = CrawlWorker(self.crawler)
        self.worker.progress.connect(self._on_crawl_progress)
        self.worker.finished_ok.connect(self._on_crawl_finished)
        self.worker.failed.connect(self._on_crawl_failed)
        self.worker.start()

    def load_manual(self) -> None:
        """只讀 data/manual 本機年檔，不打線上。"""
        manual_dir = self.cache_path.parent / "manual"
        self.status_label.setText("正在讀取本機年檔…")
        self.search_btn.setEnabled(False)
        self.reload_btn.setEnabled(False)
        self.manual_btn.setEnabled(False)
        try:
            draws = self.crawler.load_from_local_dir(manual_dir)
            if not draws:
                QMessageBox.information(
                    self,
                    "找不到本機年檔",
                    "請先用瀏覽器下載官方年檔 zip，放到：\n"
                    f"{manual_dir}\n\n"
                    "下載頁：\n"
                    "https://www.taiwanlottery.com/lotto/history/result_download/",
                )
                self.status_label.setText("本機年檔為空")
                return
            self.crawler.save_cache(draws)
            self._on_crawl_finished(draws)
        except Exception as exc:  # noqa: BLE001
            log_error("load_manual failed", exc)
            QMessageBox.critical(self, "讀取失敗", str(exc))
        finally:
            self.reload_btn.setEnabled(True)
            self.manual_btn.setEnabled(True)

    def _on_crawl_progress(self, message: str, current: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
        self.statusBar().showMessage(f"{message} ({current}/{total})")

    def _on_crawl_finished(self, draws: List[Draw]) -> None:
        self.analyzer.set_draws(draws)
        self.reload_btn.setEnabled(True)
        self.manual_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        if draws:
            self.status_label.setText(
                f"已載入 {len(draws)} 期（{draws[0].date} ~ {draws[-1].date}）"
            )
            self.statusBar().showMessage("歷史資料已載入記憶體，可開始搜尋")
            self._sync_year_range(draws)
            self.run_search()
        else:
            cached = self.crawler.load_cache()
            if cached:
                self.analyzer.set_draws(cached)
                self.status_label.setText(f"線上爬取為空，改用本地快取 {len(cached)} 期")
                self.search_btn.setEnabled(True)
                self._sync_year_range(cached)
                self.run_search()
            else:
                self.status_label.setText("沒有抓到資料（進度有跑≠成功）")
                QMessageBox.warning(
                    self,
                    "沒有抓到資料",
                    "進度條會跟著「嘗試次數」前進，但這次每次請求都被官方擋下"
                    "（常見是 WAF 回 403），所以最後 0 期。\n\n"
                    f"詳情請看：\n{LOG_PATH}",
                )

    def _on_crawl_failed(self, message: str) -> None:
        self.reload_btn.setEnabled(True)
        self.manual_btn.setEnabled(True)
        log_error("crawl finished with failure signal", context=message)
        cached = self.crawler.load_cache()
        if cached:
            self.analyzer.set_draws(cached)
            self.search_btn.setEnabled(True)
            self.status_label.setText(f"爬取失敗，已改用本地快取 {len(cached)} 期")
            self.statusBar().showMessage(f"爬取失敗：{message}")
            self._sync_year_range(cached)
            self.run_search()
            QMessageBox.warning(
                self,
                "爬取失敗",
                f"線上爬取失敗，已載入本地快取。\n\n錯誤：{message}\n\n詳情已寫入：{LOG_PATH}",
            )
        else:
            self.search_btn.setEnabled(False)
            self.status_label.setText("爬取失敗，且無本地快取")
            QMessageBox.critical(
                self,
                "爬取失敗",
                f"{message}\n\n詳情已寫入：{LOG_PATH}",
            )

    def _sync_year_range(self, draws: List[Draw]) -> None:
        years = [d.year for d in draws]
        if not years:
            return
        self.year_spin.setRange(min(years), max(years))
        self.year_spin.setValue(max(years))

    def _resolve_base_draw(self) -> Optional[Draw]:
        if not self.analyzer.draws:
            return None

        period_text = self.main_period_edit.text().strip()
        if period_text:
            try:
                period = int(period_text)
            except ValueError:
                QMessageBox.warning(self, "輸入錯誤", "期數請填入數字。")
                return None
            for draw in self.analyzer.draws:
                if draw.period == period:
                    return draw
            QMessageBox.warning(self, "找不到基準期", f"找不到期數 {period} 的資料。")
            return None

        year = int(self.main_year_spin.value())
        month = int(self.main_month_spin.value())
        day = int(self.main_day_spin.value())
        target = f"{year:04d}-{month:02d}-{day:02d}"

        exact = next((draw for draw in self.analyzer.draws if draw.date == target), None)
        if exact is not None:
            return exact

        # 若輸入的是未來日期或不存在的日期，則直接把它視為同月同日的前一年來分析。
        # 例如 2026/09/01 -> 2025/09/01；2026/08/14 -> 2025/08/14。
        previous_year = year - 1
        previous_target = f"{previous_year:04d}-{month:02d}-{day:02d}"
        previous_draw = next((draw for draw in self.analyzer.draws if draw.date == previous_target), None)
        if previous_draw is not None:
            return previous_draw

        # 若前一年同月同日也沒有資料，就退回到最近可用的歷史資料。
        valid_draws = sorted(
            [draw for draw in self.analyzer.draws if draw.date <= target],
            key=lambda d: d.period,
        )
        if not valid_draws:
            valid_draws = sorted(self.analyzer.draws, key=lambda d: d.period)
            if not valid_draws:
                QMessageBox.warning(self, "找不到基準期", f"找不到 {target} 的資料。")
                return None
            return valid_draws[-1]

        return valid_draws[-1]

    def _weekday_nth(self, year: int, month: int, day: int) -> int:
        target_day = datetime(year, month, day)
        count = 0
        current = datetime(year, month, 1)
        while current <= target_day:
            if current.weekday() == target_day.weekday():
                count += 1
            current += timedelta(days=1)
        return count

    def _weekday_label(self, draw: Draw) -> str:
        dt = datetime.strptime(draw.date, "%Y-%m-%d")
        nth = self._weekday_nth(dt.year, dt.month, dt.day)
        weekday_names = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        return f"第{nth}個{weekday_names[dt.weekday()]}"

    def _weekday_slot(self, draw: Draw) -> tuple[int, int]:
        dt = datetime.strptime(draw.date, "%Y-%m-%d")
        return dt.weekday(), self._weekday_nth(dt.year, dt.month, dt.day)

    def _issue_number(self, period: int) -> int:
        return int(period) % 1000

    def _matches_for_year(self, year: int, base_draw: Draw, mode: str) -> List[Draw]:
        matches: List[Draw] = []
        base_issue = self._issue_number(base_draw.period)
        for draw in self.analyzer.draws:
            if draw.year != year:
                continue
            if mode == "period":
                if self._issue_number(draw.period) == base_issue:
                    matches.append(draw)
            elif mode == "date":
                if draw.month == base_draw.month and draw.day == base_draw.day:
                    matches.append(draw)
            elif mode == "weekday":
                if draw.month == base_draw.month and self._weekday_slot(draw) == self._weekday_slot(base_draw):
                    matches.append(draw)
        return matches

    def _matches_for_month(self, year: int, month: int, base_draw: Draw, mode: str) -> List[Draw]:
        matches: List[Draw] = []
        for draw in self.analyzer.draws:
            if draw.year != year or draw.month != month:
                continue
            if mode == "date" and draw.day == base_draw.day:
                matches.append(draw)
            elif mode == "weekday" and self._weekday_slot(draw) == self._weekday_slot(base_draw):
                matches.append(draw)
        return matches

    def _collect_reference_matches(
        self,
        years: List[int],
        base_draw: Draw,
        mode: str,
        *,
        year_window: bool = True,
        max_rows: int = 5,
    ) -> List[tuple[str, List[Draw]]]:
        refs: List[tuple[str, List[Draw]]] = []
        for year in reversed(years):
            if year >= base_draw.year:
                continue
            matches = self._matches_for_year(year, base_draw, mode)
            if not matches:
                continue
            if year_window:
                refs.append((f"{year}年（{len(matches)}筆）", matches))
            else:
                refs.append((f"{year}年 {matches[0].date}（{self._weekday_label(matches[0])}）", matches[:1]))
            if len(refs) >= max_rows:
                break
        return refs

    def _shift_months(self, base_dt: datetime, offset: int) -> datetime:
        year = base_dt.year
        month = base_dt.month - offset
        while month <= 0:
            month += 12
            year -= 1
        return datetime(year, month, 1)

    def _sorted_distribution_items(self, dist_stat, keys: List[int]) -> List[tuple[int, int, float]]:
        items: List[tuple[int, int, float]] = []
        for key in keys:
            count = dist_stat.counts.get(key, 0)
            if count <= 0:
                continue
            items.append((key, count, dist_stat.percent(key)))
        items.sort(key=lambda x: (-x[1], -x[2], x[0]))
        return items

    def _distribution_summary(self, dist_stat, keys: List[int]) -> str:
        items = self._sorted_distribution_items(dist_stat, keys)
        if not items:
            return "無資料"
        best_count = items[0][1]
        winners = [str(key) for key, count, _ in items if count == best_count]
        winner_text = "、".join(winners)
        best_pct = items[0][2]
        return f"{winner_text}: {best_count}次 ({best_pct:.1f}%)"

    def _distribution_tooltip(self, dist_stat, keys: List[int]) -> str:
        items = self._sorted_distribution_items(dist_stat, keys)
        if not items:
            return "無資料"
        best_count = items[0][1]
        item_lines = []
        for key, count, pct in items:
            marker = "★" if count == best_count else ""
            item_lines.append(f"{marker}{key}: {count}次 ({pct:.1f}%)")
        return "\n".join(item_lines)

    def _distribution_cell(self, dist_stat, keys: List[int]) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        items = self._sorted_distribution_items(dist_stat, keys)
        if not items:
            label = QLabel("無資料")
            layout.addWidget(label)
            return widget

        best_count = items[0][1]
        winners = [str(key) for key, count, _ in items if count == best_count]
        winner_text = "、".join(winners)
        best_pct = items[0][2]
        summary = QLabel(f"{winner_text}: {best_count}次 ({best_pct:.1f}%)")
        summary.setStyleSheet(
            "font-weight: bold; color: #B45309; background: #FEF3C7; border-radius: 4px; padding: 2px 6px;"
        )
        summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(summary)

        info = QToolButton()
        info.setText("i")
        info.setToolTip(self._distribution_tooltip(dist_stat, keys))
        info.setFixedSize(22, 22)
        info.setStyleSheet(
            "QToolButton { border: 1px solid #94A3B8; border-radius: 11px; background: #E2E8F0; color: #0F172A; font-weight: bold; }"
        )
        layout.addWidget(info)
        return widget

    def _window_after(self, draw: Draw, window_size: int = 100) -> List[Draw]:
        idx = None
        for i, candidate in enumerate(self.analyzer.draws):
            if candidate.period == draw.period and candidate.date == draw.date:
                idx = i
                break
        if idx is None:
            return []
        return self.analyzer.draws[idx + 1 : idx + 1 + window_size]

    def _group_draws_by_date(self, draws: List[Draw]) -> List[tuple[str, List[Draw]]]:
        grouped: dict[str, List[Draw]] = {}
        for draw in draws:
            grouped.setdefault(draw.date, []).append(draw)
        return [(date, grouped[date]) for date in sorted(grouped.keys())]

    def _build_reference_group(
        self,
        title: str,
        refs: List[tuple[str, List[Draw]]],
        *,
        total_label: str = "合計",
    ) -> QWidget:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["項目", "合數分布", "尾數分布"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)

        all_draws = [draw for _, group_draws in refs for draw in group_draws]
        table.setRowCount(len(refs) + 1)

        def fill_row(row: int, label: str, draws: List[Draw]) -> None:
            he_stat = self.analyzer.he_distribution([n for draw in draws for n in draw.numbers])
            wei_stat = self.analyzer.wei_distribution([n for draw in draws for n in draw.numbers])

            table.setItem(row, 0, QTableWidgetItem(label))

            he_widget = self._distribution_cell(he_stat, Analyzer.HE_KEYS)
            he_container = QWidget()
            he_layout = QVBoxLayout(he_container)
            he_layout.setContentsMargins(0, 0, 0, 0)
            he_layout.addWidget(he_widget)
            table.setCellWidget(row, 1, he_container)

            wei_widget = self._distribution_cell(wei_stat, Analyzer.WEI_KEYS)
            wei_container = QWidget()
            wei_layout = QVBoxLayout(wei_container)
            wei_layout.setContentsMargins(0, 0, 0, 0)
            wei_layout.addWidget(wei_widget)
            table.setCellWidget(row, 2, wei_container)

        fill_row(0, f"{total_label}（{len(all_draws)}筆）", all_draws)
        for row, (label, draws) in enumerate(refs, start=1):
            fill_row(row, label, draws)

        layout.addWidget(table)
        return group

    def run_main_analysis(self) -> None:
        if not self.analyzer.draws:
            QMessageBox.information(self, "提示", "尚未載入資料")
            return

        base_draw = self._resolve_base_draw()
        if base_draw is None:
            return

        dt = datetime.strptime(base_draw.date, "%Y-%m-%d")
        self.main_info_label.setText(
            f"基準期：{base_draw.date}（{dt.year}年{dt.month}月{dt.day}日，{self._weekday_label(base_draw)}），期別 {base_draw.period}"
        )

        self._clear_main_output()

        target_years = list(range(base_draw.year - 5, base_draw.year))

        year_period_matches: List[Draw] = []
        for year in reversed(target_years):
            year_period_matches.extend(self._matches_for_year(year, base_draw, mode="period"))
        if not year_period_matches:
            self.main_output_layout.addWidget(QLabel("找不到可比對的前五年同期數資料。"))
        else:
            period_refs = self._group_draws_by_date(year_period_matches)
            self.main_output_layout.addWidget(
                self._build_reference_group(
                    "第一組：前五年（同期數）",
                    period_refs,
                    total_label=f"前五年 同期數: 第{self._issue_number(base_draw.period)}期",
                )
            )

        year_date_matches: List[Draw] = []
        for year in reversed(target_years):
            year_date_matches.extend(self._matches_for_year(year, base_draw, mode="date"))
        if not year_date_matches:
            self.main_output_layout.addWidget(QLabel("找不到可比對的前五年同日期資料。"))
        else:
            date_refs = self._group_draws_by_date(year_date_matches)
            self.main_output_layout.addWidget(
                self._build_reference_group(
                    "第一組：前五年（同日期）",
                    date_refs,
                    total_label=f"前五年 同日期: {base_draw.day}號",
                )
            )

        year_weekday_matches: List[Draw] = []
        for year in reversed(target_years):
            year_weekday_matches.extend(self._matches_for_year(year, base_draw, mode="weekday"))
        if not year_weekday_matches:
            self.main_output_layout.addWidget(QLabel("找不到可比對的前五年同週次資料。"))
        else:
            weekday_refs = self._group_draws_by_date(year_weekday_matches)
            self.main_output_layout.addWidget(
                self._build_reference_group(
                    "第一組：前五年（同月同週次）",
                    weekday_refs,
                    total_label=f"前五年 同月同週次: {dt.month}月{self._weekday_label(base_draw)}",
                )
            )

        month_date_matches: List[Draw] = []
        for offset in range(1, 13):
            prev_month = self._shift_months(dt, offset)
            month_date_matches.extend(self._matches_for_month(prev_month.year, prev_month.month, base_draw, mode="date"))
        if not month_date_matches:
            self.main_output_layout.addWidget(QLabel("找不到可比對的前十二月同日期資料。"))
        else:
            month_date_refs = self._group_draws_by_date(month_date_matches)
            self.main_output_layout.addWidget(
                self._build_reference_group(
                    "第二組：前十二月（同日期）",
                    month_date_refs,
                    total_label=f"前十二月 同日期: {base_draw.day}號",
                )
            )

        month_weekday_matches: List[Draw] = []
        for offset in range(1, 13):
            prev_month = self._shift_months(dt, offset)
            month_weekday_matches.extend(self._matches_for_month(prev_month.year, prev_month.month, base_draw, mode="weekday"))
        if month_weekday_matches:
            month_weekday_refs = self._group_draws_by_date(month_weekday_matches)
            self.main_output_layout.addWidget(
                self._build_reference_group(
                    "第二組：前十二月（同週次）",
                    month_weekday_refs,
                    total_label=f"前十二月 同週次: {self._weekday_label(base_draw)}",
                )
            )

    def _clear_main_output(self) -> None:
        while self.main_output_layout.count():
            item = self.main_output_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def run_search(self) -> None:
        if not self.analyzer.draws:
            QMessageBox.information(self, "提示", "尚未載入資料")
            return

        flt = self.build_filter()
        result = self.analyzer.analyze(flt)
        draws: List[Draw] = result["draws"]
        he_stat = result["he"]
        wei_stat = result["wei"]

        self.summary_label.setText(
            f"結果摘要：符合 {result['draw_count']} 期，統計號碼 {result['number_count']} 顆"
        )

        he_rows = he_stat.rows(Analyzer.HE_KEYS)
        wei_rows = wei_stat.rows(Analyzer.WEI_KEYS)
        self.he_chart.update_data(he_rows, "合數")
        self.wei_chart.update_data(wei_rows, "尾數")
        self._fill_stat_table(self.he_stat_table, he_rows)
        self._fill_stat_table(self.wei_stat_table, wei_rows)
        self._fill_draw_table(draws)
        self.statusBar().showMessage(
            f"搜尋完成：{result['draw_count']} 期 / {result['number_count']} 號碼"
        )

    def _fill_stat_table(self, table: QTableWidget, rows) -> None:
        table.setRowCount(len(rows))
        for r, (key, count, pct) in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(str(key)))
            table.setItem(r, 1, QTableWidgetItem(str(count)))
            table.setItem(r, 2, QTableWidgetItem(f"{pct:.2f}%"))

    def _fill_draw_table(self, draws: List[Draw]) -> None:
        # 避免一次塞太多導致 UI 卡死
        max_rows = 500
        show = draws[-max_rows:] if len(draws) > max_rows else draws
        self.draw_table.setRowCount(len(show))
        for r, draw in enumerate(reversed(show)):
            nums = " ".join(f"{n:02d}" for n in draw.numbers)
            he = ",".join(str(x) for x in draw.he_list())
            wei = ",".join(str(x) for x in draw.wei_list())
            self.draw_table.setItem(r, 0, QTableWidgetItem(str(draw.period)))
            self.draw_table.setItem(r, 1, QTableWidgetItem(draw.date))
            self.draw_table.setItem(r, 2, QTableWidgetItem(nums))
            self.draw_table.setItem(r, 3, QTableWidgetItem(f"合[{he}] 尾[{wei}]"))
        if len(draws) > max_rows:
            self.statusBar().showMessage(
                self.statusBar().currentMessage()
                + f"（期別表僅顯示最近 {max_rows} 期）"
            )
