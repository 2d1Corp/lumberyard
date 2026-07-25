from decimal import Decimal, InvalidOperation

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
    TemplateView,
    UpdateView,
    DeleteView,
)
from .forms import WorkerCreationForm, MaterialForm, SupplierForm, CategoryForm, WarehouseForm
from .models import Category, Material, StockBalance, Supplier, Warehouse, Worker, MaterialSupplier


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_by_warehouse = {
            sb.warehouse_id: sb for sb in self.object.stock_balances.all()
        }
        context["stock_rows"] = [
            (warehouse, stock_by_warehouse.get(warehouse.pk))
            for warehouse in Warehouse.objects.all()
        ]
        context["suppliers"] = Supplier.objects.all()
        return context

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
def stockbalance_update(request, material_pk, warehouse_pk):
    material = get_object_or_404(Material, pk=material_pk)
    warehouse = get_object_or_404(Warehouse, pk=warehouse_pk)
    quantity = request.POST.get("quantity", "").strip()

    try:
        quantity = Decimal(quantity)
    except (InvalidOperation, ValueError):
        messages.error(request, "Enter a valid quantity.")
        return redirect("material-detail", pk=material_pk)

    if quantity < 0:
        messages.error(request, "Quantity cannot be negative.")
        return redirect("material-detail", pk=material_pk)

    stock = StockBalance.objects.filter(
        material=material, warehouse=warehouse
    ).first()

    if quantity == 0:
        if stock is not None:
            stock.delete()
            messages.success(request, "Stock removed.")
    else:
        if stock is None:
            StockBalance.objects.create(
                material=material, warehouse=warehouse, quantity=quantity
            )
            messages.success(request, "Stock added.")
        else:
            stock.quantity = quantity
            stock.save(update_fields=["quantity"])
            messages.success(request, "Stock quantity updated.")

    return redirect("material-detail", pk=material_pk)


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier


class SupplierCreateView(LoginRequiredMixin, CreateView):
    form_class = SupplierForm
    template_name = "lumberyard/supplier_form.html"
    success_url = reverse_lazy("supplier-list")


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "lumberyard/supplier_form.html"
    success_url = reverse_lazy("supplier-list")


class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    template_name = "lumberyard/supplier_confirm_delete.html"
    success_url = reverse_lazy("supplier-list")

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "Cannot delete supplier because it still has offers."
            )
            return redirect("supplier-list")
        return redirect(self.get_success_url())


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category


class CategoryCreateView(LoginRequiredMixin, CreateView):
    form_class = CategoryForm
    template_name = "lumberyard/category_form.html"
    success_url = reverse_lazy("category-list")


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "lumberyard/category_form.html"
    success_url = reverse_lazy("category-list")


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = "lumberyard/category_confirm_delete.html"
    success_url = reverse_lazy("category-list")

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "Cannot delete category because it still has materials.",
            )
            return redirect("category-list")
        return redirect(self.get_success_url())


class WarehouseListView(LoginRequiredMixin, ListView):
    model = Warehouse


class WarehouseCreateView(LoginRequiredMixin, CreateView):
    form_class = WarehouseForm
    template_name = "lumberyard/warehouse_form.html"
    success_url = reverse_lazy("warehouse-list")


class WarehouseUpdateView(LoginRequiredMixin, UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = "lumberyard/warehouse_form.html"
    success_url = reverse_lazy("warehouse-list")


class WarehouseDeleteView(LoginRequiredMixin, DeleteView):
    model = Warehouse
    template_name = "lumberyard/warehouse_confirm_delete.html"
    success_url = reverse_lazy("warehouse-list")

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "Cannot delete warehouse because it still has stock.",
            )
            return redirect("warehouse-list")
        return redirect(self.get_success_url())


@login_required
@require_POST
def offer_save(request, material_pk):
    material = get_object_or_404(Material, pk=material_pk)
    supplier = get_object_or_404(Supplier, pk=request.POST.get("supplier"))
    price_raw = request.POST.get("purchase_price", "").strip()
    try:
        price = Decimal(price_raw)
    except (InvalidOperation, ValueError):
        messages.error(request, "Enter a valid purchase price.")
        return redirect("material-detail", pk=material_pk)
    if price < 0:
        messages.error(request, "Purchase price cannot be negative.")
        return redirect("material-detail", pk=material_pk)
    supplier_sku = request.POST.get("supplier_sku", "").strip()
    _, created = MaterialSupplier.objects.update_or_create(
        material=material,
        supplier=supplier,
        defaults={"purchase_price": price, "supplier_sku": supplier_sku},
    )
    messages.success(request, "Offer added." if created else "Offer updated.")
    return redirect("material-detail", pk=material_pk)


@login_required
@require_POST
def offer_delete(request, material_pk, supplier_pk):
    material = get_object_or_404(Material, pk=material_pk)
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    MaterialSupplier.objects.filter(material=material, supplier=supplier).delete()
    messages.success(request, "Offer removed.")
    return redirect("material-detail", pk=material_pk)


class PublicMaterialListView(ListView):
    model = Material
    template_name = "lumberyard/public_material_list.html"
    context_object_name = "materials"
    paginate_by = 10

    queryset = Material.objects.select_related("category").annotate(
        total_stock=Sum("stock_balances__quantity")
    ).order_by("name", "pk")

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("query", "").strip()
        category = self.request.GET.get("category", "").strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
            )

        if category.isdigit():
            queryset = queryset.filter(category__id=category)

        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["selected_category"] = self.request.GET.get(
            "category", ""
        ).strip()
        return context


class PublicMaterialDetailView(DetailView):
    model = Material
    template_name = "lumberyard/public_material_detail.html"
    context_object_name = "material"

    queryset = (
        Material.objects
        .select_related("category")
        .annotate(
            total_stock=Sum("stock_balances__quantity")
        )
    )


class DeliveryView(TemplateView):
    template_name = "lumberyard/delivery.html"


class ContactsView(TemplateView):
    template_name = "lumberyard/contacts.html"
