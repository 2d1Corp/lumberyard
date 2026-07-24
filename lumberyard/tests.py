from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import (
    Category,
    Material,
    MaterialSupplier,
    StockBalance,
    Supplier,
    Warehouse,
    Worker,
)


class SeedDataCommandTests(TestCase):
    def test_seed_data_is_idempotent(self):
        output = StringIO()

        call_command("seed_data", stdout=output)
        call_command("seed_data", stdout=output)

        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(Supplier.objects.count(), 3)
        self.assertEqual(Warehouse.objects.count(), 2)
        self.assertEqual(Material.objects.count(), 12)
        self.assertEqual(StockBalance.objects.count(), 16)
        self.assertEqual(MaterialSupplier.objects.count(), 12)
        self.assertTrue(Material.objects.filter(sku="OAK-BOARD-25").exists())


class MaterialListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Lumber")
        cls.user = Worker.objects.create_user(
            username="worker",
            password="test-password",
            phone_number="+10000000000",
        )
        cls.name_match = Material.objects.create(
            name="Oak Board",
            sku="BOARD-001",
            category=category,
        )
        cls.sku_match = Material.objects.create(
            name="Pine Beam",
            sku="OAK-002",
            category=category,
        )
        Material.objects.create(
            name="Birch Plywood",
            sku="PLY-003",
            category=category,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_search_matches_name_or_sku_case_insensitively(self):
        response = self.client.get(
            reverse("material-list"),
            {"query": "OAK"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["material_list"],
            [self.name_match, self.sku_match],
            ordered=False,
        )


class ToggleReplenishmentViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Boards")
        material = Material.objects.create(
            name="Oak Board",
            sku="OAK-BOARD-001",
            category=category,
        )
        warehouse = Warehouse.objects.create(name="Main Warehouse")
        cls.user = Worker.objects.create_user(
            username="warehouse-worker",
            password="test-password",
            phone_number="+10000000001",
        )
        cls.stock = StockBalance.objects.create(
            material=material,
            warehouse=warehouse,
            quantity=10,
        )
        cls.url = reverse(
            "material-toggle-replenishment",
            args=[material.pk, cls.stock.pk],
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_does_not_request_replenishment(self):
        response = self.client.get(self.url)

        self.stock.refresh_from_db()

        self.assertEqual(response.status_code, 405)
        self.assertIsNone(self.stock.replenishment_requested_at)

    def test_post_requests_replenishment(self):
        response = self.client.post(self.url)

        self.stock.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(self.stock.replenishment_requested_at)
        self.assertEqual(self.stock.replenishment_requested_by, self.user)

    def test_post_ignores_external_next_url(self):
        response = self.client.post(
            self.url,
            {"next": "https://attacker.example/phishing"},
        )

        self.assertEqual(
            response.url,
            reverse(
                "material-detail",
                args=[self.stock.material_id],
            ),
        )

    def test_post_accepts_local_next_url(self):
        next_url = reverse("replenishment-list")

        response = self.client.post(
            self.url,
            {"next": next_url},
        )

        self.assertEqual(response.url, next_url)
