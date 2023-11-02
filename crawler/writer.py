import logging

from django.db import connections

from crawler.models import Component, Link, Page


logger = logging.getLogger("crawler")


class DatabaseWriter:
    def __init__(self, db):
        self.db = db
        self.connection = connections[self.db]

    def write(self, instance):
        if isinstance(instance, Page):
            return self._write_page(instance)
        else:
            logger.debug(f"Saving {instance}")
            instance.save(using=self.db)

    def _write_page(self, page):
        Component.objects.using(self.db).bulk_create(
            page.components.all(), ignore_conflicts=True
        )

        page.components = (
            Component.objects.using(self.db)
            .in_bulk(
                page.components.values_list("class_name", flat=True),
                field_name="class_name",
            )
            .values()
        )

        Link.objects.using(self.db).bulk_create(page.links.all(), ignore_conflicts=True)

        page.links = (
            Link.objects.using(self.db)
            .in_bulk(page.links.values_list("href", flat=True), field_name="href")
            .values()
        )

        logger.debug(f"Saving {page}")
        page.save(using=self.db)

    def analyze(self):
        with self.connection.cursor() as cursor:
            cursor.execute("ANALYZE")
