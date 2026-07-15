from django.test import TestCase
from .models import Tenant, Order
from .context import set_current_tenant, clear_current_tenant

class TenantIsolationTests(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="A", subdomain="a")
        self.tenant_b = Tenant.objects.create(name="B", subdomain="b")
        self.order_a = Order.all_tenants.create(tenant=self.tenant_a, reference="A-1", amount=10)
        self.order_b = Order.all_tenants.create(tenant=self.tenant_b, reference="B-1", amount=20)

    def tearDown(self):
        clear_current_tenant()

    def test_tenant_a_sees_only_its_own_orders_via_all(self):
        set_current_tenant(self.tenant_a)
        visible = list(Order.objects.all())
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].reference, "A-1")

    def test_tenant_a_cannot_fetch_tenant_b_order_by_get(self):
        set_current_tenant(self.tenant_a)
        with self.assertRaises(Order.DoesNotExist):
            Order.objects.get(id=self.order_b.id)

    def test_no_tenant_bound_returns_empty_not_everything(self):
        clear_current_tenant()
        visible = list(Order.objects.all())
        self.assertEqual(visible, [])

    def test_switching_tenant_context_switches_visible_rows(self):
        set_current_tenant(self.tenant_a)
        self.assertEqual(list(Order.objects.all().values_list("reference", flat=True)), ["A-1"])
        set_current_tenant(self.tenant_b)
        self.assertEqual(list(Order.objects.all().values_list("reference", flat=True)), ["B-1"])
