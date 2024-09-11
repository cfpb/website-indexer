import codecs
from io import BytesIO

from django.test import TestCase
from django.urls import reverse


class TestCSVExport(TestCase):
    fixtures = ["sample.json"]

    def test_csv_generation(self):
        response = self.client.get(reverse("index") + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")

        rows = BytesIO(response.getvalue()).readlines()
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], codecs.BOM_UTF8 + b"url,title,language\r\n")
