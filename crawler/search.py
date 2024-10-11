from urllib.parse import quote_plus

from django.db.models import Q

from crawler.models import Page


_page_values = ["timestamp", "url", "title", "language"]


def search_components(class_name_contains, include_class_names=False):
    queryset = Page.objects.prefetch_related("components").filter(
        components__class_name__icontains=class_name_contains
    )

    values = _page_values

    if include_class_names:
        values = values + ["components__class_name"]
    else:
        queryset = queryset.distinct()

    return queryset.values(*values)


def search_links(href_contains, include_hrefs=False, or_urlencoded=True):
    queryset = Page.objects.prefetch_related("links")

    href_filter = Q(links__href__icontains=href_contains)

    if or_urlencoded:  # pragma: no branch
        href_filter |= Q(links__href__icontains=quote_plus(href_contains))

    queryset = queryset.filter(href_filter)

    values = _page_values

    if include_hrefs:
        values = values + ["links__href"]
    else:
        queryset = queryset.distinct()

    return queryset.values(*values)


def _search_pages(**filter_kwargs):
    return Page.objects.filter(**filter_kwargs).values(*_page_values)


def search_empty():
    return _search_pages()


def search_html(html_contains):
    return _search_pages(html__icontains=html_contains)


def search_text(text_contains):
    return _search_pages(text__icontains=text_contains)


def search_title(title_contains):
    return _search_pages(title__icontains=title_contains)


def search_url(url_contains):
    return _search_pages(url__icontains=url_contains)
