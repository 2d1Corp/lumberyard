from django import forms
from django.contrib.auth.forms import UserCreationForm

from lumberyard.models import Category, Material, Supplier, Warehouse, Worker


class WorkerCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Worker
        fields = (
            "username",
            "first_name",
            "last_name",
            "phone_number",
        )


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = (
            "name",
            "sku",
            "category",
            "sale_price",
            "unit",
            "species",
            "grade",
            "thickness_mm",
            "width_mm",
            "length_mm",
            "description",
        )


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ("name",)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name",)


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ("name",)
