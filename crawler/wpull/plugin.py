import logging
import re
from urllib import parse

from django.utils import timezone

from wpull.application.hook import Actions
from wpull.application.plugin import PluginFunctions, WpullPlugin, hook
from wpull.errors import ExitStatus
from wpull.network.connection import BaseConnection
from wpull.pipeline.item import URLProperties
from wpull.url import URLInfo

from crawler.models import Crawl, Error, Page, Redirect
from crawler.writer import DatabaseWriter


logger = logging.getLogger("crawler")


SKIP_URLS = list(
    map(
        re.compile,
        [
            r"^https://www.facebook.com/dialog/share\?.*",
            r"^https://twitter.com/intent/tweet\?.*",
            r"^https://x.com/intent/tweet\?.*",
            r"^https://www.linkedin.com/shareArticle\?.*",
        ],
    )
)

HEAD_URLS = list(map(re.compile, [r"https://files.consumerfinance.gov/.*"]))


def patch_wpull_connection():
    """Use wait_timeout instead of close_timeout for readline."""

    async def readline(self):
        data = await self.run_network_operation(
            self.reader.readline(), wait_timeout=self._timeout, name="Readline"
        )
        return data

    BaseConnection.readline = readline


class DatabaseWritingPlugin(WpullPlugin):
    def activate(self):
        super().activate()

        patch_wpull_connection()

        self.start_url = URLInfo.parse(self.app_session.args.urls[0])

        crawl_record_id = int(self.app_session.args.plugin_args)
        crawl_record = Crawl.objects.get(pk=crawl_record_id)

        self.db_writer = DatabaseWriter(crawl_record)
        self.max_pages = crawl_record.config["max_pages"]

        self.accepted_urls = []
        self.requested_urls = []

    def deactivate(self):
        super().deactivate()
        self.db_writer.analyze()

    @property
    def at_max_pages(self):
        return self.max_pages and len(self.requested_urls) >= self.max_pages

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

        # Use HEAD requests to speed up the crawl for certain external domains.
        # We can't do this everywhere because other sites may respond to HEAD
        # requests in inconvenient ways. This avoids the need to fully download
        # external responses.
        if HEAD_URLS and any(head_url.match(request.url) for head_url in HEAD_URLS):
            item_session.request.method = "HEAD"

        # If we're crawling on the start domain, apply additional rejections.
        elif request.url_info.hostname_with_port == self.start_url.hostname_with_port:
            # Don't crawl URLs that look like filenames.
            if "." in request.url_info.path:
                return False

            qs = parse.parse_qs(request.url_info.query)

            if qs:
                # Don't crawl external link URLs directly.
                # Instead crawl to their ultimate destination.
                if Page.HTML_EXTERNAL_SITE.match(request.url_info.path):
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
            logger.debug(error)
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
        # Our accept_url handler converts certain external requests from GET to
        # HEAD. The wpull response body handler seems to assume that HEAD
        # request responses will never have Content-Length or Transfer-Encoding
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

        if not page_record:
            logger.debug(f"Unexpected response for {request.url}, skipping")
            item_session.skip()
            return Actions.FINISH

        self.db_writer.write(page_record)
        return Actions.NORMAL

    def process_200_response(self, request, response):
        content_type = response.fields.get("Content-Type")

        if not (content_type or "").startswith("text/html"):
            return

        html = response.body.content().decode("utf-8")
        return Page.from_html(request.url, html, self.start_url.hostname)

    @hook(PluginFunctions.exit_status)
    def exit_status(self, app_session, exit_code):
        # If a non-zero exit code exists because of some kind of network error
        # (DNS resolution, connection issue, etc.) we want to ignore it and
        # instead return a zero error code. We expect to encounter some of
        # these errors when we crawl, but we don't want the overall process to
        # fail downstream processing.
        #
        # See list of wpull exit status codes here:
        # https://github.com/ArchiveTeam/wpull/blob/v2.0.1/wpull/errors.py#L40-L63
        return (
            0
            if exit_code
            in (
                ExitStatus.network_failure,
                ExitStatus.ssl_verification_error,
                ExitStatus.authentication_failure,
                ExitStatus.protocol_error,
                ExitStatus.server_error,
            )
            else exit_code
        )
