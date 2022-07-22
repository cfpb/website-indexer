import re

from django import template


register = template.Library()


PAGE_TITLE_SUFFIX_RE = re.compile(
    r" \| ("
    r"Consumer Financial Protection Bureau|"
    r"Oficina para la Protección Financiera del Consumidor"
    r")$"
)


@register.filter
def strip_title_suffix(title):
    return PAGE_TITLE_SUFFIX_RE.sub("", title)
