import asyncio
import logging
import os
import os.path
import re
from urllib import parse

from django.core.management import call_command
from django.db import connections
from django.utils import timezone

import djclick as click
import lxml.html.soupparser
from wpull.application.builder import Builder
from wpull.application.hook import Actions
from wpull.application.options import AppArgumentParser
from wpull.application.plugin import PluginFunctions, WpullPlugin, hook
from wpull.network.connection import BaseConnection
from wpull.pipeline.item import URLProperties
from wpull.url import URLInfo

from crawler.models import Component, Error, Link, Page, Redirect
from crawler.writer import DatabaseWriter


logger = logging.getLogger("crawler")


COMPONENT_SEARCH = re.compile(r"(?:(?:class=\")|\s)((?:o|m|a)-[\w\-]*)")
EXTERNAL_SITE = re.compile("/external-site/")
WHITESPACE = re.compile(r"\s+")

SKIP_URLS = list(
    map(
        re.compile,
        [
            r"^https://www.facebook.com/dialog/share\?.*",
            r"^https://twitter.com/intent/tweet\?.*",
            r"^https://www.linkedin.com/shareArticle\?.*",
        ],
    )
)


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


class DatabaseWritingPlugin(WpullPlugin):
    def activate(self):
        super().activate()

        self.start_url = URLInfo.parse(self.app_session.args.urls[0])
        self.db_filename, self.max_pages = self.app_session.args.plugin_args.rsplit(
            ",", maxsplit=1
        )
        self.max_pages = int(self.max_pages)

        self.init_db()
        self.accepted_urls = []
        self.requested_urls = []

    def init_db(self):
        db_alias = "warc_to_db"

        connections.databases[db_alias] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": self.db_filename,
        }

        call_command("migrate", database=db_alias, app_label="crawler", run_syncdb=True)

        self.db_writer = DatabaseWriter(db_alias)

    @property
    def at_max_pages(self):
        return self.max_pages and len(self.retrieved_urls) >= self.max_pages

    @hook(PluginFunctions.accept_url)
    def accept_url(self, item_session, verdict, reasons):
        # If upstream logic rejected this URL, let the rejection stand.
        if not verdict:
            return False

        # If we've already crawled enough pages, stop.
        if self.at_max_pages:
            return False

        request = item_session.url_record

        # Don't request pages more than once.
        if request.url in self.requested_urls:
            return False

        # Always skip certain URLs.
        if SKIP_URLS and any(skip_url.match(request.url) for skip_url in SKIP_URLS):
            return False

        # We want to crawl links to different domains to test their validity.
        # But once we've done that, we don't want to keep crawling there.
        # Therefore, don't crawl links that start on different domains.
        if (
            request.parent_url_info.hostname_with_port
            != self.start_url.hostname_with_port
        ):
            return False

        # If we're crawling on a different domain, use a HEAD request to avoid
        # downloading files that might be linked, for example from S3.
        if request.url_info.hostname_with_port != self.start_url.hostname_with_port:
            if "." in request.url_info.path:
                item_session.request.method = "HEAD"

        # If we're crawling on the start domain, apply additional rejections.
        else:
            # Don't crawl URLs that look like filenames.
            if "." in request.url_info.path:
                return False

            qs = parse.parse_qs(request.url_info.query)

            if qs:
                # Don't crawl external link URLs directly.
                # Instead crawl to their ultimate destination.
                if EXTERNAL_SITE.match(request.url_info.path):
                    ext_urls = qs.get("ext_url")
                    if ext_urls:
                        # Add the external URL to the list to be crawled.
                        ext_url = ext_urls[0]

                        url_properties = URLProperties()
                        url_properties.level = request.level
                        url_properties.inline_level = request.inline_level
                        url_properties.parent_url = request.parent_url
                        url_properties.root_url = request.root_url

                        item_session.app_session.factory["URLTable"].remove_many(
                            [ext_url]
                        )
                        item_session.add_url(ext_url, url_properites=url_properties)
                        return False

                # For all other URLs, limit querystrings that get crawled.
                # Only crawl pages that only have the "page" parameter.
                elif list(qs.keys()) != ["page"]:
                    return False

        if request.url not in self.accepted_urls:
            logger.info(f"Crawling {request.url}")
            self.accepted_urls.append(request.url)

        return True

    @hook(PluginFunctions.handle_error)
    def handle_error(self, item_session, error):
        if item_session.request.url in self.requested_urls:
            logger.debug(f"Already logged error for {item_session.request.url}")
        else:
            self.db_writer.write(
                Error(
                    timestamp=timezone.now(),
                    url=item_session.request.url,
                    status_code=0,
                    referrer=item_session.request.fields.get("Referer"),
                )
            )

            self.requested_urls.append(item_session.request.url)

    @hook(PluginFunctions.handle_pre_response)
    def handle_pre_response(self, item_session):
        # Our accept_url handler converts external requests from GET to HEAD.
        # The wpull response body handler seems to assume that HEAD request
        # responses will never have Content-Length or Transfer-Encoding
        # headers, which doesn't seem to be the case in practice:
        #
        # https://github.com/ArchiveTeam/wpull/blob/v2.0.1/wpull/protocol/http/stream.py#L441-L451
        #
        # Therefore, we strip these headers out if they exist, since we don't
        # need them for our purposes. Since this was an external request, we
        # care only about the status code, not the response body.
        if item_session.request.method == "HEAD":
            item_session.response.fields.pop("Content-Length", None)
            item_session.response.fields.pop("Transfer-Encoding", None)

        return Actions.NORMAL

    @hook(PluginFunctions.handle_response)
    def handle_response(self, item_session):
        request = item_session.request
        response = item_session.response
        status_code = response.status_code
        timestamp = timezone.now()

        if request.url in self.requested_urls:
            logger.debug(f"Already logged {request.url}")
            item_session.skip()
            return Actions.FINISH
        else:
            self.requested_urls.append(request.url)

        if status_code >= 300:
            referrer = request.fields.get("Referer")

            if status_code < 400:
                location = response.fields.get("Location")
                location_parsed = parse.urlparse(location)

                self.db_writer.write(
                    Redirect(
                        timestamp=timestamp,
                        url=request.url,
                        status_code=status_code,
                        referrer=referrer,
                        location=location,
                    )
                )

                # Don't follow redirects that don't point to the start domain.
                if (
                    location_parsed.hostname
                    and location_parsed.hostname != self.start_url.hostname
                ) or (
                    location_parsed.port and location_parsed.port != self.start_url.port
                ):
                    logger.debug(f"Not following redirect to {location}")
                    item_session.skip()
                    return Actions.FINISH
            else:
                self.db_writer.write(
                    Error(
                        timestamp=timestamp,
                        url=request.url,
                        status_code=status_code,
                        referrer=referrer,
                    )
                )

            return Actions.NORMAL

        # If this request was to an external domain and it responded with
        # a normal status code, we don't care about recording it.
        if request.url_info.hostname_with_port != self.start_url.hostname_with_port:
            item_session.skip()
            return Actions.FINISH

        page_record = self.process_200_response(request, response)

        if page_record:
            self.db_writer.write(page_record)

        return Actions.NORMAL

    def process_200_response(self, request, response):
        timestamp = timezone.now()

        content_type = response.fields.get("Content-Type")

        if not content_type:
            raise ValueError(f"Missing content type for {request.url}")

        if not content_type.startswith("text/html"):
            return

        html = response.body.content().decode("utf-8")

        tree = lxml.html.soupparser.fromstring(html)
        title_tag = tree.find(".//title")
        title = title_tag.text.strip() if title_tag is not None else None
        language = tree.find(".").get("lang")

        if title is None:
            return

        body = get_body(tree)

        if body is not None:
            text = WHITESPACE.sub(" ", body.text_content()).strip()
        else:
            text = None

        page = Page(
            timestamp=timestamp,
            url=request.url,
            title=title,
            language=language,
            html=html,
            text=text,
        )

        hrefs = list(
            set(
                href
                for element, attribute, href, pos in body.iterlinks()
                if "a" == element.tag and "href" == attribute
            )
        )

        # Remove any external link URL wrapping.
        for i, href in enumerate(hrefs):
            parsed_href = parse.urlparse(href)
            if not EXTERNAL_SITE.match(parsed_href.path):
                continue

            if parsed_href.netloc and self.start_url.host != parsed_href.netloc:
                continue

            ext_url = parse.parse_qs(parsed_href.query).get("ext_url")
            if ext_url:
                hrefs[i] = ext_url[0]

        page.links = [Link(href=href) for href in sorted(hrefs)]

        body_html = lxml.etree.tostring(body, encoding="unicode")

        class_names = set(COMPONENT_SEARCH.findall(body_html))
        page.components = [
            Component(class_name=class_name) for class_name in sorted(class_names)
        ]

        return page


def patch_wpull_connection():
    @asyncio.coroutine
    def readline(self):
        data = yield from self.run_network_operation(
            self.reader.readline(), wait_timeout=self._timeout, name="Readline"
        )
        return data

    BaseConnection.readline = readline


@click.command()
@click.argument("start_url")
@click.argument("db_filename", type=click.Path())
@click.option(
    "--max-pages", type=int, help="Maximum number of pages to crawl", default=0
)
@click.option("--depth", type=int, help="Maximum crawl depth", default=0)
@click.option(
    "--recreate",
    is_flag=True,
    show_default=True,
    default=False,
    help="Recreate database file if it already exists",
)
def command(start_url, db_filename, max_pages, depth, recreate):
    if os.path.exists(db_filename):
        if not recreate:
            raise click.ClickException(
                f"File {db_filename} already exists, use --recreate to recreate."
            )

        os.remove(db_filename)

    arg_parser = AppArgumentParser()
    args = arg_parser.parse_args(
        [
            start_url,
            "--quiet",
            "--recursive",
            "--delete-after",
            "--no-robots",
            "--wait=0.5",
            "--random-wait",
            "--dns-timeout=5",
            "--connect-timeout=5",
            "--read-timeout=30",
            "--session-timeout=30",
            "--span-hosts",
            "--link-extractors=html",
            "--follow-tags=a",
            "--user-agent=CFPB website indexer",
            "--no-check-certificate",
            f"--level={depth}",
            f"--plugin-script={__file__}",
            f"--plugin-args={db_filename},{max_pages}",
        ]
    )
    builder = Builder(args)
    app = builder.build()

    # This is required due to the use of async code in wpull. Unfortunately
    # wpull hooks aren't called in a way that allows us to wrap Django database
    # calls with sync_to_async. This is only safe because we only download one
    # URL at a time.
    # https://docs.djangoproject.com/en/3.2/topics/async/#async-safety
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

    patch_wpull_connection()
    return app.run_sync()
