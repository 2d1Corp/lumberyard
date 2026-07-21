from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "supplier"
        verbose_name_plural = "suppliers"

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=255, unique=True)
    workers = models.ManyToManyField(
        "Worker",
        related_name="warehouses",
        blank=True
    ) #lazy reference, forward references. Assigned before class Worker model
    class Meta:
        ordering = ["name"]
        verbose_name = "warehouse"
        verbose_name_plural = "warehouses"

    def __str__(self):
        return self.name


class Worker(AbstractUser):
    phone_number = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = "worker"
        verbose_name_plural = "workers"

    def __str__(self):
        return f"{self.username} {self.first_name} {self.last_name} {self.phone_number}"


class Material(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    in_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="materials"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials"
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="materials")

    class Meta:
        ordering = ["name"]
        verbose_name = "material"
        verbose_name_plural = "materials"

    def __str__(self):
        return f"{self.name} - {self.sku}"

