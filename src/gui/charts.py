from __future__ import annotations

from typing import List, Tuple

import matplotlib
from matplotlib import font_manager as fm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QSizePolicy, QVBoxLayout, QWidget


def _configure_chinese_font() -> None:
    preferred_families = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "Source Han Sans CN",
        "Arial Unicode MS",
        "sans-serif",
    ]
    available = {font.name for font in fm.fontManager.ttflist}
    selected = [family for family in preferred_families if family in available]
    if not selected:
        selected = ["DejaVu Sans"]
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = selected
    matplotlib.rcParams["axes.unicode_minus"] = False


_configure_chinese_font()


class DistChart(QWidget):
    """合數 / 尾數次數與百分比長條圖。"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 3), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._title = title
        self.clear()

    def clear(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_title(self._title)
        ax.text(0.5, 0.5, "尚無資料", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas.draw_idle()

    def update_data(self, rows: List[Tuple[int, int, float]], xlabel: str) -> None:
        """rows: (key, count, percent)"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if not rows or sum(r[1] for r in rows) == 0:
            ax.set_title(self._title)
            ax.text(0.5, 0.5, "查無符合條件的資料", ha="center", va="center", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            self.canvas.draw_idle()
            return

        keys = [str(r[0]) for r in rows]
        counts = [r[1] for r in rows]
        percents = [r[2] for r in rows]
        max_count = max(counts) if counts else 0

        colors = []
        for cnt in counts:
            if cnt == max_count and max_count > 0:
                colors.append("#F59E0B")
            else:
                colors.append("#60A5FA")

        bars = ax.bar(keys, counts, color=colors, edgecolor="#1E3A8A", linewidth=0.6)
        ax.set_title(self._title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("次數")
        ax.grid(axis="y", linestyle="--", alpha=0.35)

        ymax = max(counts) if counts else 1
        for bar, pct, cnt in zip(bars, percents, counts):
            if cnt <= 0:
                continue
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ymax * 0.01,
                f"{pct:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#111827" if cnt == max_count else "#374151",
                fontweight="bold" if cnt == max_count else "normal",
            )

        for label in ax.get_xticklabels():
            label.set_fontsize(9)
        self.canvas.draw_idle()
