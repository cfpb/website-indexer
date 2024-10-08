from unittest.mock import patch

import lxml.etree

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from crawler.models import Crawl, CrawlConfig, Error, Page, Redirect


class CrawlTests(TestCase):
    def test_lifecycle(self):
        self.assertFalse(Crawl.objects.exists())

        config = CrawlConfig(start_url="https://example.com")
        crawl = Crawl.start(config)
        self.assertEqual(
            crawl.config,
            {"start_url": "https://example.com", "max_pages": 0, "depth": 0},
        )
        self.assertEqual(crawl.status, Crawl.Status.STARTED)

        crawl.finish()
        self.assertEqual(crawl.status, Crawl.Status.FINISHED)
        self.assertIsNone(crawl.failure_message)

        crawl.fail("Testing crawl failure")
        self.assertEqual(crawl.status, Crawl.Status.FAILED)
        self.assertEqual(crawl.failure_message, "Testing crawl failure")

    def test_repr(self):
        now = timezone.now()

        self.assertEqual(
            str(
                Crawl(pk=123, started=now, config={"start_url": "https://example.com"})
            ),
            f"Crawl 123 (Started) started {now}, config {{'start_url': 'https://example.com'}}",
        )

        self.assertEqual(
            str(
                Crawl(
                    pk=123,
                    started=now,
                    status=Crawl.Status.FAILED,
                    config={"start_url": "https://example.com"},
                    failure_message="It broke!",
                )
            ),
            f"Crawl 123 (Failed) started {now}, config {{'start_url': 'https://example.com'}}, failure message: It broke!",
        )


class PageTests(SimpleTestCase):
    def test_from_html_no_title_returns_none(self):
        self.assertIsNone(
            Page.from_html(
                "https://example.com/",
                "<html><head></head><body>This page has no title.</body></html>",
                "example.com",
            )
        )

    def check_from_html(self):
        html = """
<html lang="en">
<head><title>Test page</title></head>
<body>
    <script>Ignore me!</script>
    <div class="m-links">Links</div>
        <div><a href="/page/">A regular link on the same domain.</a></div>
        <div class="a-external-link">
            <a href="/external-site/?ext_url=https%3A%2F%2Fexample.org%2F">
                An external link pointing to another domain
            </a>
            <a href="/external-site/">
                An external link missing its target
            </a>
            <a href="https://example.org/external-site/">
                A link on another domain that also uses /external-site/
            </a>
        </div>
</body>
</html>
        """.strip()

        page = Page.from_html("https://example.com/", html, "example.com")
        self.assertEqual(str(page), "https://example.com/")
        self.assertEqual(page.title, "Test page")
        self.assertEqual(page.language, "en")
        self.assertEqual(page.html, html)
        self.assertEqual(
            page.text,
            (
                "Links "
                "A regular link on the same domain. "
                "An external link pointing to another domain "
                "An external link missing its target "
                "A link on another domain that also uses /external-site/"
            ),
        )
        self.assertCountEqual(
            page.components.values_list("class_name", flat=True),
            ["a-external-link", "m-links"],
        )
        self.assertCountEqual(
            page.links.values_list("href", flat=True),
            [
                "/external-site/",
                "/page/",
                "https://example.org/",
                "https://example.org/external-site/",
            ],
        )

    def test_from_html(self):
        self.check_from_html()

    def test_from_html_etree_fallback_parser(self):
        with patch(
            "lxml.html.fromstring",
            side_effect=lxml.etree.ParserError("testing parser error"),
        ):
            self.check_from_html()

    def test_from_html_no_body(self):
        html = '<html lang="en"><head><title>Test page with no body</head></html>'
        page = Page.from_html("https://example.com/", html, "example.com")
        self.assertEqual(str(page), "https://example.com/")
        self.assertEqual(page.title, "Test page with no body")
        self.assertEqual(page.language, "en")
        self.assertEqual(page.html, html)
        self.assertIsNone(page.text)


class PageQuerySetTestsNoPages(TestCase):
    def test_no_crawls_no_pages(self):
        self.assertFalse(Page.objects.exists())

    def test_default_queryset_uses_latest_crawl(self):
        Crawl.objects.create(status=Crawl.Status.FINISHED, config={})
        second_crawl = Crawl.objects.create(status=Crawl.Status.FINISHED, config={})

        page = Page.objects.create(
            crawl=second_crawl,
            timestamp=timezone.now(),
            url="https://example.com",
            title="test",
            html="<html>",
            text="text",
        )

        self.assertEqual(Page.objects.all().count(), 1)
        self.assertEqual(Page.objects.first(), page)


class PageQuerySetTests(TestCase):
    fixtures = ["sample.json"]

    def test_crawl_has_pages(self):
        self.assertTrue(Page.objects.exists())


class ErrorTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(
            str(Error(url="/not-found/", status_code=404)), "/not-found/ 404 !"
        )


class RedirectTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(
            str(
                Redirect(
                    url="/redirect/",
                    referrer="/source/",
                    status_code=301,
                    location="/destination/",
                )
            ),
            "/redirect/ (from /source/) 301 -> /destination/",
        )

    def test_is_http_to_https(self):
        self.assertTrue(
            Redirect(
                url="http://example.com/", location="https://example.com/"
            ).is_http_to_https
        )

        self.assertFalse(
            Redirect(
                url="http://example.com/", location="https://example.com"
            ).is_http_to_https
        )

        self.assertFalse(
            Redirect(url="https://example.com/", location="/foo/").is_http_to_https
        )

    def test_is_append_slash(self):
        self.assertTrue(
            Redirect(
                url="https://example.com", location="https://example.com/"
            ).is_append_slash
        )

        self.assertFalse(
            Redirect(url="https://example.com/", location="/foo/").is_append_slash
        )
