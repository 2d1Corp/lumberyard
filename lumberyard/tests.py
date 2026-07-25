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

        self.assertEqual(Category.objects.count(), 2)
        self.assertEqual(Supplier.objects.count(), 2)
        self.assertEqual(Warehouse.objects.count(), 2)
        self.assertEqual(Material.objects.count(), 8)
        self.assertEqual(StockBalance.objects.count(), 12)
        self.assertEqual(MaterialSupplier.objects.count(), 8)
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

    def test_queryset_has_deterministic_ordering(self):
        response = self.client.get(
            reverse("material-list"),
        )

        queryset = response.context["paginator"].object_list

        self.assertTrue(queryset.ordered)
        self.assertEqual(queryset.query.order_by, ("name", "pk"))


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


class WorkerDeleteViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Worker.objects.create_superuser(
            username="admin",
            password="test-password",
            phone_number="+10000000002",
        )
        cls.other_superuser = Worker.objects.create_superuser(
            username="owner",
            password="test-password",
            phone_number="+10000000003",
        )
        cls.worker = Worker.objects.create_user(
            username="worker-to-delete",
            password="test-password",
            phone_number="+10000000004",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_cannot_delete_own_account(self):
        response = self.client.post(
            reverse("worker-delete", args=[self.admin.pk]),
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Worker.objects.filter(pk=self.admin.pk).exists(),
        )

    def test_cannot_delete_superuser(self):
        response = self.client.post(
            reverse(
                "worker-delete",
                args=[self.other_superuser.pk],
            ),
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Worker.objects.filter(
                pk=self.other_superuser.pk,
            ).exists(),
        )

    def test_can_delete_regular_worker(self):
        response = self.client.post(
            reverse("worker-delete", args=[self.worker.pk]),
        )

        self.assertRedirects(response, reverse("worker-list"))
        self.assertFalse(
            Worker.objects.filter(pk=self.worker.pk).exists(),
        )

    def test_worker_list_hides_protected_delete_actions(self):
        response = self.client.get(reverse("worker-list"))

        self.assertNotContains(
            response,
            reverse("worker-delete", args=[self.admin.pk]),
        )
        self.assertNotContains(
            response,
            reverse(
                "worker-delete",
                args=[self.other_superuser.pk],
            ),
        )
        self.assertContains(
            response,
            reverse("worker-delete", args=[self.worker.pk]),
        )


class PublicMaterialListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Test Boards")

        cls.material = Material.objects.create(
            name="Public Oak Board",
            sku="PUBLIC-OAK-001",
            category=category,
            sale_price="25.00",
        )

        warehouse = Warehouse.objects.create(
            name="Private Test Warehouse",
        )
        StockBalance.objects.create(
            material=cls.material,
            warehouse=warehouse,
            quantity="137.125",
        )

        supplier = Supplier.objects.create(
            name="Private Test Supplier",
        )
        MaterialSupplier.objects.create(
            material=cls.material,
            supplier=supplier,
            purchase_price="8.99",
            supplier_sku="PRIVATE-SKU-777",
        )

    def test_catalog_is_available_to_anonymous_users(self):
        response = self.client.get(reverse("public-material-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "lumberyard/public_material_list.html",
        )

    def test_catalog_hides_internal_data(self):
        response = self.client.get(
            reverse("public-material-list")
        )

        self.assertContains(response, self.material.name)
        self.assertContains(response, "Available")

        self.assertNotContains(response, "137.125")
        self.assertNotContains(
            response,
            "Private Test Warehouse",
        )
        self.assertNotContains(
            response,
            "Private Test Supplier"
        )
        self.assertNotContains(response, "PRIVATE-SKU-777")
        self.assertNotContains(response, "8.99")

    def test_search_matches_name_or_sku(self):
        sku_match = Material.objects.create(
            name="Pine Beam",
            sku="OAK-SKU-002",
            category=self.material.category,
        )
        non_match = Material.objects.create(
            name="Birch Plywood",
            sku="PLYWOOD-003",
            category=self.material.category,
        )

        response = self.client.get(
            reverse("public-material-list"),
            {"query": "OAK"},
        )

        self.assertContains(response, self.material.name)
        self.assertContains(response, sku_match.name)
        self.assertNotContains(response, non_match.name)

    def test_category_filter_shows_only_selected_category(self):
        other_category = Category.objects.create(
            name="Test Beams",
        )
        other_material = Material.objects.create(
            name="Filtered Pine Beam",
            sku="FILTERED-PINE-001",
            category=other_category,
        )

        response = self.client.get(
            reverse("public-material-list"),
            {"category": self.material.category_id},
        )

        self.assertContains(response, self.material.name)
        self.assertNotContains(response, other_material.name)