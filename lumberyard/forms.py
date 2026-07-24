from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Worker, Material


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