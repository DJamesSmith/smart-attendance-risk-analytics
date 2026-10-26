from .utils import get_employee_profile, get_role


def role_context(request):
    if not request.user.is_authenticated:
        return {}
    return {"user_role": get_role(request.user), "user_profile": get_employee_profile(request.user)}