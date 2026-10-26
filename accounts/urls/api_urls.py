from django.urls import path
from ..views import api_views

urlpatterns = [
    path("auth/hr/register/", api_views.hr_register, name="api-hr-register"),
    path("auth/hr/verify-otp/", api_views.hr_verify_otp, name="api-hr-verify-otp"),
    path("auth/login/", api_views.login, name="api-login"),
    path("auth/refresh/", api_views.refresh, name="api-refresh"),
    path("auth/logout/", api_views.logout, name="api-logout"),
]