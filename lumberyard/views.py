from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .forms import WorkerCreationForm
from .models import Category, Material, Supplier, Warehouse, Worker


def index(request):
    context = {
        "categories": Category.objects.all(),
    }
    return render(
        request,
        "lumberyard/index.html",
        context,
    )


@login_required
def dashboard(request):
    context = {
        "material_count": Material.objects.count(),
        "supplier_count": Supplier.objects.count(),
        "warehouse_count": Warehouse.objects.count(),
        "worker_count": Worker.objects.count(),
    }
    return render(request, "lumberyard/dashboard.html", context)


class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    queryset = Material.objects.select_related("category")
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("query", "").strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
            )

        return queryset


class MaterialDetailView(LoginRequiredMixin, DetailView):
    model = Material
    queryset = Material.objects.select_related("category").prefetch_related(
        "stock_balances__warehouse",
        "supplier_offers__supplier",
    )


class WorkerCreateView(PermissionRequiredMixin, CreateView):
    form_class = WorkerCreationForm
    template_name = "lumberyard/worker_form.html"
    success_url = reverse_lazy("dashboard")
    permission_required = "lumberyard.add_worker"
