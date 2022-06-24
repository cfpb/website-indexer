#!/usr/bin/env python
import argparse
import csv
import re
import sys
from dataclasses import astuple, dataclass
from html import unescape

import click
import lxml.html
from warcio.archiveiterator import ArchiveIterator


TITLE_TAG = re.compile(r"<title>\s*(.*?)\s*</title>", re.IGNORECASE)


@dataclass
class PageRecord:
    url: str
    title: str
    language: str


@dataclass
class RedirectRecord:
    from_url: str
    to_url: str
    status_code: int


@dataclass
class ErrorRecord:
    url: str
    status_code: int


@dataclass
class LinkRecord:
    page_url: str
    link_href: str
    link_text: str
    xpath: str


def generate_warc_records(warc):
    for warc_record in ArchiveIterator(warc):
        if warc_record.rec_type == "response":
            yield warc_record


def generate_records_from_warc_record(warc_record):
    url = warc_record.rec_headers.get_header("WARC-Target-URI")
    status_code = int(warc_record.http_headers.get_statuscode())
    content_type = warc_record.http_headers.get_header("Content-Type")

    if 300 <= status_code < 400:
        redirect_location = warc_record.http_headers.get("Location")
        yield RedirectRecord(url, redirect_location, status_code)
        return

    if 400 <= status_code:
        yield ErrorRecord(url, status_code)
        return

    if 200 != status_code:
        raise ValueError(f"Unexpected status code {status_code} for {url}")

    if not content_type:
        raise ValueError(f"Missing content type for {url}")

    if not content_type.startswith("text/html;"):
        return

    html = warc_record.content_stream().read().decode("utf-8")
    tree = lxml.html.fromstring(html)
    root_tree = tree.getroottree()

    title = tree.find(".//title").text
    language = tree.find(".").get("lang")

    yield PageRecord(url, title, language)

    for element, attribute, link, pos in tree.iterlinks():
        if "a" != element.tag or "href" != attribute:
            continue

        link_text = element.text_content().strip()
        link_xpath = root_tree.getpath(element)

        yield LinkRecord(url, link, link_text, link_xpath)


@click.command()
@click.argument("warc", type=click.File("rb"))
@click.option(
    "--pages-csv",
    type=click.File("w"),
    default="pages.csv",
    show_default=True
)
@click.option(
    "--redirects-csv",
    type=click.File("w"),
    default="redirects.csv",
    show_default=True
)
@click.option(
    "--errors-csv",
    type=click.File("w"),
    default="errors.csv",
    show_default=True
)
@click.option(
    "--links-csv",
    type=click.File("w"),
    default="links.csv",
    show_default=True
)
def dump_csvs(
    warc,
    pages_csv,
    redirects_csv,
    errors_csv,
    links_csv
):
    """Generate CSVs from a WARC archive (*.warc, *.warc.gz)."""
    writers = {
        record_type: csv.writer(record_csv, csv.QUOTE_ALL)
        for record_type, record_csv in {
            PageRecord: pages_csv,
            RedirectRecord: redirects_csv,
            ErrorRecord: errors_csv,
            LinkRecord: links_csv,
        }.items()
    }

    for warc_record in generate_warc_records(warc):
        for record in generate_records_from_warc_record(warc_record):
            writers[record.__class__].writerow(astuple(record))


if __name__ == '__main__':
    dump_csvs()
