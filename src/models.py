from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


def digit_sum(number: int) -> int:
    """合數：各位數字相加。例：19 → 10、28 → 10。"""
    n = abs(int(number))
    return (n // 10) + (n % 10)


def tail_digit(number: int) -> int:
    """尾數：個位數字 0~9。"""
    return abs(int(number)) % 10


@dataclass
class Draw:
    period: int
    date: str  # YYYY-MM-DD
    numbers: List[int] = field(default_factory=list)

    @property
    def year(self) -> int:
        return int(self.date[:4])

    @property
    def month(self) -> int:
        return int(self.date[5:7])

    @property
    def day(self) -> int:
        return int(self.date[8:10])

    def he_list(self) -> List[int]:
        return [digit_sum(n) for n in self.numbers]

    def wei_list(self) -> List[int]:
        return [tail_digit(n) for n in self.numbers]

    def has_he(self, values: List[int]) -> bool:
        if not values:
            return True
        he_set = set(self.he_list())
        return any(v in he_set for v in values)

    def has_wei(self, values: List[int]) -> bool:
        if not values:
            return True
        wei_set = set(self.wei_list())
        return any(v in wei_set for v in values)

    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "date": self.date,
            "numbers": list(self.numbers),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Draw":
        return cls(
            period=int(data["period"]),
            date=str(data["date"])[:10],
            numbers=[int(n) for n in data["numbers"]],
        )


@dataclass
class SearchFilter:
    year: Optional[int] = None
    month: Optional[int] = None
    period_from: Optional[int] = None
    period_to: Optional[int] = None
    he_values: List[int] = field(default_factory=list)  # 合數 1~12
    wei_values: List[int] = field(default_factory=list)  # 尾數 0~9
    # True: 只統計符合合數/尾數條件的「號碼」
    # False: 用合數/尾數篩選「期別」，再統計該期全部號碼
    match_numbers_only: bool = False
