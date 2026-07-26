from io import StringIO

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from lumberyard.models import (
    Category,
    Material,
    MaterialSupplier,
    StockBalance,
    Supplier,
    Warehouse,
    Worker,
)
from lumberyard.templatetags.lumberyard_extras import (
    MATERIAL_IMAGES,
    category_image,
    material_image,
)


class DashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Worker.objects.create_user(
            username="dashboard-worker",
            password="test-password",
            phone_number="+10000000001",
        )
        cls.category = Category.objects.create(name="Dashboard Lumber")

        for index in range(6):
            Material.objects.create(
                name=f"Dashboard Material {index}",
                sku=f"DASH-{index:03}",
                category=cls.category,
            )

        cls.warehouse = Warehouse.objects.create(
            name="Dashboard Warehouse",
        )
        cls.requested_stock = StockBalance.objects.create(
            material=Material.objects.order_by("-pk").first(),
            warehouse=cls.warehouse,
            quantity="12.000",
            replenishment_requested_at=timezone.now(),
            replenishment_requested_by=cls.user,
        )
        StockBalance.objects.create(
            material=Material.objects.order_by("pk").first(),
            warehouse=cls.warehouse,
            quantity="4.000",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_dashboard_uses_real_counts_and_recent_data(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["material_count"], 6)
        self.assertEqual(response.context["category_count"], 1)
        self.assertEqual(response.context["warehouse_count"], 1)
        self.assertEqual(response.context["replenishment_count"], 1)
        self.assertQuerySetEqual(
            response.context["recent_materials"],
            Material.objects.order_by("-pk")[:5],
        )
        self.assertQuerySetEqual(
            response.context["recent_replenishments"],
            [self.requested_stock],
        )

    def test_dashboard_renders_recent_related_details(self):
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, self.requested_stock.material.name)
        self.assertContains(response, self.category.name)
        self.assertContains(response, self.warehouse.name)
        self.assertContains(response, self.user.username)

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )


class CategoryImageFilterTests(TestCase):
    def test_known_category_uses_curated_image(self):
        category = Category(name="Sheet Goods")

        self.assertEqual(
            category_image(category),
            "lumberyard/images/public/category-sheet-materials.webp",
        )

    def test_unknown_category_uses_fallback_image(self):
        category = Category(name="Custom Timber Product")

        self.assertEqual(
            category_image(category),
            "lumberyard/images/public/category-mixed-timber.webp",
        )

    def test_known_material_uses_its_own_image(self):
        material = Material(sku="OAK-BOARD-25")

        self.assertEqual(
            material_image(material),
            "lumberyard/images/public/material-oak-board.webp",
        )

    def test_unknown_material_uses_its_category_image(self):
        category = Category(name="Sheet Goods")
        material = Material(sku="NEW-SHEET-001", category=category)

        self.assertEqual(
            material_image(material),
            "lumberyard/images/public/category-sheet-materials.webp",
        )

    def test_material_image_paths_point_to_static_files(self):
        for image_path in MATERIAL_IMAGES.values():
            with self.subTest(image_path=image_path):
                self.assertIsNotNone(finders.find(image_path))


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


class PublicMaterialDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name="Detail Test Boards",
        )
        cls.material = Material.objects.create(
            name="Detailed Oak Board",
            sku="DETAIL-OAK-001",
            category=cls.category,
            description="Public material description.",
            sale_price="42.50",
            species="Oak",
            grade="A",
            thickness_mm=25,
            width_mm=150,
            length_mm=3000,
        )

        warehouse = Warehouse.objects.create(
            name="Private Detail Warehouse",
        )
        StockBalance.objects.create(
            material=cls.material,
            warehouse=warehouse,
            quantity="91.125",
        )

        supplier = Supplier.objects.create(
            name="Private Detail Supplier",
        )
        MaterialSupplier.objects.create(
            material=cls.material,
            supplier=supplier,
            purchase_price="19.75",
            supplier_sku="PRIVATE-DETAIL-SKU",
        )

        cls.url = reverse(
            "public-material-detail",
            args=[cls.material.pk],
        )

    def test_detail_is_public_and_hides_internal_data(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "lumberyard/public_material_detail.html",
        )

        self.assertContains(response, self.material.name)
        self.assertContains(
            response,
            self.material.description,
        )
        self.assertContains(response, "Available")
        self.assertContains(response, "42.50")

        self.assertNotContains(response, "91.125")
        self.assertNotContains(
            response,
            "Private Detail Warehouse",
        )
        self.assertNotContains(
            response,
            "Private Detail Supplier",
        )
        self.assertNotContains(
            response,
            "PRIVATE-DETAIL-SKU",
        )
        self.assertNotContains(response, "19.75")

    def test_detail_shows_contact_us_without_stock(self):
        unavailable_material = Material.objects.create(
            name="Unavailable Test Board",
            sku="UNAVAILABLE-001",
            category=self.category,
        )

        response = self.client.get(
            reverse(
                "public-material-detail",
                args=[unavailable_material.pk],
            )
        )

        self.assertContains(response, "Contact us")


class PublicInformationPageTests(TestCase):
    def test_delivery_page_is_public(self):
        response = self.client.get(reverse("delivery"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "lumberyard/delivery.html",
        )
        self.assertContains(
            response,
            settings.PUBLIC_CONTACT["location"],
        )
        self.assertContains(
            response,
            reverse("contacts"),
        )

    def test_contacts_page_is_public(self):
        response = self.client.get(reverse("contacts"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "lumberyard/contacts.html",
        )
        self.assertContains(
            response,
            settings.PUBLIC_CONTACT["email"],
        )
        self.assertContains(
            response,
            settings.PUBLIC_CONTACT["location"],
        )

        for phone in settings.PUBLIC_CONTACT["phones"]:
            self.assertContains(response, phone["display"])
            self.assertContains(
                response,
                f'tel:{phone["href"]}',
            )
