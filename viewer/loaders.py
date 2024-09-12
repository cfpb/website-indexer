import re

from django.template.base import Origin
from django.template.loaders.base import Loader


SVG_FILENAME = re.compile(r"^.*\.svg$")


class IgnoreMissingSVGsTemplateLoader(Loader):
    def get_template_sources(self, template_name):
        if SVG_FILENAME.match(template_name):  # pragma: no branch
            yield Origin(template_name, template_name, loader=self)

    def get_contents(self, origin):
        return ""
