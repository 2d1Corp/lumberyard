from django.urls import include, path

from . import views

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "materials/",
        views.MaterialListView.as_view(),
        name="material-list",
    ),
    path(
        "materials/<int:pk>/",
        views.MaterialDetailView.as_view(),
        name="material-detail",
    ),
    path(
        "workers/create/",
        views.WorkerCreateView.as_view(),
        name="worker-create",
    ),
]
