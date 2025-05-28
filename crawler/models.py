import dataclasses
import re

from django.db import models

from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalManyToManyField

from crawler.parser import parse_html


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

    @classmethod
    def from_html(
        cls,
        url,
        html,
        internal_link_host,
    ):
        parsed_html = parse_html(html, internal_link_host)

        if parsed_html is None:
            return None

        return Page(
            timestamp=parsed_html.timestamp,
            url=url,
            title=parsed_html.title,
            language=parsed_html.language,
            html=parsed_html.html,
            text=parsed_html.text,
            links=[Link(href=href) for href in parsed_html.links],
            components=[
                Component(class_name=class_name)
                for class_name in parsed_html.components
            ],
        )


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
