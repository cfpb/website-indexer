import multiprocessing
import re
from dataclasses import dataclass, field
from datetime import datetime
from os import environ
from typing import List
from urllib import parse

from django.utils import timezone

import lxml.etree
import lxml.html.soupparser

HTML_COMPONENT_SEARCH = re.compile(r"(?:(?:class=\")|\s)((?:o|m|a)-[\w\-]*)")
HTML_EXTERNAL_SITE = re.compile("/external-site/")
HTML_WHITESPACE = re.compile(r"\s+")


@dataclass
class ParsedHTML:
    html: str
    title: str | None
    language: str | None
    text: str | None
    timestamp: datetime = field(default_factory=timezone.now)
    links: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)


def parse_html(html, internal_link_host):
    # Parse HTML using lxml in a child process to avoid memory leaks.
    #
    # See https://www.reddit.com/r/Python/comments/j0gl8t/psa_pythonlxml_memory_leaks_and_a_solution/
    #
    # This doesn't work reliably when testing using pytest, so when
    # testing just call lxml directly since we don't care as much
    # about long-running memory usage.
    parser = (
        _parse_html
        if ("PYTEST_CURRENT_TEST" in environ)
        else _parse_html_multiprocessing
    )
    return parser(html, internal_link_host)


def _parse_html_multiprocessing(html, internal_link_host):  # pragma: no cover
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_parse_html_multiprocessing_process,
        args=(html, internal_link_host, queue),
    )
    process.daemon = True
    process.start()

    parsed_html = queue.get(timeout=5)
    process.terminate()

    return parsed_html


def _parse_html_multiprocessing_process(
    html, internal_link_host, queue
):  # pragma: no cover
    parsed_html = _parse_html(html, internal_link_host)
    queue.put(parsed_html)


def _parse_html(html, internal_link_host):
    tree = _parse_html_into_tree(html)

    title_tag = tree.find(".//title")
    title = title_tag.text.strip() if title_tag is not None else None
    language = tree.find(".").get("lang")

    if title is None:
        return None

    body = _get_cleaned_body_from_tree(tree)

    if body is not None:
        text = HTML_WHITESPACE.sub(" ", body.text_content()).strip()
    else:
        text = None

    parsed_html = ParsedHTML(title=title, language=language, html=html, text=text)

    if body is None:
        return parsed_html

    hrefs = list(
        set(
            href
            for element, attribute, href, pos in body.iterlinks()
            if "a" == element.tag and "href" == attribute
        )
    )

    # Remove any external link URL wrapping.
    for i, href in enumerate(hrefs):
        try:
            parsed_href = parse.urlparse(href)
        except ValueError:
            continue

        if not HTML_EXTERNAL_SITE.match(parsed_href.path):
            continue

        if parsed_href.netloc and internal_link_host != parsed_href.netloc:
            continue

        ext_url = parse.parse_qs(parsed_href.query).get("ext_url")
        if ext_url:
            hrefs[i] = ext_url[0]

    parsed_html.links = sorted(hrefs)

    body_html = lxml.etree.tostring(body, encoding="unicode")

    class_names = set(HTML_COMPONENT_SEARCH.findall(body_html))
    parsed_html.components = sorted(class_names)

    return parsed_html


def _parse_html_into_tree(html):
    try:
        return lxml.html.fromstring(html)
    except lxml.etree.ParserError:
        # https://bugs.launchpad.net/lxml/+bug/1949271
        return lxml.html.soupparser.fromstring(html)


def _get_cleaned_body_from_tree(tree):
    """Extract page body without header, footer, images, or scripts."""
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
