from django.http import JsonResponse
from .models import User


def get_role(user):
    if user.is_superuser:
        return User.Role.HR_ADMIN
    return user.role


def is_hr(user):
    return user.is_authenticated and get_role(user) == User.Role.HR_ADMIN


def is_manager(user):
    return user.is_authenticated and get_role(user) == User.Role.MANAGER


def get_employee_profile(user):
    return getattr(user, "employee_profile", None)


def json_response(status, message, data=None, errors=None, http_status=200):
    payload = {"status": status, "message": message, "data": data, "errors": errors}
    return JsonResponse(payload, status=http_status)