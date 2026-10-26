from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.utils import get_employee_profile, is_hr, is_manager, json_response
from attendance.models import AttendanceCorrection, AttendanceLog
from attendance.processor import EMPLOYEE_CODE_PATTERN
from attendance.services import build_daily_rows
from leaves.models import LeaveRequest

from .models import Department, Employee
from .serializers import EmployeeLookupSerializer

CLOSED_CORRECTIONS = (
    AttendanceCorrection.Status.FINALIZED,
    AttendanceCorrection.Status.HR_REJECTED,
    AttendanceCorrection.Status.MANAGER_REJECTED,
)


def visible_employees(user):
    employees = Employee.objects.select_related("user", "department", "manager__user")
    if is_hr(user):
        return employees
    profile = get_employee_profile(user)
    if is_manager(user):
        return employees.filter(Q(manager=profile) | Q(pk=getattr(profile, "pk", None)))
    return employees.filter(pk=getattr(profile, "pk", None))


def employee_list(request):
    employees = visible_employees(request.user)
    search = request.GET.get("q", "").strip()
    department_id = request.GET.get("department", "")
    if search:
        employees = employees.filter(
            Q(employee_code__icontains=search) | Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search)
        )
    if department_id.isdigit():
        employees = employees.filter(department_id=department_id)

    context = {
        "employees": employees.order_by("employee_code")[:200],
        "departments": Department.objects.filter(is_active=True),
        "search": search,
        "selected_department": department_id,
    }
    return render(request, "organization/employee_list.html", context)


def employee_detail(request, employee_code):
    employee = get_object_or_404(visible_employees(request.user), employee_code=employee_code.upper())
    since = timezone.localdate() - timedelta(days=30)

    logs = AttendanceLog.objects.filter(employee=employee, punch_date__gte=since).select_related(
        "employee__user", "employee__department", "shift_rule"
    )
    daily_rows = build_daily_rows(logs)
    daily_rows.reverse()

    context = {
        "employee": employee,
        "daily_rows": daily_rows,
        "anomaly_rows": [row for row in daily_rows if row["status"] != "PRESENT"],
        "open_corrections": employee.correction_requests.exclude(status__in=CLOSED_CORRECTIONS).select_related("attendance_log"),
        "leaves": employee.leave_requests.order_by("-start_date")[:10],
        "is_self": employee == get_employee_profile(request.user),
    }
    return render(request, "organization/employee_detail.html", context)


def employee_lookup(request):
    code = request.GET.get("code", "").strip().upper()
    if not EMPLOYEE_CODE_PATTERN.match(code):
        return json_response("error", "Invalid employee code.", errors={"code": ["Use a code like EMP1001."]}, http_status=400)

    try:
        employee = visible_employees(request.user).get(employee_code=code)
    except Employee.DoesNotExist:
        return json_response("error", "Employee not found.", errors={"code": [f"No employee with code {code}."]}, http_status=404)

    data = EmployeeLookupSerializer(employee).data
    data["recent_punches"] = list(
        AttendanceLog.objects.filter(employee=employee)
        .order_by("-punch_date", "-punch_time")
        .values("punch_date", "punch_time", "punch_type", "device_location")[:5]
    )
    data["open_corrections"] = employee.correction_requests.exclude(status__in=CLOSED_CORRECTIONS).count()
    data["pending_leaves"] = employee.leave_requests.filter(status=LeaveRequest.Status.PENDING).count()
    return json_response("success", "Employee found.", data=data)


def employee_attendance_json(request, employee_code):
    try:
        employee = visible_employees(request.user).get(employee_code=employee_code.upper())
    except Employee.DoesNotExist:
        return json_response("error", "Employee not found.", errors={"employee_code": ["Not found or not visible to you."]}, http_status=404)

    end_date = parse_date(request.GET.get("end", "")) or timezone.localdate()
    start_date = parse_date(request.GET.get("start", "")) or end_date - timedelta(days=30)
    if start_date > end_date:
        return json_response("error", "Invalid date range.", errors={"start": ["Start date must be before end date."]}, http_status=400)

    logs = AttendanceLog.objects.filter(employee=employee, punch_date__range=(start_date, end_date)).select_related(
        "employee__user", "employee__department", "shift_rule"
    )
    anomalies = [row for row in build_daily_rows(logs) if row["status"] != "PRESENT" or row["early_exit_minutes"]]
    data = {
        "employee_code": employee.employee_code,
        "start": start_date,
        "end": end_date,
        "punches": list(logs.order_by("punch_date", "punch_time").values("id", "punch_date", "punch_time", "punch_type", "device_location", "remarks")),
        "anomalies": anomalies,
    }
    return json_response("success", "Attendance details loaded.", data=data)