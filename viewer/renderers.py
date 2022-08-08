from rest_framework.renderers import TemplateHTMLRenderer


class BetterTemplateHTMLRenderer(TemplateHTMLRenderer):
    """Properly handle non-paginated HTML results.

    See https://github.com/encode/django-rest-framework/issues/5236#issuecomment-653451009.
    """

    def get_template_context(self, *args, **kwargs):
        context = super().get_template_context(*args, **kwargs)
        if isinstance(context, list):
            context = {"results": context}
        return context
