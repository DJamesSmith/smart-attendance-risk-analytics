from django.urls import path
from organization.views import api_views

urlpatterns = [
    path("departments/", api_views.department_list, name="api-department-list"),
    path("departments/<int:pk>/", api_views.department_detail, name="api-department-detail"),
    path("employees/", api_views.employee_list, name="api-employee-list"),
]