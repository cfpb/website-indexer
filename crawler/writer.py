import logging

from django.db import connections

from crawler.models import Component, Link, Page


logger = logging.getLogger("crawler")


class DatabaseWriter:
    def __init__(self, crawl):
        self.crawl = crawl

    def write(self, instance):
        if isinstance(instance, Page):
            return self._write_page(instance)
        else:
            logger.debug(f"Saving {instance}")
            instance.crawl = self.crawl
            instance.save()

    def _write_page(self, page):
        page.crawl = self.crawl

        for component in page.components.all():
            component.crawl = self.crawl

        Component.objects.bulk_create(page.components.all(), ignore_conflicts=True)

        page.components = Component.objects.in_bulk(
            page.components.values_list("class_name", flat=True),
            field_name="class_name",
        ).values()

        Link.objects.bulk_create(page.links.all(), ignore_conflicts=True)

        page.links = Link.objects.in_bulk(
            page.links.values_list("href", flat=True), field_name="href"
        ).values()

        logger.debug(f"Saving {page}")
        page.save()
