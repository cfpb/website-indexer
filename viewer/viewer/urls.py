from django.urls import include, path

from rest_framework import routers

from viewer import views


router = routers.DefaultRouter()
router.register(r"components", views.ComponentViewSet)
router.register(r"errors", views.ErrorViewSet)
router.register(r"pages", views.PageViewSet)
router.register(r"redirects", views.RedirectViewSet)


urlpatterns = [
    path("", views.PageListView.as_view(), name="index"),
    path("page/", views.PageDetailView.as_view(), name="page"),
    path("download-csv/", views.DownloadCSVView.as_view(), name="download-csv"),
    path(
        "download-database/",
        views.DownloadDatabaseView.as_view(),
        name="download-database",
    ),
    path("components", views.ComponentsListView.as_view(), name="components"),
    path("api/", include(router.urls)),
]
