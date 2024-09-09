from django.urls import path
from django.views.generic import TemplateView

from viewer import views


urlpatterns = [
    path("", views.PageListView.as_view(), name="index"),
    path("page/", views.PageDetailView.as_view(), name="page"),
    path("components/", views.ComponentListView.as_view(), name="components"),
    path("errors/", views.ErrorListView.as_view(), name="errors"),
    path("redirects/", views.RedirectListView.as_view(), name="redirects"),
    path("help/", TemplateView.as_view(template_name="viewer/help.html"), name="help"),
]
