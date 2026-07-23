from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from phonenumber_field.modelfields import PhoneNumberField


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
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "warehouse"
        verbose_name_plural = "warehouses"

    def __str__(self):
        return self.name


class Worker(AbstractUser):
    phone_number = PhoneNumberField(unique=True)
    REQUIRED_FIELDS = ["phone_number"]

    class Meta:
        verbose_name = "worker"
        verbose_name_plural = "workers"

    def __str__(self):
        return (
            f"{self.username} {self.first_name} "
            f"{self.last_name} {self.phone_number}"
        )


class Material(models.Model):
    class Unit(models.TextChoices):
        PIECE = "pcs", "Pieces"
        METER = "m", "Meters"
        SQUARE_METER = "m2", "Square Meters"
        CUBIC_METER = "m3", "Cubic Meters"

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="materials",
    )
    unit = models.CharField(
        max_length=10,
        choices=Unit,
        default=Unit.PIECE,
    )
    species = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    thickness_mm = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    width_mm = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    length_mm = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sale_price__gte=0),
                name="material_sale_price_non_negative",
            )
        ]
        ordering = ["name"]
        verbose_name = "material"
        verbose_name_plural = "materials"

    def __str__(self):
        return f"{self.name} - {self.sku} - {self.sale_price}"


class StockBalance(models.Model):
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="stock_balances",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stock_balances",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["material", "warehouse"],
                name="unique_material_warehouse_stock",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="stock_quantity_non_negative",
            ),
        ]
        verbose_name = "stock balance"
        verbose_name_plural = "stock balances"

    def __str__(self):
        return f"{self.material} | {self.warehouse} | {self.quantity}"


class MaterialSupplier(models.Model):
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="supplier_offers",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="material_offers",
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    supplier_sku = models.CharField(
        max_length=100,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["material", "supplier"],
                name="unique_material_supplier_offer",
            ),
            models.CheckConstraint(
                condition=models.Q(purchase_price__gte=0),
                name="supplier_purchase_price_non_negative",
            ),
        ]
        verbose_name = "material supplier"
        verbose_name_plural = "material suppliers"

    def __str__(self):
        return f"{self.material} | {self.supplier} | {self.purchase_price}"
