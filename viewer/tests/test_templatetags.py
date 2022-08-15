from datetime import datetime, timezone

from django.test import RequestFactory, SimpleTestCase

from viewer.templatetags.viewer import format_datetime, results_summary


class FormatDatetimeTests(SimpleTestCase):
    def test_format(self):
        self.assertEqual(
            format_datetime(datetime(2022, 8, 11, 16, 54, 29, tzinfo=timezone.utc)),
            "Aug. 11, 2022, 12:54 p.m. EDT",
        )

    def test_format_am(self):
        self.assertEqual(
            format_datetime(datetime(2022, 8, 11, 12, 54, 29, tzinfo=timezone.utc)),
            "Aug. 11, 2022, 8:54 a.m. EDT",
        )


class ResultsSummaryTests(SimpleTestCase):
    def make_context(self, count=1000, **kwargs):
        return {
            "request": RequestFactory().get("/", kwargs),
            "count": count,
        }

    def check_default_response(self, **kwargs):
        context = self.make_context(**kwargs)
        self.assertEqual(results_summary(context), "Showing all 1,000 indexed pages")

    def test_no_query_params(self):
        self.check_default_response()

    def test_no_q(self):
        self.check_default_response(search_type="foo")

    def test_no_search_type(self):
        self.check_default_response(q="foo")

    def test_invalid_search_type_raises_exception(self):
        context = self.make_context(search_type="invalid", q="foo")
        with self.assertRaises(KeyError):
            results_summary(context)

    def check_response(self, kwargs, expected):
        context = self.make_context(**kwargs)
        self.assertEqual(results_summary(context), expected)

    def test_title(self):
        self.check_response(
            {"search_type": "title", "q": "foo"},
            '1,000 pages with "foo" in the page title',
        )

    def test_title_single_result(self):
        self.check_response(
            {"search_type": "title", "q": "foo", "count": 1},
            '1 page with "foo" in the page title',
        )

    def test_title_truncates(self):
        self.check_response(
            {"search_type": "title", "q": "abcdefghijklmnopqrstuvwxyz"},
            '1,000 pages with "abcdefghijklmnopqrstuvwx..." in the page title',
        )

    def test_url(self):
        self.check_response(
            {"search_type": "url", "q": "foo"},
            '1,000 pages with "foo" in the page URL',
        )

    def test_components(self):
        self.check_response(
            {"search_type": "components", "q": "foo"},
            '1,000 pages with "foo" in components',
        )

    def test_links(self):
        self.check_response(
            {"search_type": "links", "q": "foo"},
            '1,000 pages with "foo" in link URLs',
        )

    def test_text(self):
        self.check_response(
            {"search_type": "text", "q": "foo"},
            '1,000 pages with "foo" in full text',
        )

    def test_html(self):
        self.check_response(
            {"search_type": "html", "q": "foo"},
            '1,000 pages with "foo" in page HTML',
        )

    def test_no_results(self):
        self.check_response({"count": 0}, "There are no indexed pages")
