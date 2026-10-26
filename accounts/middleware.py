import logging
import time
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render

from .utils import get_role

audit_logger = logging.getLogger("audit")

PUBLIC_PATHS = ("/accounts/login/", "/accounts/register/", "/admin/", "/static/", "/api/")

ROLE_RULES = {
    "attendance:upload": ("HR_ADMIN",),
    "attendance:batch_list": ("HR_ADMIN",),
    "attendance:batch_detail": ("HR_ADMIN",),
    "attendance:daily_list": ("HR_ADMIN", "MANAGER"),
    "attendance:correction_manager_review": ("HR_ADMIN", "MANAGER"),
    "attendance:correction_finalize": ("HR_ADMIN",),
    "organization:employee_list": ("HR_ADMIN", "MANAGER"),
    "organization:employee_lookup": ("HR_ADMIN", "MANAGER"),
    "leaves:review": ("HR_ADMIN", "MANAGER"),
}


class RequestAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - started) * 1000
        user = request.user.username if request.user.is_authenticated else "anonymous"
        audit_logger.info(
            "%s %s user=%s status=%s ip=%s time=%.0fms",
            request.method, request.get_full_path(), user, response.status_code,
            request.META.get("REMOTE_ADDR", ""), duration_ms)
        return response


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith(PUBLIC_PATHS):
            return None

        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        allowed_roles = ROLE_RULES.get(request.resolver_match.view_name)
        if allowed_roles and get_role(request.user) not in allowed_roles:
            audit_logger.warning("BLOCKED %s user=%s role=%s", request.path, request.user.username, get_role(request.user))
            return render(request, "403.html", status=403)

        return None