# DESIGN.md - Section 02: Rate-Limited Async Job Queue

## Architecture choice: Celery + Redis vs Django-Q vs custom

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Celery + Redis** | Mature, battle-tested retry/backoff primitives (`self.retry`, `max_retries`, `countdown`); `acks_late` + `reject_on_worker_lost` give strong crash-safety guarantees out of the box; large ecosystem, well-documented failure modes | Heavier dependency footprint than a custom queue; requires running a separate worker process | **Chosen.** The brief explicitly requires crash-safety ("does not lose jobs if worker crashes") and retry/backoff -- reimplementing these correctly from scratch is exactly the over-engineering the brief warns against |
| **Django-Q** | Simpler setup, Django-native admin integration, can use ORM as broker (no separate Redis needed) | Smaller community/track record than Celery; ORM-as-broker mode adds DB write load per task, conflicting with the "2,000 requests in 10 seconds" burst scenario | Rejected -- the burst scenario specifically stresses a broker's queuing throughput; Redis-backed Celery is the stronger fit |
| **Custom (raw Redis lists as queue)** | Full control, minimal dependencies | Would require reimplementing retry logic, dead-letter handling, and crash-recovery semantics that Celery already provides correctly -- high risk of subtly wrong edge cases (e.g. losing a task between pop and processing) | Rejected -- directly conflicts with "Do not over-engineer. Readable code that solves the problem is the goal" |

## Rate limiter: sliding window (Option B)

See ANSWERS.md Section 02 for the full three-part justification (why this approach, atomicity guarantee, fail-open-vs-closed). Summary: chosen over token bucket because it gives an exact, boundary-safe guarantee for the brief's stated worst case (2,000-request burst in under 10 seconds); atomicity via a single Lua script executed with `EVAL`; fails closed on Redis failure, because exceeding the provider's 200/min cap risks account suspension.

## Dead-letter handling

After `MAX_RETRIES` (5) exhausted failures, `send_transactional_email` marks the job's status as `dead_letter` in `EmailJobLog` and logs the event, giving a persistent, queryable record of permanently-failed jobs instead of relying on Celery's own result backend, which may expire.

## What this design does not handle (acknowledged trade-off)

- No idempotency key on the simulated provider call -- a task that succeeds in sending but crashes before updating its own status to `sent` would be redelivered (per `acks_late`) and could send a duplicate email. Production fix: store and check an idempotency key per job.
- The rate limiter uses a single global Redis key, correct for the brief's single-provider-limit scenario, but would need per-tenant/per-provider keys for multiple providers with different limits.
