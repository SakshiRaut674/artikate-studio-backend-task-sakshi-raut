from .context import set_current_tenant, clear_current_tenant
from .models import Tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = self._resolve_tenant(request)
        set_current_tenant(tenant)
        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant()
        return response

    def _resolve_tenant(self, request):
        header_id = request.headers.get("X-Tenant-ID")
        if header_id:
            return Tenant.objects.filter(id=header_id).first()
        host = request.get_host().split(":")[0]
        subdomain = host.split(".")[0]
        return Tenant.objects.filter(subdomain=subdomain).first()
