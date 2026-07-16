from django.contrib import admin

from .models import Category, Supplier, Warehouse, Worker

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Warehouse)
admin.site.register(Worker)