from django.urls import path

from . import views

urlpatterns = [
    path("", views.PageListView.as_view(), name="index"),
    path("page/", views.PageDetailView.as_view(), name="page"),
]