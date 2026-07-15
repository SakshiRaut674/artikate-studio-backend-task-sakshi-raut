from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from .models import Customer, Order, OrderItem

class OrdersSummaryQueryCountTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Test Customer")
        orders = Order.objects.bulk_create([Order(customer=self.customer, total_amount=10+i) for i in range(250)])
        items = [OrderItem(order=o, sku="SKU-1", quantity=1, price=5) for o in orders]
        OrderItem.objects.bulk_create(items)
        self.client = Client()

    def test_broken_view_has_n_plus_one_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(f"/api/orders/summary/broken/?customer_id={self.customer.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 250)
        app_q = [q for q in ctx.captured_queries if "orders_order" in q["sql"] or "orders_customer" in q["sql"]]
        self.assertGreater(len(app_q), 500)

    def test_fixed_view_has_constant_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(f"/api/orders/summary/?customer_id={self.customer.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 250)
        app_q = [q for q in ctx.captured_queries if "orders_order" in q["sql"] or "orders_customer" in q["sql"]]
        self.assertLessEqual(len(app_q), 6)
