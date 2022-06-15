import os.path

from django import template
from django.db.models import Max, Min

from humanize import precisedelta as humanize_precisedelta

from ..database import get_crawl_database_filename
from ..models import Page


register = template.Library()


@register.simple_tag()
def get_last_crawl():
    crawl = Page.objects.aggregate(
        start=Min("timestamp"),
        end=Max("timestamp")
    )

    crawl["duration"] = crawl["end"] - crawl["start"]

    return crawl


@register.simple_tag()
def get_database_file_size():
    if filename := get_crawl_database_filename():
        return os.path.getsize(filename)


@register.filter
def precisedelta(timedelta):
    return humanize_precisedelta(timedelta)
