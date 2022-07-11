from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.http import urlencode


# WARNING: Do not alter the model definitions in this file without making
# comparable changes to the schema in db.js.


class Component(models.Model):
    name = models.TextField(unique=True, db_index=True)

    class Meta:
        managed = False
        db_table = "components"
        ordering = ["name"]


class Link(models.Model):
    url = models.TextField(unique=True, db_index=True)

    class Meta:
        managed = False
        db_table = "links"


class Page(models.Model):
    crawled_at = models.DateTimeField(db_index=True)
    path = models.TextField(unique=True, db_index=True)
    html = models.TextField(db_index=True)
    title = models.TextField(db_index=True)
    hash = models.TextField()
    components = models.ManyToManyField(Component, related_name="pages")
    links = models.ManyToManyField(Link, related_name="pages")

    class Meta:
        managed = False
        db_table = "pages"
        ordering = ["path"]

    def get_absolute_url(self):
        return reverse("page") + "?" + urlencode({"path": self.path})

    def get_trimmed_page_title(self):
        return self.title.replace(" | Consumer Financial Protection Bureau", "")

    @property
    def absolute_path(self):
        return f"{settings.BASE_CRAWL_URL}{self.path}"
