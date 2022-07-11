import codecs
import csv

from django.conf import settings
from django.db.models import CharField, ExpressionWrapper, F, Func
from django.db.models import Exists, OuterRef
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.http.request import QueryDict
from django.shortcuts import render
from django.views.generic import DetailView, ListView, View

from .forms import SearchForm
from .models import Component, Page


class PageListView(ListView):
    model = Page
    context_object_name = "pages"
    paginate_by = 25

    def get_context_data(self, *args, **kwargs):
        qs = self.object_list
        pagination_query_params = QueryDict({}, mutable=True)

        form = SearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data.get("q")
            search_type = form.cleaned_data.get("search_type")
            pagination_query_params["q"] = q

            if q:
                pagination_query_params["search_type"] = search_type

                if "title" == search_type:
                    qs = qs.filter(title__icontains=q).order_by("title")
                    ordering = "title"
                elif "path" == search_type:
                    qs = qs.filter(path__icontains=q)
                elif "components" == search_type:
                    # This is significantly faster than the simpler
                    # qs = qs.filter(components__name__icontains=q)
                    qs = qs.filter(
                        Exists(
                            Page.components.through.objects.filter(
                                page=OuterRef("id"), component__name__icontains=q
                            )
                        )
                    )
                elif "links" == search_type:
                    # This is significantly faster than the simpler
                    # qs = qs.filter(links__url_icontains=q)
                    qs = qs.filter(
                        Exists(
                            Page.links.through.objects.filter(
                                page=OuterRef("id"), link__url__icontains=q
                            )
                        )
                    )
                elif "html" == search_type:
                    qs = qs.filter(html__icontains=q)

        qs = qs.only("path", "title")

        return super().get_context_data(
            object_list=qs,
            form=form.cleaned_data,
            pagination_query_params=pagination_query_params.urlencode(),
        )


class DownloadCSVView(PageListView):
    def render_to_response(self, context, **response_kwargs):
        return StreamingHttpResponse(
            self.generate_csv_content(context),
            content_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="export.csv"',
            },
        )

    def generate_csv_content(self, context):
        columns = (
            "path",
            "title",
            "crawled_at",
            "hash",
        )

        # Inspired by https://docs.djangoproject.com/en/4.0/howto/outputting-csv/#streaming-large-csv-files.
        class Echo:
            def write(self, value):
                return value

        buffer = Echo()
        yield buffer.write(codecs.BOM_UTF8)  # u'\ufeff'.encode('utf8'))

        writer = csv.writer(buffer)

        yield writer.writerow(columns)

        pages = context["pages"].annotate(
            crawled=ExpressionWrapper(
                Func(F("timestamp"), function="DATETIME"), output_field=CharField()
            )
        )

        for page in pages.iterator():
            yield writer.writerow(getattr(page, col) for col in columns)


class PageDetailView(DetailView):
    model = Page

    def get_object(self, queryset=None):
        path = self.request.GET.get("path")

        if not path:
            raise Http404("Missing path parameter")

        try:
            return Page.objects.get(path=path)
        except Page.DoesNotExist:
            raise Http404(path)


class DownloadDatabaseView(View):
    def get(self, request, *args, **kwargs):
        return FileResponse(open(settings.CRAWL_DATABASE, "rb"))


class ComponentsListView(ListView):
    model = Component
    context_object_name = "components"
