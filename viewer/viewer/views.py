from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View

from rest_framework.generics import ListAPIView, RetrieveAPIView

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
from warc.models import Component, Error, Page, Redirect
from warc.search import (
    search_components,
    search_html,
    search_links,
    search_text,
    search_title,
    search_url,
)


class DownloadDatabaseView(View):
    def get(self, request, *args, **kwargs):
        return FileResponse(open(settings.CRAWL_DATABASE, "rb"))


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
            context["bom"] = True

        return context

    def finalize_response(self, *args, **kwargs):
        response = super().finalize_response(*args, **kwargs)

        if self.is_rendering_csv:
            crawl_start = crawl_stats()["crawl_stats"]["end"]
            response["Content-Disposition"] = (
                "attachment; filename="
                f"{self.csv_basename}-"
                f"{crawl_start.strftime('%Y%m%d')}.csv"
            )

        return response


class ComponentListView(AlsoRenderHTMLMixin, BetterCSVsMixin, ListAPIView):
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    pagination_class = None
    csv_basename = "components"

    def get_template_names(self):
        return ["viewer/component_list.html"]


class ErrorListView(BetterCSVsMixin, ListAPIView):
    queryset = Error.objects.all()
    serializer_class = ErrorSerializer
    filterset_fields = ["status_code"]
    csv_basename = "errors"


class RedirectListView(BetterCSVsMixin, ListAPIView):
    queryset = Redirect.objects.all()
    serializer_class = RedirectSerializer
    filterset_fields = ["status_code"]
    csv_basename = "redirects"


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
            elif "url" == search_type:
                return search_url(q)

        return Page.objects.all()


class PageListView(PageMixin, ListAPIView):
    def get_template_names(self):
        return ["viewer/page_list.html"]

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
