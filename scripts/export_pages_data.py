from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "daily539_cache.json"
DOCS_DATA_DIR = ROOT / "docs" / "data"
OUTPUT_SUMMARY = DOCS_DATA_DIR / "summary.json"
OUTPUT_CACHE = DOCS_DATA_DIR / "cache.json"


def digit_sum(value: int) -> int:
    return (value // 10) + (value % 10)


def load_cache() -> tuple[list[dict], str | None]:
    if not CACHE_PATH.exists():
        raise FileNotFoundError(f"Missing cache file: {CACHE_PATH}")

    with CACHE_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    draws = payload.get("draws") if isinstance(payload, dict) else payload
    if not isinstance(draws, list):
        raise ValueError("Cache JSON must contain a 'draws' list")
    periods: set[int] = set()
    for draw in draws:
        period = int(draw["period"])
        numbers = [int(number) for number in draw["numbers"]]
        date.fromisoformat(draw["date"])
        if period in periods or len(numbers) != 5 or len(set(numbers)) != 5 or any(
            number < 1 or number > 39 for number in numbers
        ):
            raise ValueError(f"Invalid or duplicate draw: {period}")
        periods.add(period)
    return sorted(draws, key=lambda draw: (draw["date"], int(draw["period"]))), (
        payload.get("updated_at") if isinstance(payload, dict) else None
    )


def build_summary(draws: list[dict]) -> dict:
    if not draws:
        return {
            "draw_count": 0,
            "latest_date": None,
            "latest_period": None,
            "recent_dates": [],
            "yearly_counts": {},
            "he_distribution": {},
            "wei_distribution": {},
        }

    ordered = sorted(draws, key=lambda d: int(d["period"]))
    latest = ordered[-1]
    recent = ordered[-10:]

    yearly_counts: Counter[str] = Counter()
    he_counts: Counter[int] = Counter()
    wei_counts: Counter[int] = Counter()

    for draw in ordered:
        date_text = str(draw.get("date", ""))
        if len(date_text) >= 4 and date_text[:4].isdigit():
            yearly_counts[date_text[:4]] += 1
        for number in draw.get("numbers", []):
            he_counts[digit_sum(int(number))] += 1
            wei_counts[int(number) % 10] += 1

    return {
        "draw_count": len(ordered),
        "latest_date": latest.get("date"),
        "latest_period": int(latest.get("period", 0)),
        "recent_dates": [d.get("date") for d in recent],
        "yearly_counts": {k: yearly_counts[k] for k in sorted(yearly_counts)},
        "he_distribution": {str(k): he_counts[k] for k in sorted(he_counts)},
        "wei_distribution": {str(k): wei_counts[k] for k in sorted(wei_counts)},
    }


def main() -> None:
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    draws, updated_at = load_cache()
    summary = build_summary(draws)
    summary["updated_at"] = updated_at

    with OUTPUT_CACHE.open("w", encoding="utf-8") as fh:
        json.dump(
            {"updated_at": updated_at, "count": len(draws), "draws": draws},
            fh,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    with OUTPUT_SUMMARY.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"Exported {len(draws)} draws into {OUTPUT_CACHE}")
    print(f"Summary saved to {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
