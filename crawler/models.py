from django.db import models

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


class ErrorBase(Request):
    status_code = models.PositiveIntegerField(db_index=True)
    referrer = models.TextField(db_index=True, null=True, blank=True)

    class Meta(Request.Meta):
        abstract = True


class Error(ErrorBase):
    pass


class Redirect(ErrorBase):
    location = models.TextField(db_index=True)
