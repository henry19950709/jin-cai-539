from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import Draw, SearchFilter, digit_sum, tail_digit


@dataclass
class DistStat:
    counts: Dict[int, int]
    total: int

    def percent(self, key: int) -> float:
        if self.total <= 0:
            return 0.0
        return 100.0 * self.counts.get(key, 0) / self.total

    def rows(self, keys: List[int]) -> List[Tuple[int, int, float]]:
        return [(k, self.counts.get(k, 0), self.percent(k)) for k in keys]


class Analyzer:
    """以記憶體中的歷史資料做篩選與合數/尾數統計。"""

    HE_KEYS = list(range(1, 13))  # 01~39 合數最大 3+9=12
    WEI_KEYS = list(range(0, 10))

    def __init__(self, draws: List[Draw] | None = None):
        self.draws: List[Draw] = list(draws or [])

    def set_draws(self, draws: List[Draw]) -> None:
        self.draws = list(draws)

    def filter_draws(self, flt: SearchFilter) -> List[Draw]:
        result: List[Draw] = []
        for draw in self.draws:
            if flt.year is not None and draw.year != flt.year:
                continue
            if flt.month is not None and draw.month != flt.month:
                continue
            if flt.period_from is not None and draw.period < flt.period_from:
                continue
            if flt.period_to is not None and draw.period > flt.period_to:
                continue
            if not draw.has_he(flt.he_values):
                continue
            if not draw.has_wei(flt.wei_values):
                continue
            result.append(draw)
        return result

    def collect_numbers(self, draws: List[Draw], flt: SearchFilter) -> List[int]:
        numbers: List[int] = []
        for draw in draws:
            for n in draw.numbers:
                if flt.match_numbers_only:
                    if flt.he_values and digit_sum(n) not in flt.he_values:
                        continue
                    if flt.wei_values and tail_digit(n) not in flt.wei_values:
                        continue
                numbers.append(n)
        return numbers

    def he_distribution(self, numbers: List[int]) -> DistStat:
        counter = Counter(digit_sum(n) for n in numbers)
        return DistStat(counts=dict(counter), total=len(numbers))

    def wei_distribution(self, numbers: List[int]) -> DistStat:
        counter = Counter(tail_digit(n) for n in numbers)
        return DistStat(counts=dict(counter), total=len(numbers))

    def analyze(self, flt: SearchFilter) -> dict:
        draws = self.filter_draws(flt)
        numbers = self.collect_numbers(draws, flt)
        he_stat = self.he_distribution(numbers)
        wei_stat = self.wei_distribution(numbers)
        return {
            "draws": draws,
            "numbers": numbers,
            "draw_count": len(draws),
            "number_count": len(numbers),
            "he": he_stat,
            "wei": wei_stat,
        }
