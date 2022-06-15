import codecs
import csv
from datetime import datetime

from django.db.models import CharField, ExpressionWrapper, F, Func
from django.db.models.expressions import RawSQL
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.http.request import QueryDict
from django.views.generic import DetailView, ListView, View

from .database import get_crawl_database_filename
from .forms import SearchForm
from .models import Page


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

                if "links" == search_type:
                    qs = qs.filter(links__icontains=q)
                elif "components" == search_type:
                    qs = qs.filter(components__icontains=q)
                elif "html" == search_type:
                    qs = qs.filter(
                        path__in=RawSQL(
                            "SELECT path FROM cfgov_fts WHERE cfgov_fts MATCH %s",
                            [f'pageHtml : ( "{q}" )'],
                        )
                    )

        return super().get_context_data(
            all_pages=qs,
            total_count=self.model.objects.count(),
            object_list=qs,
            form=form.cleaned_data,
            pagination_query_params=pagination_query_params.urlencode(),
        )


class PrepDatetimeForCSV(Func):
   function = 'DATETIME'


class DownloadCSVView(PageListView):
    def render_to_response(self, context, **response_kwargs):
        if not context["total_count"]:
            raise Http404

        return StreamingHttpResponse(
            self.generate_csv_content(context),
            content_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=\"export.csv\"",
            }
        )

    def generate_csv_content(self, context):
        columns = (
            "path",
            "title",
            "crawled",
            "hash",
        )

        # Inspired by https://docs.djangoproject.com/en/4.0/howto/outputting-csv/#streaming-large-csv-files.
        class Echo:
            def write(self, value):
                return value

        buffer = Echo()
        yield buffer.write(codecs.BOM_UTF8) # u'\ufeff'.encode('utf8'))

        writer = csv.writer(buffer)

        yield writer.writerow(columns)

        pages = context["all_pages"] \
            .annotate(
                crawled=ExpressionWrapper(
                    Func(F("timestamp"), function="DATETIME"),
                    output_field=CharField()
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
        if filename := get_crawl_database_filename():
            return FileResponse(open(filename, "rb"))

        raise Http404
