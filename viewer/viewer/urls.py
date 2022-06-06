from django.urls import path

from . import views


urlpatterns = [
    path("", views.PageListView.as_view(), name="index"),
    path("page/", views.PageDetailView.as_view(), name="page"),
    path(
        "download-csv/",
        views.DownloadCSVView.as_view(),
        name="download-csv"
    ),
    path(
        "download-database/",
        views.DownloadDatabaseView.as_view(),
        name="download-database"
    ),
]
