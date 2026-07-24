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
        "materials/create/",
        views.MaterialCreateView.as_view(),
        name="material-create"
    ),
    path(
        "materials/<int:pk>/update/",
        views.MaterialUpdateView.as_view(),
        name="material-update",
    ),
    path(
        "materials/<int:pk>/delete/",
        views.MaterialDeleteView.as_view(),
        name="material-delete",
    ),
    path(
        "workers/",
        views.WorkerListView.as_view(),
        name="worker-list",
    ),
    path(
        "workers/create/",
        views.WorkerCreateView.as_view(),
        name="worker-create",
    ),
    path(
        "workers/<int:pk>/delete/",
        views.WorkerDeleteView.as_view(),
        name="worker-delete",
    ),
    path(
        "materials/<int:pk>/stock/<int:stock_pk>/toggle-replenishment/",
        views.toggle_replenishment,
        name="material-toggle-replenishment",
    ),
    path(
        "replenishment/",
        views.ReplenishmentListView.as_view(),
        name="replenishment-list",
    ),
    path(
        "materials/<int:material_pk>/stock/<int:warehouse_pk>/update/",
        views.stockbalance_update,
        name="stockbalance-update",
    ),
]
