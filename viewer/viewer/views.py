import re
from urllib.parse import unquote

from django.db.models.expressions import RawSQL
from django.http import Http404
from django.http.request import QueryDict
from django.template.response import TemplateResponse
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormMixin

from .forms import SearchForm
from .models import Page, PageHTML


class PageListView(ListView):
    model = Page
    context_object_name = "pages"
    paginate_by = 50

    def get_paginate_by(self, queryset):
        return self.request.GET.get("paginate_by", self.paginate_by)

    def get_context_data(self, *args, **kwargs):
        qs = self.object_list
        pagination_query_params = QueryDict({}, mutable=True)

        form = SearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data.get("q")
            search_type = form.cleaned_data.get("search_type")
            paginate_by = form.cleaned_data.get("paginate_by")
            pagination_query_params["q"] = q

            if q:
                pagination_query_params["search_type"] = search_type
                pagination_query_params["paginate_by"] = paginate_by

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
            object_list=qs,
            form=form.cleaned_data,
            pagination_query_params=pagination_query_params.urlencode(),
        )


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
