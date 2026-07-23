from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db.models import Q, Sum, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
    DeleteView,
)
from .forms import WorkerCreationForm, MaterialForm
from .models import Category, Material, StockBalance, Supplier, Warehouse, Worker


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
        "replenishment_count": StockBalance.objects.filter(
            replenishment_requested_at__isnull=False
        ).count(),
    }
    return render(request, "lumberyard/dashboard.html", context)


class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    queryset = Material.objects.select_related("category").annotate(
        total_stock=Sum("stock_balances__quantity"),
    )
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

class MaterialCreateView(LoginRequiredMixin, CreateView):
    form_class = MaterialForm
    template_name = "lumberyard/material_form.html"

    def get_success_url(self):
        return reverse("material-detail", kwargs={"pk": self.object.pk})


class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = Material
    form_class = MaterialForm
    template_name = "lumberyard/material_form.html"

    def get_success_url(self):
        return reverse("material-detail", kwargs={"pk": self.object.pk})


class MaterialDeleteView(LoginRequiredMixin, DeleteView):
    model = Material
    template_name = "lumberyard/material_confirm_delete.html"
    success_url = reverse_lazy("material-list")

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "Cannot delete material because it still has stock.",
            )
            return redirect("material-detail", pk=self.object.pk)
        return redirect(self.get_success_url())

class WorkerCreateView(PermissionRequiredMixin, CreateView):
    form_class = WorkerCreationForm
    template_name = "lumberyard/worker_form.html"
    success_url = reverse_lazy("dashboard")
    permission_required = "lumberyard.add_worker"


class ReplenishmentListView(LoginRequiredMixin, ListView):
    model = StockBalance
    template_name = "lumberyard/replenishment_list.html"
    queryset = StockBalance.objects.filter(
        replenishment_requested_at__isnull=False
    ).select_related(
        "material",
        "warehouse",
        "replenishment_requested_by",
    ).order_by("-replenishment_requested_at")


@login_required
def toggle_replenishment(request, pk, stock_pk):
    stock = get_object_or_404(
        StockBalance,
        pk=stock_pk,
        material_id=pk,
    )
    if stock.replenishment_requested_at is None:
        stock.replenishment_requested_at = timezone.now()
        stock.replenishment_requested_by = request.user
        stock.save(update_fields=["replenishment_requested_at", "replenishment_requested_by"])
        messages.success(request, "Added to replenishment list.")
    else:
        stock.replenishment_requested_at = None
        stock.replenishment_requested_by = None
        stock.save(update_fields=["replenishment_requested_at", "replenishment_requested_by"])
        messages.success(request, "Removed from replenishment list.")
    return redirect("material-detail", pk=pk)



