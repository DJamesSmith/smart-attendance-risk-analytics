from rest_framework.permissions import SAFE_METHODS, BasePermission

from .utils import is_hr


class IsHRAdmin(BasePermission):
    message = "Only HR Admins can do this."

    def has_permission(self, request, view):
        return is_hr(request.user)


class IsHROrReadOnly(BasePermission):
    message = "Only HR Admins can change this."

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or is_hr(request.user)