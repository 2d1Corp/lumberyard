from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.forms import CheckboxSelectMultiple

from .models import (
    Category,
    Material,
    MaterialSupplier,
    StockBalance,
    Supplier,
    Warehouse,
    Worker,
)

admin.site.register(Category)
admin.site.register(Supplier)
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


@admin.register(Worker)
class WorkerAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Lumberyard",
            {
                "fields": (
                    "phone_number",
                ),
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Lumberyard",
            {
                "fields": (
                    "phone_number",
                ),
            },
        ),
    )

    list_display = (
        "username",
        "first_name",
        "last_name",
        "phone_number",
        "is_staff",
        "is_active",
    )
