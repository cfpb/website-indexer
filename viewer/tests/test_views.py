import codecs
import json
import re
from io import BytesIO
from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse


class CSVTestMixin:
    CSV_BOM_UTF8_RE = re.compile(rb"^" + codecs.BOM_UTF8 + rb".*$")

    def get_csv(self, url, **search_kwargs):
        search_kwargs["format"] = "csv"

        response = self.client.get(url + "?" + urlencode(search_kwargs))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")

        rows = BytesIO(response.getvalue()).readlines()

        self.assertRegex(rows[0], self.CSV_BOM_UTF8_RE)
        rows[0] = rows[0][len(codecs.BOM_UTF8) :]

        return rows


class ViewTests(CSVTestMixin, TestCase):
    fixtures = ["sample.json"]

    def test_search_view(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Sample homepage")

    def get_pages_api(self, **search_kwargs):
        search_kwargs["format"] = "json"

        response = self.client.get(reverse("index") + "?" + urlencode(search_kwargs))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        results = json.loads(response.content)
        return results["results"]

    def test_search_default(self):
        results = self.get_pages_api()
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["title"], "Sample homepage")

    def test_search_by_html(self):
        results = self.get_pages_api(
            search_type="html", q='<a href="https://example.com/">'
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Sample homepage")

    def check_search_by_text(self, q):
        results = self.get_pages_api(search_type="text", q=q)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Sample child page")

    def test_search_by_text(self):
        self.check_search_by_text("Sample child page")

    def test_search_by_text_case_insensitive(self):
        self.check_search_by_text("SAMPLE CHILD PAGE")

    def test_search_by_title(self):
        results = self.get_pages_api(search_type="title", q="Sample child page")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Sample child page")

    def test_search_by_url(self):
        results = self.get_pages_api(search_type="url", q="/child")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Sample child page")

    def test_search_invalid_type_falls_back_to_default(self):
        results = self.get_pages_api(search_type="invalid")
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["title"], "Sample homepage")

    def test_pages_csv(self):
        rows = self.get_csv(reverse("index"))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], b"url,title,language\r\n")

    def test_search_components(self):
        results = self.get_pages_api(search_type="components", q="o-sample")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Sample homepage")

    def test_search_links(self):
        results = self.get_pages_api(search_type="links", q="example.com")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Sample homepage")

    def test_components_csv(self):
        rows = self.get_csv(reverse("index"), search_type="components")
        self.assertEqual(
            rows,
            [
                b"url,title,language,class_name\r\n",
                b"http://localhost:8000/,Sample homepage,en,o-sample\r\n",
            ],
        )

    def test_links_csv(self):
        rows = self.get_csv(reverse("index"), search_type="links")
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[0], b"url,title,language,link_url\r\n")
        self.assertEqual(
            rows[1], b"http://localhost:8000/,Sample homepage,en,./file.xlsx\r\n"
        )

    def test_errors_csv(self):
        rows = self.get_csv(reverse("errors"))
        self.assertEqual(
            rows,
            [
                b"url,status_code,referrer\r\n",
                b"https://example.com/file.xlsx,404,http://localhost:8000/\r\n",
            ],
        )

    def test_redirects_csv(self):
        rows = self.get_csv(reverse("redirects"))
        self.assertEqual(
            rows,
            [
                b"url,status_code,referrer,redirect_url,is_http_to_https,is_append_slash\r\n"
            ],
        )

    def test_component_view(self):
        response = self.client.get(reverse("components"))
        self.assertContains(response, "o-sample")

    def test_detail_view(self):
        response = self.client.get(reverse("page") + "?url=http://localhost:8000/")
        self.assertContains(response, "Sample homepage")


class ViewTestsNoCrawls(CSVTestMixin, TestCase):
    def test_errors_csv(self):
        rows = self.get_csv(reverse("errors"))
        self.assertEqual(
            rows,
            [
                b"url,status_code,referrer\r\n",
            ],
        )
