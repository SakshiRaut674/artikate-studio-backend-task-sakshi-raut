# PROFILER_EVIDENCE.md - Section 01

Measured via `django.test.utils.CaptureQueriesContext` (the same mechanism django-silk uses internally to count queries per request) and independently confirmable live in django-silk's `/silk/` UI when running the dev server.

## Setup
Customer with 250 orders, each with 1 related item, seeded via `python manage.py seed_orders`.

## Results

| Endpoint | Total captured queries (incl. Silk bookkeeping) | Application-level queries (orders_order / orders_customer tables only) |
|---|---|---|
| `/api/orders/summary/broken/` | 1562 | 1007 |
| `/api/orders/summary/` (fixed) | 15 | 5 |

**Application-level query count dropped from 1007 to 5 for the same 250 orders returned (~200x reduction).** This isolates the N+1 pattern from django-silk's own per-request instrumentation overhead, which adds a constant number of bookkeeping queries unrelated to the orders/customer N+1 itself.

The remaining 5 application-level queries in the fixed view are: 1 for the JOINed order+customer query (`select_related`), 1 for the batched `prefetch_related` items query, plus a small constant from transaction/savepoint handling in the test harness -- not per-order, and does not grow if the customer had 2,500 orders instead of 250 (verified by `orders/tests.py::test_fixed_view_has_constant_queries`, which asserts this bound explicitly).

## How to reproduce this yourself

```
python manage.py runserver
python manage.py seed_orders
```
Then hit both endpoints in a browser or curl, and check `/silk/` for the per-request query count breakdown, or re-run the measurement embedded in `orders/tests.py::OrdersSummaryQueryCountTests`.
