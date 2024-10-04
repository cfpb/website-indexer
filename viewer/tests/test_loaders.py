from django.template.loader import render_to_string
from django.test import SimpleTestCase


class IgnoreMissingSVGsTemplateLoaderTests(SimpleTestCase):
    def test_loader_returns_empty_content(self):
        self.assertEqual(render_to_string("nonexistent.svg"), "")
