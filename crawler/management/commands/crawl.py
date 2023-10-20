import os
import os.path
import re
from email.utils import parsedate_to_datetime
from urllib import parse

from django.core.management import call_command
from django.db import connections

import djclick as click
import lxml.html
from wpull.application.builder import Builder
from wpull.application.hook import Actions
from wpull.application.options import AppArgumentParser
from wpull.application.plugin import PluginFunctions, WpullPlugin, hook
from wpull.pipeline.item import URLProperties
from wpull.url import URLInfo

from crawler.models import Component, Error, Link, Page, Redirect
from crawler.writer import DatabaseWriter


COMPONENT_SEARCH = re.compile(r"(?:(?:class=\")|\s)((?:o|m|a)-[\w\-]*)")
EXTERNAL_SITE = re.compile("/external-site/")
WHITESPACE = re.compile(r"\s+")


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
        self.num_pages = 0

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
        return self.max_pages and self.num_pages >= self.max_pages

    @hook(PluginFunctions.accept_url)
    def accept_url(self, item_session, verdict, reasons):
        if self.at_max_pages:
            return False

        request = item_session.url_record

        # We want to crawl links to different domains to test their validity.
        # But once we've done that, we don't want to keep crawling there.
        # Therefore, don't crawl links that start on different domains.
        if (
            request.parent_url_info.hostname_with_port
            != self.start_url.hostname_with_port
        ):
            return False

        # If we're crawling on the start domain, apply additional rejections.
        if request.url_info.hostname_with_port == self.start_url.hostname_with_port:
            # Don't crawl URLs that look like filenames.
            if "." in request.url_info.path:
                return False

            qs = parse.parse_qs(request.url_info.query)

            if qs:
                # Don't crawl external link URLs directly.
                # Instead crawl to their ultimate destination.
                if EXTERNAL_SITE.match(request.url_info.path):
                    ext_url = qs.get("ext_url")
                    if ext_url:
                        # Add the external URL to the list to be crawled.
                        url_properties = URLProperties()
                        url_properties.level = request.level
                        url_properties.inline_level = request.inline_level
                        url_properties.parent_url = request.parent_url
                        url_properties.root_url = request.root_url

                        item_session.add_url(ext_url[0], url_properites=url_properties)
                        return False

                # For all other URLs, limit querystrings that get crawled.
                # Only crawl pages that only have the "page" parameter.
                elif list(qs.keys()) != ["page"]:
                    return False

        return verdict

    @hook(PluginFunctions.handle_response)
    def my_handle_response(self, item_session):
        self.num_pages += 1
        if self.at_max_pages:
            item_session.skip()
            return Actions.FINISH

        db_record = self.process_response(item_session.request, item_session.response)

        if db_record:
            self.db_writer.write(db_record)

        return Actions.NORMAL

    def process_response(self, request, response):
        status_code = response.status_code
        content_type = response.fields["Content-Type"]
        timestamp = parsedate_to_datetime(response.fields["Date"])
        referrer = request.fields.get("Referer")

        if status_code >= 300:
            if status_code < 400:
                location = response.fields.get("Location")
                return Redirect(
                    timestamp=timestamp,
                    url=request.url,
                    status_code=status_code,
                    referrer=referrer,
                    location=location,
                )
            else:
                return Error(
                    timestamp=timestamp,
                    url=request.url,
                    status_code=status_code,
                    referrer=referrer,
                )

        if 200 != status_code:
            raise ValueError(f"Unexpected status code {status_code} for {request.url}")

        if not content_type:
            raise ValueError(f"Missing content type for {request.url}")

        if not content_type.startswith("text/html"):
            return

        # We don't record external page data because we've only crawled them to
        # check for redirects, 404s, or other errors.
        if request.url_info.hostname_with_port != self.start_url.hostname_with_port:
            return

        html = response.body.content().decode("utf-8")
        tree = lxml.html.fromstring(html)
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
            "--recursive",
            "--no-verbose",
            "--delete-after",
            "--no-robots",
            "--wait=0.5",
            "--random-wait",
            "--span-hosts",
            "--user-agent=CFPB website indexer",
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

    return app.run_sync()
