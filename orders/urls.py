from django.urls import path
from .views import orders_summary_broken, orders_summary_fixed
urlpatterns = [
    path("summary/", orders_summary_fixed, name="orders-summary"),
    path("summary/broken/", orders_summary_broken, name="orders-summary-broken"),
]
