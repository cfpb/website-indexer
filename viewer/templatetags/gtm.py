from django import template
from django.conf import settings


register = template.Library()


def add_google_tag_id_to_context(context):
    context["GOOGLE_TAG_ID"] = getattr(settings, "GOOGLE_TAG_ID", None)
    return context


for tag in ("head", "body"):
    register.inclusion_tag(
        f"viewer/gtm/{tag}.html", name=f"gtm_{tag}", takes_context=True
    )(add_google_tag_id_to_context)
