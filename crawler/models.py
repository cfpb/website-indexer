import lxml.etree
import lxml.html.soupparser
import re
from urllib import parse

from django.db import models
from django.utils import timezone

from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalManyToManyField


class Request(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    url = models.TextField(unique=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ["url"]


class Component(models.Model):
    class_name = models.TextField(unique=True, db_index=True)

    class Meta:
        ordering = ["class_name"]


class Link(models.Model):
    href = models.TextField(unique=True, db_index=True)

    class Meta:
        ordering = ["href"]


class Page(Request, ClusterableModel):
    title = models.TextField(db_index=True)
    language = models.TextField(db_index=True, null=True, blank=True)
    html = models.TextField()
    text = models.TextField()
    components = ParentalManyToManyField(Component, related_name="pages")
    links = ParentalManyToManyField(Link, related_name="links")

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
    status_code = models.PositiveIntegerField(db_index=True)
    referrer = models.TextField(db_index=True, null=True, blank=True)

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
    location = models.TextField(db_index=True)

    def __str__(self):
        return super().__str__() + f" -> {self.location}"
