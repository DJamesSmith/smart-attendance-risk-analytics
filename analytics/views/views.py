from django.shortcuts import render
from organization.views import visible_employees
from .services import dashboard_summary


def dashboard(request):
    summary = dashboard_summary(visible_employees(request.user).filter(is_active=True))
    return render(request, "analytics/dashboard.html", {"summary": summary})


def api_docs(request):
    return render(request, "analytics/api_docs.html")