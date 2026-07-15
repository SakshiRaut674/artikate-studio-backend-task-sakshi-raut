from django.db import models
from .context import get_current_tenant

class Tenant(models.Model):
    name = models.CharField(max_length=120)
    subdomain = models.CharField(max_length=120, unique=True)
    def __str__(self):
        return self.name

class TenantManager(models.Manager):
    """Overrides get_queryset() -- the single choke point every manager
    method routes through. Fails CLOSED if no tenant is bound."""
    def get_queryset(self):
        tenant = get_current_tenant()
        qs = super().get_queryset()
        if tenant is None:
            return qs.none()
        return qs.filter(tenant=tenant)

class Order(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    reference = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    objects = TenantManager()
    all_tenants = models.Manager()
    def __str__(self):
        return self.reference
