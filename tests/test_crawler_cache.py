import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.crawler import Daily539Crawler
from src.models import Draw


class CrawlerCacheTests(unittest.TestCase):
    def test_crawl_all_uses_existing_cache_without_network(self) -> None:
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "daily539_cache.json"
            crawler = Daily539Crawler(cache_path)
            expected = [Draw(period=1, date="2024-01-01", numbers=[1, 2, 3, 4, 5])]
            crawler.save_cache(expected)

            with patch.object(
                crawler,
                "_crawl_via_monthly_api",
                side_effect=AssertionError("should not crawl when cache exists"),
            ) as mocked_monthly:
                result = crawler.crawl_all()

            self.assertEqual(result, expected)
            mocked_monthly.assert_not_called()


if __name__ == "__main__":
    unittest.main()
