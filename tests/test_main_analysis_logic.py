import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PyQt5.QtWidgets import QApplication

from src.crawler import Daily539Crawler
from src.gui.main_window import MainWindow
from src.models import Draw


class MainAnalysisLogicTests(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.window = MainWindow(Path("data"))

    def test_same_date_ignores_weekday_fallback(self):
        base = Draw(period=217, date="2024-08-10", numbers=[1, 2, 3, 4, 5])
        draws = [
            Draw(period=211, date="2024-07-11", numbers=[10, 11, 12, 13, 14]),
            Draw(period=212, date="2024-06-10", numbers=[20, 21, 22, 23, 24]),
            Draw(period=214, date="2023-08-10", numbers=[30, 31, 32, 33, 34]),
        ]
        self.window.analyzer.set_draws(draws + [base])

        matches = self.window._collect_reference_matches(
            [2023, 2024],
            base,
            "date",
            year_window=True,
            max_rows=5,
        )

        self.assertEqual(len(matches), 1)
        self.assertTrue(any("2023年" in label for label, _ in matches))
        self.assertFalse(any("2024年" in label for label, _ in matches))
        self.assertFalse(any("07月11日" in label for label, _ in matches))

    def test_previous_year_period_matches_period_number_only(self):
        base = Draw(period=100, date="2024-08-10", numbers=[1, 2, 3, 4, 5])
        draws = [
            Draw(period=100, date="2023-07-11", numbers=[10, 11, 12, 13, 14]),
            Draw(period=100, date="2022-03-08", numbers=[20, 21, 22, 23, 24]),
            Draw(period=101, date="2021-08-10", numbers=[30, 31, 32, 33, 34]),
        ]
        self.window.analyzer.set_draws(draws + [base])

        matches = self.window._collect_reference_matches(
            [2021, 2022, 2023, 2024],
            base,
            "period",
            year_window=True,
            max_rows=5,
        )

        self.assertEqual(len(matches), 2)
        self.assertTrue(all(draw.period == 100 for _, group in matches for draw in group))

    def test_year_prefixed_period_uses_issue_number_for_same_period_match(self):
        base = Draw(period=115000194, date="2026-08-11", numbers=[1, 2, 3, 4, 5])
        draws = [
            Draw(period=114000194, date="2025-08-11", numbers=[10, 11, 12, 13, 14]),
            Draw(period=113000194, date="2024-08-11", numbers=[20, 21, 22, 23, 24]),
            Draw(period=115000195, date="2026-08-12", numbers=[30, 31, 32, 33, 34]),
        ]
        self.window.analyzer.set_draws(draws + [base])

        matches = self.window._collect_reference_matches(
            [2024, 2025, 2026],
            base,
            "period",
            year_window=True,
            max_rows=5,
        )

        self.assertEqual(len(matches), 2)
        self.assertTrue(all(self.window._issue_number(draw.period) == 194 for _, group in matches for draw in group))

    def test_refresh_to_latest_updates_stale_cache(self):
        with TemporaryDirectory() as tmpdir:
            crawler = Daily539Crawler(Path(tmpdir) / 'test_cache.json')
            base = Draw(period=115000194, date='2026-08-11', numbers=[1, 2, 3, 4, 5])
            crawler.save_cache([base])

            def fake_fetch_month(year, month):
                if (year, month) == (2026, 8):
                    return [Draw(period=115000195, date='2026-08-12', numbers=[10, 11, 12, 13, 14])]
                return []

            crawler.fetch_month = fake_fetch_month
            updated = crawler.refresh_to_latest()

            self.assertTrue(any(draw.period == 115000195 for draw in updated))
            self.assertTrue(any(draw.date == '2026-08-12' for draw in updated))


if __name__ == "__main__":
    unittest.main()
