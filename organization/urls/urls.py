from django.urls import path
from .. import views

app_name = "organization"

urlpatterns = [
    path("", views.employee_list, name="employee_list"),
    path("lookup/", views.employee_lookup, name="employee_lookup"),
    path("<str:employee_code>/", views.employee_detail, name="employee_detail"),
    path("<str:employee_code>/attendance.json", views.employee_attendance_json, name="employee_attendance_json"),
]