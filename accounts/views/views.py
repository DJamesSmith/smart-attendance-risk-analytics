from django.contrib import messages
from django.contrib.auth import login, logout
from ..forms import LoginForm, RegistrationForm, find_claimable_user
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from ..utils import get_employee_profile, is_hr, is_manager


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.GET.get("next", "")
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("accounts:home")

    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    claimable_user = None
    if request.method == "POST":
        claimable_user = find_claimable_user(request.POST.get("employee_code", ""))

    form = RegistrationForm(request.POST or None, instance=claimable_user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.first_name}! Your account is ready.")
        return redirect("accounts:home")

    return render(request, "accounts/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


def home(request):
    if is_hr(request.user) or is_manager(request.user):
        return redirect("attendance:daily_list")

    profile = get_employee_profile(request.user)
    if profile:
        return redirect("organization:employee_detail", employee_code=profile.employee_code)

    return render(request, "accounts/home.html")