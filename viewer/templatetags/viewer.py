from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.defaultfilters import date, pluralize
from django.templatetags.tz import localtime


register = template.Library()


@register.filter
def format_datetime(dt):
    return date(localtime(dt), "N j, Y, g:i a T")


@register.simple_tag(takes_context=True)
def results_summary(context, truncate_q_at=24):
    request = context["request"]
    count = context["count"]

    q = request.GET.get("q")
    search_type = request.GET.get("search_type")

    if not q or not search_type:
        if not count:
            return "There are no indexed pages"
        else:
            return f"Showing all {intcomma(count)} indexed page{pluralize(count)}"

    search_name = {
        "title": "the page title",
        "url": "the page URL",
        "components": "components",
        "links": "link URLs",
        "text": "full text",
        "html": "page HTML",
    }[search_type]

    count_str = intcomma(count) if count else "No"
    truncated_q = f"{q[:truncate_q_at]}..." if len(q) > truncate_q_at else q

    return f'{count_str} page{pluralize(count)} with "{truncated_q}" in {search_name}'
