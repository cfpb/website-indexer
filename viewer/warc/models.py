from django.db import models


class Request(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    url = models.TextField(unique=True, db_index=True)

    class Meta:
        abstract = True


class Page(Request):
    title = models.TextField(db_index=True)
    language = models.TextField(db_index=True, null=True, blank=True)
    html = models.TextField(db_index=True)
    text = models.TextField(db_index=True)


class ErrorBase(Request):
    status_code = models.PositiveIntegerField(db_index=True)
    referrer = models.TextField(db_index=True, null=True, blank=True)

    class Meta:
        abstract = True


class Error(ErrorBase):
    pass


class Redirect(ErrorBase):
    location = models.TextField(db_index=True)


class Component(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="components")
    class_name = models.TextField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page", "class_name"], name="uniq_page_component_class_name"
            ),
        ]


class Link(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="pages")
    href = models.TextField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page", "href"], name="uniq_page_link_href"
            ),
        ]
