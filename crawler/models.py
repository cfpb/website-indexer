import dataclasses
import lxml.etree
import lxml.html.soupparser
import re
from urllib import parse

from django.db import models
from django.utils import timezone

from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalManyToManyField


@dataclasses.dataclass
class CrawlConfig:
    start_url: str
    max_pages: int = 0
    depth: int = 0


class Crawl(models.Model):
    class Status(models.TextChoices):
        STARTED = "Started"
        FINISHED = "Finished"
        FAILED = "Failed"

    started = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=64, default=Status.STARTED)
    config = models.JSONField()
    failure_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-started"]

    def __str__(self):
        s = f"Crawl {self.pk} ({self.status}) started {self.started}, config {self.config}"

        if self.failure_message:
            s += f", failure message: {self.failure_message}"

        return s

    @classmethod
    def start(cls, config: CrawlConfig):
        return cls.objects.create(config=dataclasses.asdict(config))

    def finish(self):
        self.status = self.Status.FINISHED
        self.save()

    def fail(self, failure_message):
        self.status = self.Status.FAILED
        self.failure_message = failure_message
        self.save()


class LatestCrawlManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()

        latest_crawl = Crawl.objects.filter(status=Crawl.Status.FINISHED).first()

        if latest_crawl is None:
            return qs.none()

        return qs.filter(crawl=latest_crawl)


class Request(models.Model):
    crawl = models.ForeignKey(
        Crawl, on_delete=models.CASCADE, related_name="%(class)ss"
    )
    timestamp = models.DateTimeField(db_index=True)
    url = models.TextField(db_index=True)

    class Meta:
        abstract = True
        ordering = ["url"]
        constraints = [
            models.UniqueConstraint("crawl", "url", name="%(class)s_crawl_url_key")
        ]

    objects = LatestCrawlManager()


class Component(models.Model):
    class_name = models.TextField(unique=True)

    class Meta:
        ordering = ["class_name"]


class Link(models.Model):
    href = models.TextField(unique=True)

    class Meta:
        ordering = ["href"]


class Page(Request, ClusterableModel):
    title = models.TextField()
    language = models.TextField(null=True, blank=True)
    html = models.TextField()
    text = models.TextField()
    components = ParentalManyToManyField(Component, related_name="pages")
    links = ParentalManyToManyField(Link, related_name="links")

    class Meta(Request.Meta):
        ordering = Request.Meta.ordering
        indexes = [
            models.Index("crawl", "title", name="page_crawl_title_idx"),
            models.Index("crawl", "language", name="page_crawl_language_idx"),
        ]

    def __str__(self):
        return self.url

    HTML_COMPONENT_SEARCH = re.compile(r"(?:(?:class=\")|\s)((?:o|m|a)-[\w\-]*)")
    HTML_EXTERNAL_SITE = re.compile("/external-site/")
    HTML_WHITESPACE = re.compile(r"\s+")

    @classmethod
    def from_html(
        cls,
        url,
        html,
        internal_link_host,
    ):
        try:
            tree = lxml.html.fromstring(html)
        except lxml.etree.ParserError:
            # https://bugs.launchpad.net/lxml/+bug/1949271
            tree = lxml.html.soupparser.fromstring(html)

        title_tag = tree.find(".//title")
        title = title_tag.text.strip() if title_tag is not None else None
        language = tree.find(".").get("lang")

        if title is None:
            return

        body = cls._get_cleaned_body_from_tree(tree)

        if body is not None:
            text = cls.HTML_WHITESPACE.sub(" ", body.text_content()).strip()
        else:
            text = None

        page = Page(
            timestamp=timezone.now(),
            url=url,
            title=title,
            language=language,
            html=html,
            text=text,
        )

        if body is None:
            return page

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
            if not cls.HTML_EXTERNAL_SITE.match(parsed_href.path):
                continue

            if parsed_href.netloc and internal_link_host != parsed_href.netloc:
                continue

            ext_url = parse.parse_qs(parsed_href.query).get("ext_url")
            if ext_url:
                hrefs[i] = ext_url[0]

        page.links = [Link(href=href) for href in sorted(hrefs)]

        body_html = lxml.etree.tostring(body, encoding="unicode")

        class_names = set(cls.HTML_COMPONENT_SEARCH.findall(body_html))
        page.components = [
            Component(class_name=class_name) for class_name in sorted(class_names)
        ]

        return page

    @staticmethod
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


class ErrorBase(Request):
    status_code = models.PositiveIntegerField()
    referrer = models.TextField(null=True, blank=True)

    class Meta(Request.Meta):
        abstract = True

    def __str__(self):
        s = self.url

        if self.referrer:
            s += f" (from {self.referrer})"

        s += f" {self.status_code}"

        return s


class Error(ErrorBase):
    def __str__(self):
        return super().__str__() + " !"


class Redirect(ErrorBase):
    location = models.TextField()

    def __str__(self):
        return super().__str__() + f" -> {self.location}"

    @property
    def is_http_to_https(self):
        return self.location == re.sub(r"^http://", "https://", self.url)

    @property
    def is_append_slash(self):
        return not self.url.endswith("/") and self.location == self.url + "/"
