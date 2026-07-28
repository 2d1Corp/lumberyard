from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from lumberyard.models import (
    Category,
    Material,
    MaterialSupplier,
    StockBalance,
    Supplier,
    Warehouse,
)


class Command(BaseCommand):
    help = "Load idempotent demo data for local development"

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {
            name: Category.objects.get_or_create(name=name)[0]
            for name in (
                "Lumber",
                "Sheet Goods",
            )
        }
        suppliers = {
            name: Supplier.objects.get_or_create(name=name)[0]
            for name in (
                "Baltic Panels Ltd.",
                "Northern Timber Co.",
            )
        }
        warehouses = {
            name: Warehouse.objects.get_or_create(name=name)[0]
            for name in ("Main Warehouse", "North Yard")
        }

        material_data = (
            {
                "sku": "OAK-BOARD-25",
                "name": "Oak Board",
                "category": "Lumber",
                "unit": Material.Unit.PIECE,
                "sale_price": "48.50",
                "species": "Oak",
                "grade": "A",
                "thickness_mm": 25,
                "width_mm": 150,
                "length_mm": 3000,
            },
            {
                "sku": "PINE-BEAM-100",
                "name": "Pine Beam",
                "category": "Lumber",
                "unit": Material.Unit.PIECE,
                "sale_price": "36.00",
                "species": "Pine",
                "grade": "Construction",
                "thickness_mm": 100,
                "width_mm": 100,
                "length_mm": 4000,
            },
            {
                "sku": "ASH-BOARD-30",
                "name": "Ash Board",
                "category": "Lumber",
                "unit": Material.Unit.PIECE,
                "sale_price": "55.75",
                "species": "Ash",
                "grade": "A/B",
                "thickness_mm": 30,
                "width_mm": 180,
                "length_mm": 3000,
            },
            {
                "sku": "SPRUCE-BATTEN-50",
                "name": "Spruce Batten",
                "category": "Lumber",
                "unit": Material.Unit.METER,
                "sale_price": "4.20",
                "species": "Spruce",
                "grade": "Construction",
                "thickness_mm": 50,
                "width_mm": 50,
                "length_mm": None,
            },
            {
                "sku": "BIRCH-PLY-18",
                "name": "Birch Plywood 18 mm",
                "category": "Sheet Goods",
                "unit": Material.Unit.SQUARE_METER,
                "sale_price": "28.90",
                "species": "Birch",
                "grade": "BB/BB",
                "thickness_mm": 18,
                "width_mm": 1250,
                "length_mm": 2500,
            },
            {
                "sku": "OSB3-12",
                "name": "OSB-3 Panel 12 mm",
                "category": "Sheet Goods",
                "unit": Material.Unit.SQUARE_METER,
                "sale_price": "12.40",
                "species": "",
                "grade": "OSB-3",
                "thickness_mm": 12,
                "width_mm": 1250,
                "length_mm": 2500,
            },
            {
                "sku": "MDF-16",
                "name": "MDF Panel 16 mm",
                "category": "Sheet Goods",
                "unit": Material.Unit.SQUARE_METER,
                "sale_price": "15.80",
                "species": "",
                "grade": "Standard",
                "thickness_mm": 16,
                "width_mm": 1220,
                "length_mm": 2440,
            },
            {
                "sku": "CHIPBOARD-18",
                "name": "Chipboard 18 mm",
                "category": "Sheet Goods",
                "unit": Material.Unit.SQUARE_METER,
                "sale_price": "10.60",
                "species": "",
                "grade": "P2",
                "thickness_mm": 18,
                "width_mm": 1830,
                "length_mm": 2750,
            },
        )

        materials = {}
        for data in material_data:
            sku = data["sku"]
            defaults = {
                "name": data["name"],
                "description": "Demo catalog item for local development.",
                "sale_price": Decimal(data["sale_price"]),
                "category": categories[data["category"]],
                "unit": data["unit"],
                "species": data["species"],
                "grade": data["grade"],
                "thickness_mm": data["thickness_mm"],
                "width_mm": data["width_mm"],
                "length_mm": data["length_mm"],
            }
            materials[sku] = Material.objects.update_or_create(
                sku=sku,
                defaults=defaults,
            )[0]

        stock_data = (
            ("OAK-BOARD-25", "Main Warehouse", "42.000"),
            ("OAK-BOARD-25", "North Yard", "18.000"),
            ("PINE-BEAM-100", "Main Warehouse", "65.000"),
            ("PINE-BEAM-100", "North Yard", "31.000"),
            ("ASH-BOARD-30", "Main Warehouse", "24.000"),
            ("SPRUCE-BATTEN-50", "North Yard", "280.000"),
            ("BIRCH-PLY-18", "Main Warehouse", "96.500"),
            ("BIRCH-PLY-18", "North Yard", "35.000"),
            ("OSB3-12", "Main Warehouse", "144.000"),
            ("OSB3-12", "North Yard", "72.000"),
            ("MDF-16", "Main Warehouse", "80.000"),
            ("CHIPBOARD-18", "North Yard", "54.000"),
        )
        for sku, warehouse_name, quantity in stock_data:
            StockBalance.objects.update_or_create(
                material=materials[sku],
                warehouse=warehouses[warehouse_name],
                defaults={"quantity": Decimal(quantity)},
            )

        offer_data = (
            ("OAK-BOARD-25", "Northern Timber Co.", "31.20", "NT-OAK-25"),
            ("PINE-BEAM-100", "Northern Timber Co.", "22.50", "NT-PB-100"),
            ("ASH-BOARD-30", "Northern Timber Co.", "38.40", "NT-ASH-30"),
            ("SPRUCE-BATTEN-50", "Northern Timber Co.", "2.55", "NT-SB-50"),
            ("BIRCH-PLY-18", "Baltic Panels Ltd.", "20.10", "BP-BIR-18"),
            ("OSB3-12", "Baltic Panels Ltd.", "8.25", "BP-OSB3-12"),
            ("MDF-16", "Baltic Panels Ltd.", "10.90", "BP-MDF-16"),
            ("CHIPBOARD-18", "Baltic Panels Ltd.", "7.10", "BP-CHIP-18"),
        )
        for sku, supplier_name, purchase_price, supplier_sku in offer_data:
            MaterialSupplier.objects.update_or_create(
                material=materials[sku],
                supplier=suppliers[supplier_name],
                defaults={
                    "purchase_price": Decimal(purchase_price),
                    "supplier_sku": supplier_sku,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready: "
                f"{len(categories)} categories, "
                f"{len(suppliers)} suppliers, "
                f"{len(warehouses)} warehouses, "
                f"{len(materials)} materials, "
                f"{len(stock_data)} stock balances, "
                f"{len(offer_data)} supplier offers."
            )
        )
