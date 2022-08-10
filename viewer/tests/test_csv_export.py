import codecs
from unittest import skip

from django.test import TestCase
from django.urls import reverse


@skip("TODO, currently broken")
class TestCSVExport(TestCase):
    def test_csv_generation(self):
        response = self.client.get(reverse("download-csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.getvalue(),
            codecs.BOM_UTF8
            + b"path,title,crawled_at,hash\r\n"
            + b"/,Sample homepage,2022-06-14 16:16:40,34f605eb65d9570d06c6521c48bb75da\r\n"
            + b"/child/,Sample child page,2022-06-14 16:16:41,3022b3b15b5c9d8794c32769b3234ddb\r\n",
        )
