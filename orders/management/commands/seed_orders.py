from django.core.management.base import BaseCommand
from orders.models import Customer, Order, OrderItem

class Command(BaseCommand):
    help = "Seeds one customer with 250 orders (each with 3 items)."
    def handle(self, *args, **options):
        customer, _ = Customer.objects.get_or_create(name="Regression Test Customer")
        Order.objects.filter(customer=customer).delete()
        orders = Order.objects.bulk_create([Order(customer=customer, total_amount=100+i) for i in range(250)])
        items = []
        for order in orders:
            for j in range(3):
                items.append(OrderItem(order=order, sku=f"SKU-{j}", quantity=1, price=10+j))
        OrderItem.objects.bulk_create(items)
        self.stdout.write(self.style.SUCCESS(f"Seeded customer_id={customer.id} with {len(orders)} orders and {len(items)} items."))
