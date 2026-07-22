from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import ListView

from .models import Material, Supplier, Warehouse, Worker


def index(request):
    return render(request, "lumberyard/index.html")


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
