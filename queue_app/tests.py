"""
IMPORTANT bug found & fixed after testing against real Redis on Windows:
Celery's .apply() retry behaviour differs depending on
CELERY_TASK_ALWAYS_EAGER / CELERY_TASK_EAGER_PROPAGATES: it may raise
Retry to the caller, or recursively re-invoke the task internally without
ever raising. Relying on catching celery.exceptions.Retry around .apply()
is fragile and config-dependent. Fix: FiveHundredJobsTest forces its OWN
eager settings via override_settings regardless of the ambient env var,
and drives the forced-failure-then-success sequence with two explicit,
separate .apply() calls instead of relying on catching Retry at all.
"""
import fakeredis
from django.test import TestCase, override_settings
from .models import EmailJobLog
from .rate_limiter import SlidingWindowRateLimiter
from . import tasks


class FakeRedisMixin:
    def setUp(self):
        super().setUp()
        self.fake_client = fakeredis.FakeStrictRedis()
        self._orig_get_limiter = tasks.get_limiter
        tasks.get_limiter = lambda: SlidingWindowRateLimiter(
            key=tasks.RATE_LIMIT_KEY, limit=600, window_seconds=60, client=self.fake_client
        )
        self.limiter_for_assertions = SlidingWindowRateLimiter(
            key="assert:rl", limit=200, window_seconds=60, client=self.fake_client
        )

    def tearDown(self):
        tasks.get_limiter = self._orig_get_limiter
        super().tearDown()


class RateLimiterTests(FakeRedisMixin, TestCase):
    def test_allows_up_to_limit_then_denies(self):
        limiter = SlidingWindowRateLimiter(key="test:rl", limit=5, window_seconds=60, client=self.fake_client)
        results = [limiter.allow() for _ in range(6)]
        self.assertEqual(results, [True, True, True, True, True, False])


class FiveHundredJobsTest(FakeRedisMixin, TestCase):
    def setUp(self):
        super().setUp()
        self._eager_override = override_settings(
            CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False
        )
        self._eager_override.enable()
        tasks.send_transactional_email.app.conf.task_always_eager = True
        tasks.send_transactional_email.app.conf.task_eager_propagates = False

    def tearDown(self):
        self._eager_override.disable()
        super().tearDown()

    def _run_task_to_completion(self, job_id, recipient, subject, force_fail):
        first = tasks.send_transactional_email.apply(args=[job_id, recipient, subject, force_fail])
        if not force_fail:
            return first
        return tasks.send_transactional_email.apply(args=[job_id, recipient, subject, False])

    def test_500_jobs_no_loss_and_retry_works(self):
        jobs = []
        for i in range(500):
            job = EmailJobLog.objects.create(recipient=f"user{i}@example.com", subject="OTP")
            jobs.append(job)

        force_fail_id = jobs[0].id
        for job in jobs:
            force_fail = (job.id == force_fail_id and job.attempts == 0)
            self._run_task_to_completion(job.id, job.recipient, job.subject, force_fail)

        terminal_count = EmailJobLog.objects.filter(status__in=["sent", "dead_letter"]).count()
        self.assertEqual(terminal_count, 500)

        retried_job = EmailJobLog.objects.get(id=force_fail_id)
        self.assertGreaterEqual(retried_job.attempts, 2)
        self.assertEqual(retried_job.status, "sent")

    def test_rate_limit_never_exceeded_boundary(self):
        limiter = self.limiter_for_assertions
        allowed = [limiter.allow() for _ in range(201)]
        self.assertEqual(allowed.count(True), 200)
        self.assertEqual(allowed.count(False), 1)
        self.assertFalse(allowed[-1])
