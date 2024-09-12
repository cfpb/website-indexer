from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from crawler.models import Crawl, Page
from viewer.context_processors import crawl_stats


class CrawlStatsTests(TestCase):
    def test_crawl_stats_no_crawls(self):
        self.assertEqual(
            crawl_stats(),
            {
                "crawl_stats": {
                    "count": 0,
                    "start": None,
                    "end": None,
                    "duration": None,
                }
            },
        )

    def test_crawl_stats(self):
        start = datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))
        end = datetime(2024, 1, 1, 1, tzinfo=ZoneInfo("UTC"))

        crawl = Crawl.objects.create(status=Crawl.Status.FINISHED, config={})
        Page.objects.create(crawl=crawl, timestamp=start, url="/1/")
        Page.objects.create(crawl=crawl, timestamp=end, url="/2/")

        self.assertEqual(
            crawl_stats(),
            {
                "crawl_stats": {
                    "count": 2,
                    "start": start,
                    "end": end,
                    "duration": end - start,
                }
            },
        )
