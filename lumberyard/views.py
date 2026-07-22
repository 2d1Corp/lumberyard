from django.contrib.auth.decorators import login_required
from django.shortcuts import render

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
