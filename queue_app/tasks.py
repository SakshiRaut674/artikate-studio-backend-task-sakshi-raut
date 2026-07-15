"""
CELERY_TASK_ACKS_LATE=True means the broker only removes a task after it
returns successfully -- a SIGKILL'd worker never acked, so the task is
redelivered. See ANSWERS.md for the full SIGKILL discussion.
"""
import logging
from celery import shared_task
from django.utils import timezone
from .models import EmailJobLog
from .rate_limiter import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)
RATE_LIMIT_KEY = "email:rate_limit:sliding_window"
MAX_RETRIES = 5

def get_limiter():
    return SlidingWindowRateLimiter(key=RATE_LIMIT_KEY, limit=200, window_seconds=60)

class EmailSendError(Exception):
    pass

def _simulated_provider_send(recipient, subject, force_fail=False):
    if force_fail:
        raise EmailSendError(f"Simulated provider failure for {recipient}")
    return True

@shared_task(bind=True, max_retries=MAX_RETRIES)
def send_transactional_email(self, job_id, recipient, subject, force_fail=False):
    job = EmailJobLog.objects.get(id=job_id)
    job.attempts += 1
    job.save(update_fields=["attempts"])

    limiter = get_limiter()
    if not limiter.allow():
        job.status = "retrying"
        job.save(update_fields=["status"])
        raise self.retry(countdown=1, max_retries=1000)

    try:
        _simulated_provider_send(recipient, subject, force_fail=force_fail)
    except EmailSendError as exc:
        job.last_error = str(exc)
        job.status = "retrying"
        job.save(update_fields=["last_error", "status"])
        if self.request.retries >= MAX_RETRIES:
            job.status = "dead_letter"
            job.save(update_fields=["status"])
            logger.error("Job %s moved to dead-letter after %s attempts", job_id, job.attempts)
            return {"status": "dead_letter", "job_id": job_id}
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    job.status = "sent"
    job.updated_at = timezone.now()
    job.save(update_fields=["status", "updated_at"])
    return {"status": "sent", "job_id": job_id}
