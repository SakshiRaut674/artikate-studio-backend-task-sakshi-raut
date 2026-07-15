import threading
_local = threading.local()

def set_current_tenant(tenant):
    _local.tenant = tenant

def get_current_tenant():
    return getattr(_local, "tenant", None)

def clear_current_tenant():
    if hasattr(_local, "tenant"):
        del _local.tenant
