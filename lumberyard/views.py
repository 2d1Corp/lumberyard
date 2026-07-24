from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db.models import Count, Q, Sum, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
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
        requested_count=Count("stock_balances", filter=Q(
            stock_balances__replenishment_requested_at__isnull=False
        )),
        stock_count=Count("stock_balances"),
    ).order_by("name", "pk")
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
    success_url = reverse_lazy("worker-list")
    permission_required = "lumberyard.add_worker"


class WorkerListView(LoginRequiredMixin, ListView):
    model = Worker
    queryset = Worker.objects.all().order_by("username")


class WorkerDeleteView(PermissionRequiredMixin, DeleteView):
    model = Worker
    template_name = "lumberyard/worker_confirm_delete.html"
    success_url = reverse_lazy("worker-list")
    permission_required = "lumberyard.delete_worker"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_superuser=False)
            .exclude(pk=self.request.user.pk)
        )


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
@require_POST
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
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("material-detail", pk=pk)


@login_required
@require_POST
def toggle_material_replenishment(request, pk):
    get_object_or_404(Material, pk=pk)
    stocks = StockBalance.objects.filter(material_id=pk)
    if not stocks.exists():
        messages.error(request, "This material has no stock to replenish.")
        return redirect("material-detail", pk=pk)

    all_requested = not stocks.filter(replenishment_requested_at__isnull=True).exists()
    if all_requested:
        stocks.update(
            replenishment_requested_at=None,
            replenishment_requested_by=None,
        )
        messages.success(request, "Removed all stock of this material from the list.")
    else:
        now = timezone.now()
        for stock in stocks.filter(replenishment_requested_at__isnull=True):
            stock.replenishment_requested_at = now
            stock.replenishment_requested_by = request.user
            stock.save(update_fields=["replenishment_requested_at", "replenishment_requested_by"])
        messages.success(request, "Added all stock of this material to the list.")
    return redirect("material-list")



