# Artikate Studio Backend Task

Django backend assessment covering four sections: N+1 diagnosis, a rate-limited async job queue, multi-tenant ORM isolation, and a written architecture review.

## Setup (under 5 minutes)

```bash
python -m venv venv
# Windows: venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py test orders queue_app tenants -v 2
```

Expected output: `Ran 9 tests ... OK`. This runs with zero external services (Celery in eager mode, fakeredis for the rate limiter) -- no Docker, Redis, or worker process required to pass the suite. See "Assumptions & Interpretations" in ANSWERS.md for why this interpretation was chosen, and confirmation this was also verified against real Redis.

## Project structure

- `orders/` -- Section 01 (N+1 diagnosis + fix + tests)
- `queue_app/` -- Section 02 (Celery + Redis job queue, rate limiter, tests)
- `tenants/` -- Section 03 (tenant-scoped Manager, middleware, tests)
- `ANSWERS.md` -- all written answers, Sections 01-04
- `DESIGN.md` -- Section 02 architecture reasoning
- `PROFILER_EVIDENCE.md` -- measured query-count evidence for Section 01

## Validating Section 01 (django-silk)

```bash
python manage.py runserver
python manage.py seed_orders
```
Then visit:
- `http://localhost:8000/api/orders/summary/broken/?customer_id=<id>` 
- `http://localhost:8000/api/orders/summary/?customer_id=<id>`
## replace <<id>> with number for example -->http://localhost:8000/api/orders/summary/broken/?customer_id=1

Check `http://localhost:8000/silk/` for per-request query counts. See PROFILER_EVIDENCE.md for the exact measured numbers.

## Validating Section 03 (tenant isolation) manually

```bash
python manage.py shell
```
```python
from tenants.models import Tenant, Order
from tenants.context import set_current_tenant
a = Tenant.objects.create(name="A", subdomain="a")
b = Tenant.objects.create(name="B", subdomain="b")
Order.all_tenants.create(tenant=b, reference="B-1", amount=1)
set_current_tenant(a)
Order.objects.all()  # empty -- proves isolation
```

## Real-Redis validation (Docker) -- optional, for Section 5 recording

Not required for the automated test suite above, but used for the optional Loom recording. This exact flow (both eager and non-eager modes) was verified to produce identical 9/9 passing results during development of this repo.

1. Start Redis:
   ```bash
   docker run -d --name redis -p 6379:6379 redis:7
   docker exec -it redis redis-cli ping   # expect PONG
   ```

2. Copy env file (no credentials needed -- default Redis has no password):
   ```bash
   cp .env.example .env
   ```

3. Disable eager mode:
   ```bash
   # Windows PowerShell:
   $env:CELERY_TASK_ALWAYS_EAGER = "0"
   # Mac/Linux:
   export CELERY_TASK_ALWAYS_EAGER=0
   ```

4. Re-run the test suite against real Redis (confirms identical 9/9 pass):
   ```bash
   python manage.py test orders queue_app tenants -v 2
   ```

5. Start a real Celery worker (separate terminal, same venv):
   ```bash
   celery -A backend_task worker -l info --pool=solo
   ```
   `--pool=solo` is required on Windows; Celery's default `prefork` pool is Linux/Mac only.

6. In a third terminal, submit real jobs:
   ```bash
   python manage.py shell
   ```
   ```python
   from queue_app.models import EmailJobLog
   from queue_app.tasks import send_transactional_email
   for i in range(250):
       job = EmailJobLog.objects.create(recipient=f"user{i}@example.com", subject="OTP")
       send_transactional_email.delay(job.id, job.recipient, job.subject)
   ```
   Watch the worker terminal for real Redis-backed throttling at 200/min.

7. Inspect rate-limiter state directly:
   ```bash
   docker exec -it redis redis-cli
   > ZCARD email:rate_limit:sliding_window
   ```


## Known limitation (documented, not hidden)

`self.retry()` in `queue_app/tasks.py` does not use an idempotency key. A task that succeeds in sending but crashes before updating its own status to `sent` could be redelivered and resend. See DESIGN.md for the production fix.

## Loom recording


