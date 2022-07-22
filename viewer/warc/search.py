from warc.models import Page


_page_values = ["timestamp", "url", "title", "language"]


def search_components(class_name_contains, include_class_names=False):
    values = _page_values

    if include_class_names:
        values = values + ["components__class_name"]

    return (
        Page.objects.prefetch_related("components")
        .filter(components__class_name__contains=class_name_contains)
        .values(*values)
    )


def search_links(href_contains, include_hrefs=False):
    values = _page_values

    if include_hrefs:
        values = values + ["links__href"]

    return (
        Page.objects.prefetch_related("links")
        .filter(links__href__contains=href_contains)
        .values(*values)
    )


def _search_pages(**filter_kwargs):
    return Page.objects.filter(**filter_kwargs).values(*_page_values)


def search_html(html_contains):
    return _search_pages(html__contains=html_contains)


def search_text(text_contains):
    return _search_pages(text__contains=text_contains)


def search_title(title_contains):
    return _search_pages(title__contains=title_contains)


def search_url(url_contains):
    return _search_pages(url__contains=url_contains)
