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

    def __str__(self):
        return self.url


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
