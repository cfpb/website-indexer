from django.test import TestCase
from django.utils import timezone

from crawler.models import Component, Crawl, Error, Page
from crawler.writer import DatabaseWriter


class DatabaseWriterTests(TestCase):
    def setUp(self):
        self.crawl = Crawl.objects.create(config={}, status=Crawl.Status.FINISHED)
        self.writer = DatabaseWriter(self.crawl)
        self.now = timezone.now()

    def test_write_page(self):
        self.assertEqual(Page.objects.count(), 0)
        self.assertEqual(Component.objects.count(), 0)

        page = Page(timestamp=self.now, title="test", html="test", text="test")
        page.components = [Component(class_name="o-test")]

        self.writer.write(page)

        self.assertEqual(Page.objects.count(), 1)
        page = Page.objects.first()
        self.assertEqual(page.title, "test")
        self.assertEqual(page.crawl, self.crawl)
        self.assertEqual(page.components.count(), 1)

        self.assertEqual(Component.objects.count(), 1)
        component = Component.objects.first()
        self.assertEqual(component.class_name, "o-test")

    def test_write_error(self):
        self.assertEqual(Error.objects.count(), 0)

        error = Error(timestamp=self.now, status_code=500)

        self.writer.write(error)

        self.assertEqual(Error.objects.count(), 1)
        error = Error.objects.first()
        self.assertEqual(error.crawl, self.crawl)
        self.assertEqual(error.status_code, 500)
