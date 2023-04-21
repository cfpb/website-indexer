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

    crawl_start = crawl_stats["start"]
    crawl_end = crawl_stats["end"]

    if crawl_start and crawl_end:
        duration = crawl_end - crawl_start
    else:
        duration = None

    crawl_stats.update(
        {
            "duration": duration,
            "database_size": os.path.getsize(settings.CRAWL_DATABASE),
        }
    )

    return {"crawl_stats": crawl_stats}
