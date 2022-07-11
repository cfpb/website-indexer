import os

from django.conf import settings
from django.db.models import Count, Max, Min

from .models import Page


def crawl_stats(request):
    crawl_stats = Page.objects.values("crawled_at").aggregate(
        count=Count("crawled_at"),
        start=Min("crawled_at"),
        end=Max("crawled_at"),
    )

    crawl_stats.update(
        {
            "duration": crawl_stats["end"] - crawl_stats["start"],
            "database_size": os.path.getsize(settings.CRAWL_DATABASE),
        }
    )

    return {"crawl_stats": crawl_stats}
