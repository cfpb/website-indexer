from django import template

from humanize import precisedelta as humanize_precisedelta


register = template.Library()


@register.filter
def precisedelta(timedelta):
    return humanize_precisedelta(timedelta)
