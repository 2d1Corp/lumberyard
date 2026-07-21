from django.contrib import admin
from django.db import models
from django.forms import CheckboxSelectMultiple

from .models import Category, Supplier, Warehouse, Worker, Material

admin.site.register(Category)
admin.site.register(Supplier)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.ManyToManyField: {'widget': CheckboxSelectMultiple},
    }

admin.site.register(Worker)
admin.site.register(Material)

