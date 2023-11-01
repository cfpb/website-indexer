from operator import attrgetter
from unittest.mock import patch

import lxml.etree

from django.test import SimpleTestCase

from crawler.models import Error, Page, Redirect


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


class ErrorTests(SimpleTestCase):
    def test_error_str(self):
        self.assertEqual(
            str(Error(url="/not-found/", status_code=404)), "/not-found/ 404 !"
        )

    def test_error_str_with_referrer(self):
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
