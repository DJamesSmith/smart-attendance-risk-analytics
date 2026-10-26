from django.shortcuts import get_object_or_404
from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsHROrReadOnly
from accounts.utils import api_response, form_errors

from .forms import DepartmentForm
from .models import Department
from .serializers import DepartmentSerializer, EmployeeLookupSerializer
from .views import visible_employees

INVALID_INPUT = "Please correct the errors below."


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsHROrReadOnly])
def department_list(request):
    if request.method == "GET":
        departments = Department.objects.order_by("name")
        data = DepartmentSerializer(departments, many=True, context={"request": request}).data
        return api_response("success", f"{len(data)} departments found.", data=data)

    form = DepartmentForm(request.data)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)
    department = form.save()
    data = DepartmentSerializer(department, context={"request": request}).data
    return api_response("success", "Department created.", data=data, http_status=http.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated, IsHROrReadOnly])
def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == "GET":
        data = DepartmentSerializer(department, context={"request": request}).data
        return api_response("success", "Department loaded.", data=data)

    if request.method == "PUT":
        form = DepartmentForm(request.data, instance=department)
        if not form.is_valid():
            return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)
        department = form.save()
        data = DepartmentSerializer(department, context={"request": request}).data
        return api_response("success", "Department updated.", data=data)

    if department.employees.exists():
        message = "This department still has employees. Move them or mark the department inactive instead."
        return api_response("error", message, errors={"department": [message]}, http_status=http.HTTP_400_BAD_REQUEST)
    department.delete()
    return api_response("success", "Department deleted.")


@api_view(["GET"])
def employee_list(request):
    employees = visible_employees(request.user).order_by("employee_code")
    data = EmployeeLookupSerializer(employees, many=True).data
    return api_response("success", f"{len(data)} employees found.", data=data)