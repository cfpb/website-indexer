import os.path
import re
from urllib.parse import urlparse, urlunparse

import click
import lxml.html
from warcio.archiveiterator import ArchiveIterator

from crawler.models import Component, Error, Link, Page, Redirect


WHITESPACE = re.compile(r"\s+")


COMPONENT_SEARCH = re.compile(r"(?:(?:class=\")|\s)((?:o|m|a)-[\w\-]*)")


def read_warc_records(warc, silent=False):
    iterator = ArchiveIterator(warc)
    progress_bar = None
    progress_last = 0
    warc_request = None

    if not silent:
        file_size = os.path.getsize(warc.name)
        progress_bar = click.progressbar(length=file_size)

    for warc_record in iterator:
        if warc_record.rec_type == "request":
            warc_request = warc_record
        else:
            if warc_record.rec_type == "response":
                yield warc_request, warc_record

            warc_request = None

        if progress_bar:
            progress_current = iterator.fh.tell()
            progress_step = progress_current - progress_last
            progress_bar.update(progress_step)
            progress_last = progress_current


def get_body(tree):
    body = tree.find("./body")

    if body is not None:
        drop_element_selectors = [
            ".o-header",
            ".o-footer",
            ".skip-nav",
            "img",
            "script",
            "style",
        ]

        for drop_element_selector in drop_element_selectors:
            for element in body.cssselect(drop_element_selector):
                element.drop_tree()

    return body


def make_instance_from_warc_record(
    warc_request, warc_response, seen_urls, limit_domain
):
    url = warc_response.rec_headers.get_header("WARC-Target-URI")

    # Skip non-HTTP responses (e.g. DNS lookups).
    if not warc_response.http_headers:
        return

    # This code is needed because, surprisingly, WARCs may contain multiple
    # records pointing to the same URL. This can happen if multiple redirects
    # or relative links point to the same target URL. We only want to generate
    # records for each URL a single time, so we keep a record of which ones
    # we've already seen.
    if url in seen_urls:
        return

    seen_urls.add(url)

    status_code = int(warc_response.http_headers.get_statuscode())
    content_type = warc_response.http_headers.get_header("Content-Type")
    timestamp = warc_response.rec_headers.get_header("WARC-Date")

    if warc_request:
        referrer = warc_request.http_headers.get_header("Referer")
    else:
        referrer = None

    if status_code >= 300:
        if status_code < 400:
            location = warc_response.http_headers.get("Location")
            return Redirect(
                timestamp=timestamp,
                url=url,
                status_code=status_code,
                referrer=referrer,
                location=location,
            )
        else:
            return Error(
                timestamp=timestamp, url=url, status_code=status_code, referrer=referrer
            )

        return

    if 200 != status_code:
        raise ValueError(f"Unexpected status code {status_code} for {url}")

    if not content_type:
        raise ValueError(f"Missing content type for {url}")

    if not content_type.startswith("text/html"):
        return

    if limit_domain and not url.startswith(limit_domain):
        return

    html = warc_response.content_stream().read().decode("utf-8")
    tree = lxml.html.fromstring(html)
    title_tag = tree.find(".//title")
    title = title_tag.text.strip() if title_tag is not None else None
    language = tree.find(".").get("lang")

    body = get_body(tree)

    if body is not None:
        text = WHITESPACE.sub(" ", body.text_content()).strip()
    else:
        text = None

    page = Page(
        timestamp=timestamp,
        url=url,
        title=title,
        language=language,
        html=html,
        text=text,
    )

    hrefs = set(
        href
        for element, attribute, href, pos in body.iterlinks()
        if "a" == element.tag and "href" == attribute
    )

    page.links = [Link(href=href) for href in sorted(hrefs)]

    body_html = lxml.etree.tostring(body, encoding="unicode")

    class_names = set(COMPONENT_SEARCH.findall(body_html))
    page.components = [
        Component(class_name=class_name) for class_name in sorted(class_names)
    ]

    return page


def generate_instances(warc, max_pages=None, single_domain_only=True, silent=False):
    page_count = 0
    seen_urls = set()
    limit_domain = None

    for warc_request, warc_response in read_warc_records(warc, silent=silent):
        instance = make_instance_from_warc_record(
            warc_request, warc_response, seen_urls, limit_domain
        )

        if not instance:
            continue

        yield instance

        if isinstance(instance, Page):
            page_count += 1

            if max_pages and page_count >= max_pages:
                break

            if single_domain_only and not limit_domain:
                parsed = urlparse(instance.url)
                limit_domain = urlunparse(
                    (parsed.scheme, parsed.netloc, "/", "", "", "")
                )
