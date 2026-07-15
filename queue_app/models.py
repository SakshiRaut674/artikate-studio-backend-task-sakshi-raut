from django.db import models

class EmailJobLog(models.Model):
    STATUS_CHOICES = [("queued","queued"),("sent","sent"),("retrying","retrying"),("dead_letter","dead_letter")]
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
