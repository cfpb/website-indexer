import os

from django.conf import settings
from django.db.models import Count, Max, Min

from crawler.models import Page


def crawl_stats(request=None):
    crawl_stats = Page.objects.values("timestamp").aggregate(
        count=Count("timestamp"),
        start=Min("timestamp"),
        end=Max("timestamp"),
    )

    crawl_stats.update(
        {
            "duration": crawl_stats["end"] - crawl_stats["start"],
            "database_size": os.path.getsize(settings.CRAWL_DATABASE),
        }
    )

    return {"crawl_stats": crawl_stats}
