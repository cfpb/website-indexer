#!/usr/bin/env python
import csv
import os.path
import re
from dataclasses import asdict, astuple, dataclass, fields

import click
import lxml.html
from sqlite_utils.db import Database
from warcio.archiveiterator import ArchiveIterator


WHITESPACE = re.compile(r"\s+")


COMPONENT_SEARCH = re.compile(r"(?:(?:class=\")|\s)((?:o|m|a)-[\w\-]*)")


@dataclass
class RequestRecord:
    timestamp: str
    url: str

    indexes = ["timestamp", "url"]


@dataclass
class PageRecord(RequestRecord):
    id: int
    title: str
    language: str

    table_name = "pages"
    pk = "id"
    indexes = RequestRecord.indexes + ["title", "language"]


@dataclass
class PageWithContentRecord(PageRecord):
    html: str
    text: str
    indexes = PageRecord.indexes + ["html", "text"]


@dataclass
class ErrorRecord(RequestRecord):
    status_code: int

    table_name = "errors"
    indexes = RequestRecord.indexes + ["status_code"]


@dataclass
class RedirectRecord(ErrorRecord):
    location: str

    table_name = "redirects"
    indexes = ErrorRecord.indexes + ["location"]


@dataclass
class PageElementRecord:
    page_id: int

    indexes = ["page_id"]


@dataclass
class LinkRecord(PageElementRecord):
    href: str

    table_name = "links"
    indexes = PageElementRecord.indexes + ["href"]


@dataclass
class ComponentRecord(PageElementRecord):
    class_name: str

    table_name = "components"
    indexes = PageElementRecord.indexes + ["class_name"]


def read_warc_records(warc, silent=False):
    iterator = ArchiveIterator(warc)
    progress_bar = None
    progress_last = 0

    if not silent:
        file_size = os.path.getsize(warc.name)
        progress_bar = click.progressbar(length=file_size)

    for warc_record in iterator:
        if warc_record.rec_type == "response":
            yield warc_record

        if progress_bar:
            progress_current = iterator.fh.tell()
            progress_step = progress_current - progress_last
            progress_bar.update(progress_step)
            progress_last = progress_current


SEEN_URLS = set()


def generate_records_from_warc_record(warc_record, page_id, include_page_content=False):
    url = warc_record.rec_headers.get_header("WARC-Target-URI")

    # This code is needed because, surprisingly, WARCs may contain multiple
    # records pointing to the same URL. This can happen if multiple redirects
    # or relative links point to the same target URL. We only want to generate
    # records for each URL a single time, so we keep a record of which ones
    # we've already seen.
    #
    # TODO: Encapsulate this behavior in a class to avoid the use of a module
    # top-level SEEN_URLS variable and allow for proper testing.
    if url in SEEN_URLS:
        return

    SEEN_URLS.add(url)

    status_code = int(warc_record.http_headers.get_statuscode())
    content_type = warc_record.http_headers.get_header("Content-Type")
    timestamp = warc_record.rec_headers.get_header("WARC-Date")

    if 300 <= status_code < 400:
        location = warc_record.http_headers.get("Location")
        yield RedirectRecord(timestamp, url, status_code, location)
        return

    if 400 <= status_code:
        yield ErrorRecord(timestamp, url, status_code)
        return

    if 200 != status_code:
        raise ValueError(f"Unexpected status code {status_code} for {url}")

    if not content_type:
        raise ValueError(f"Missing content type for {url}")

    if not content_type.startswith("text/html"):
        return

    html = warc_record.content_stream().read().decode("utf-8")
    tree = lxml.html.fromstring(html)

    title = tree.find(".//title").text
    language = tree.find(".").get("lang")

    body = tree.find("./body")

    drop_element_selectors = [".o-header", ".o-footer", "img", "script", "style"]

    for drop_element_selector in drop_element_selectors:
        for element in body.cssselect(drop_element_selector):
            element.drop_tree()

    if not include_page_content:
        yield PageRecord(timestamp, url, page_id, title, language)
    else:
        text = WHITESPACE.sub(" ", body.text_content()).strip()

        yield PageWithContentRecord(
            timestamp, url, page_id, title, language, html, text
        )

    hrefs = set(
        href
        for element, attribute, href, pos in body.iterlinks()
        if "a" == element.tag and "href" == attribute
    )

    for href in sorted(hrefs):
        yield LinkRecord(page_id, href)

    body_html = lxml.etree.tostring(body, encoding="unicode")

    components = set(COMPONENT_SEARCH.findall(body_html))
    for class_name in sorted(components):
        yield ComponentRecord(page_id, class_name)


def generate_records(warc, max_pages=None, silent=False, include_page_content=False):
    page_id = 0

    for warc_record in read_warc_records(warc, silent=silent):
        for record in generate_records_from_warc_record(
            warc_record, page_id, include_page_content
        ):
            yield record

            if isinstance(record, PageRecord):
                page_id += 1

        if max_pages and page_id >= max_pages:
            break


class BufferingTableWriter:
    def __init__(self, db):
        self.db = db

        self.table_name = None
        self.table = None
        self.columns = None
        self.pk = None
        self.indexes = None

        self.records = list()
        self.chunk_size = 100

    def insert(self, record):
        if not self.table_name:
            self.table_name = record.table_name
            self.table = self.db[self.table_name]
            self.pk = getattr(record, "pk", None)
            self.indexes = getattr(record, "indexes", [])

            self.columns = {field.name: str for field in fields(record)}

        self.records.append(record)

        if len(self.records) >= self.chunk_size:
            self._do_insert()

    def flush(self):
        if self.records:
            self._do_insert()

    def _do_insert(self):
        self.table.insert_all(
            map(asdict, self.records), columns=self.columns, pk=self.pk
        )

        self.records.clear()

    def create_indexes(self):
        for index in self.indexes or []:
            click.echo(f"Creating index {index} on table {self.table_name}")
            self.table.create_index([index], analyze=True)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("warc", type=click.File("rb"))
@click.option(
    "--pages-csv", type=click.File("w"), default="pages.csv", show_default=True
)
@click.option(
    "--errors-csv", type=click.File("w"), default="errors.csv", show_default=True
)
@click.option(
    "--redirects-csv", type=click.File("w"), default="redirects.csv", show_default=True
)
@click.option(
    "--links-csv", type=click.File("w"), default="links.csv", show_default=True
)
@click.option(
    "--components-csv",
    type=click.File("w"),
    default="components.csv",
    show_default=True,
)
def dump_csvs(
    warc,
    pages_csv,
    errors_csv,
    redirects_csv,
    links_csv,
    components_csv,
):
    """Generate CSVs from a WARC archive"""
    writers = {
        record_type: csv.writer(record_csv, csv.QUOTE_ALL)
        for record_type, record_csv in {
            PageRecord: pages_csv,
            ErrorRecord: errors_csv,
            RedirectRecord: redirects_csv,
            LinkRecord: links_csv,
            ComponentRecord: components_csv,
        }.items()
    }

    for record in generate_records(warc):
        writers[record.__class__].writerow(astuple(record))


@cli.command()
@click.argument("warc", type=click.File("rb"))
@click.argument("db_filename", type=click.Path())
@click.option(
    "--max-pages", type=int, help="Maximum number of pages to read from the archive"
)
@click.option(
    "--recreate",
    is_flag=True,
    show_default=True,
    default=False,
    help="Recreate database file if it already exists",
)
def create_db(warc, db_filename, max_pages, recreate):
    """Create a SQLite database from a WARC archive"""
    if os.path.exists(db_filename) and not recreate:
        click.confirm(
            f"File {db_filename} already exists, do you wish to recreate?", abort=True
        )

    db = Database(db_filename, recreate=True)

    record_types = [
        PageWithContentRecord,
        ErrorRecord,
        RedirectRecord,
        LinkRecord,
        ComponentRecord,
    ]

    writers = {record_type: BufferingTableWriter(db) for record_type in record_types}

    for record in generate_records(
        warc, max_pages=max_pages, include_page_content=True
    ):
        writers[record.__class__].insert(record)

    for writer in writers.values():
        writer.flush()

    click.echo()

    for writer in writers.values():
        writer.create_indexes()


if __name__ == "__main__":
    cli()
