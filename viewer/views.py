from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View

from rest_framework.generics import ListAPIView, RetrieveAPIView

from crawler.models import Component, Error, Page, Redirect
from crawler.search import (
    search_components,
    search_empty,
    search_html,
    search_links,
    search_text,
    search_title,
    search_url,
)
from viewer.context_processors import crawl_stats
from viewer.forms import SearchForm
from viewer.renderers import BetterTemplateHTMLRenderer
from viewer.serializers import (
    ComponentSerializer,
    ErrorSerializer,
    PageSerializer,
    PageDetailSerializer,
    PageWithComponentSerializer,
    PageWithLinkSerializer,
    RedirectSerializer,
)


class AlsoRenderHTMLMixin:
    @property
    def renderer_classes(self):
        return [BetterTemplateHTMLRenderer] + super().renderer_classes


class BetterCSVsMixin:
    @property
    def is_rendering_csv(self):
        return self.request.query_params.get("format") == "csv"

    @property
    def paginator(self):
        """Disable pagination when rendering CSVs."""
        return None if self.is_rendering_csv else super().paginator

    def get_renderer_context(self):
        """Add utf-8 BOM when rendering CSVs."""
        context = super().get_renderer_context()

        if self.is_rendering_csv:
            serializer_cls = self.get_serializer_class()

            context.update(
                {
                    "bom": True,
                    "header": getattr(serializer_cls.Meta, "csv_header", None),
                }
            )

        return context

    def finalize_response(self, *args, **kwargs):
        response = super().finalize_response(*args, **kwargs)

        if self.is_rendering_csv:
            filename = self.csv_basename

            crawl_start = crawl_stats()["crawl_stats"]["start"]
            if crawl_start:
                filename += f"-{crawl_start.strftime('%Y%m%d')}"

            response["Content-Disposition"] = f"attachment; filename={filename}.csv"

        return response


class ComponentListView(AlsoRenderHTMLMixin, BetterCSVsMixin, ListAPIView):
    serializer_class = ComponentSerializer
    pagination_class = None
    csv_basename = "components"

    def get_queryset(self):
        return Component.objects.all()

    def get_template_names(self):
        return ["viewer/component_list.html"]


class ErrorListView(BetterCSVsMixin, ListAPIView):
    serializer_class = ErrorSerializer
    filterset_fields = ["status_code"]
    csv_basename = "errors"

    def get_queryset(self):
        return Error.objects.all()


class RedirectListView(BetterCSVsMixin, ListAPIView):
    serializer_class = RedirectSerializer
    filterset_fields = ["status_code"]
    csv_basename = "redirects"

    def get_queryset(self):
        return Redirect.objects.all()


class PageMixin(AlsoRenderHTMLMixin, BetterCSVsMixin):
    filterset_fields = ["language"]
    csv_basename = "pages"

    def get_queryset(self):
        form = SearchForm(self.request.query_params)
        if form.is_valid():
            q = form.cleaned_data["q"]
            search_type = form.cleaned_data["search_type"]

            if "components" == search_type:
                return search_components(q, include_class_names=self.is_rendering_csv)
            elif "html" == search_type:
                return search_html(q)
            elif "links" == search_type:
                return search_links(q, include_hrefs=self.is_rendering_csv)
            elif "text" == search_type:
                return search_text(q)
            elif "title" == search_type:
                return search_title(q)
            elif "url" == search_type:  # pragma: no branch
                return search_url(q)

        return search_empty()


class PageListView(PageMixin, ListAPIView):
    def get_template_names(self):
        return ["viewer/search_results.html"]

    def get_serializer_class(self):
        if self.is_rendering_csv:
            search_type = self.request.query_params.get("search_type")

            if search_type == "components":
                return PageWithComponentSerializer
            elif search_type == "links":
                return PageWithLinkSerializer

        return PageSerializer


class PageDetailView(PageMixin, RetrieveAPIView):
    serializer_class = PageDetailSerializer

    def get_object(self):
        queryset = Page.objects.all().prefetch_related("components", "links")
        return get_object_or_404(queryset, url=self.request.query_params.get("url"))

    def get_template_names(self):
        return ["viewer/page_detail.html"]
