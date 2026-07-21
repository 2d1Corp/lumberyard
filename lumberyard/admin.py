from django.contrib import admin
from django.db import models
from django.forms import CheckboxSelectMultiple

from .models import (
    Category,
    Supplier,
    Warehouse,
    Worker,
    Material,
    StockBalance,
    MaterialSupplier,
)

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Worker)
admin.site.register(StockBalance)
admin.site.register(MaterialSupplier)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.ManyToManyField: {'widget': CheckboxSelectMultiple},
    }


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "category",
        "unit",
        "sale_price"
    )
    list_filter = ("category", "unit")
    search_fields = ("sku", "name")