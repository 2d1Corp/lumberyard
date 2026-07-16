from django.contrib import admin

from .models import Category, Supplier, Warehouse

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Warehouse)