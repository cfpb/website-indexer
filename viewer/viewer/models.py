from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.http import urlencode


# The models in this file were initially generated from an existing SQLite
# database with "manage.py inspectdb".


class Page(models.Model):
    path = models.TextField(primary_key=True)
    title = models.TextField()
    components = models.JSONField()
    links = models.JSONField()
    hash = models.TextField(db_column="pageHash")
    html = models.TextField(db_column="pageHtml")
    timestamp = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "cfgov"
        ordering = ["path"]

    def get_absolute_url(self):
        return reverse("page") + "?" + urlencode({"path": self.path})

    def get_trimmed_page_title(self):
        return self.title.replace(" | Consumer Financial Protection Bureau", "")

    @property
    def absolute_path(self):
        return f"{settings.BASE_CRAWL_URL}{self.path}"


class PageHTML(models.Model):
    path = models.OneToOneField(
        primary_key=True,
        serialize=False,
        to="viewer.page",
        on_delete=models.CASCADE,
        db_column="path",
        related_name="html_fts",
    )
    html = models.TextField(db_column="pageHtml")

    class Meta:
        managed = False
        db_table = "cfgov_fts"
