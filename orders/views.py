"""
Section 01 - N+1 root cause: each order in the loop triggers
order.items.count() and order.customer.name lazily -- one query each,
per order.
"""
from django.http import JsonResponse
from .models import Order

def orders_summary_broken(request):
    customer_id = request.GET.get("customer_id")
    orders = Order.objects.filter(customer_id=customer_id)
    data = []
    for order in orders:
        item_count = order.items.count()
        customer_name = order.customer.name
        data.append({"id": order.id, "customer": customer_name,
                     "total_amount": str(order.total_amount), "item_count": item_count})
    return JsonResponse({"orders": data, "count": len(data)})

def orders_summary_fixed(request):
    customer_id = request.GET.get("customer_id")
    orders = (Order.objects.filter(customer_id=customer_id)
              .select_related("customer").prefetch_related("items"))
    data = []
    for order in orders:
        data.append({"id": order.id, "customer": order.customer.name,
                     "total_amount": str(order.total_amount), "item_count": len(order.items.all())})
    return JsonResponse({"orders": data, "count": len(data)})
