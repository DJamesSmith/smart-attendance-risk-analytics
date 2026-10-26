from collections import Counter
from datetime import timedelta

from django.db.models import Count, Max, Q
from django.utils import timezone

from attendance.models import AttendanceCorrection, AttendanceLog
from attendance.services import build_daily_rows
from leaves.models import LeaveRequest

from .models import RiskScore

WINDOW_DAYS = 30
OPEN_CORRECTIONS = (AttendanceCorrection.Status.PENDING, AttendanceCorrection.Status.MANAGER_APPROVED)


def analysis_window():
    latest = AttendanceLog.objects.aggregate(latest=Max("punch_date"))["latest"]
    end = latest or timezone.localdate()
    return end - timedelta(days=WINDOW_DAYS - 1), end


def latest_risk_scores(employees):
    return (
        RiskScore.objects.filter(employee__in=employees)
        .select_related("employee__user", "employee__department")
        .order_by("employee_id", "-calculated_at")
        .distinct("employee_id")
    )


def dashboard_summary(employees):
    start, end = analysis_window()
    logs = AttendanceLog.objects.filter(employee__in=employees, punch_date__range=(start, end)).select_related(
        "employee__user", "employee__department", "shift_rule"
    )
    late_by_department = Counter(row["department"] for row in build_daily_rows(logs) if row["status"] == "LATE")

    departments = (
        employees.values("department__name")
        .annotate(
            pending_corrections=Count("correction_requests", filter=Q(correction_requests__status__in=OPEN_CORRECTIONS), distinct=True),
            leaves=Count(
                "leave_requests",
                filter=Q(leave_requests__status=LeaveRequest.Status.APPROVED, leave_requests__start_date__lte=end, leave_requests__end_date__gte=start),
                distinct=True,
            ),
        )
        .order_by("department__name")
    )
    department_rows = [
        {
            "name": row["department__name"],
            "late": late_by_department.get(row["department__name"], 0),
            "pending_corrections": row["pending_corrections"],
            "leaves": row["leaves"],
        }
        for row in departments
    ]

    high_risk = [score for score in latest_risk_scores(employees) if score.risk_level == RiskScore.RiskLevel.HIGH]
    return {
        "window_start": start,
        "window_end": end,
        "departments": department_rows,
        "totals": {
            "late": sum(row["late"] for row in department_rows),
            "pending_corrections": sum(row["pending_corrections"] for row in department_rows),
            "leaves": sum(row["leaves"] for row in department_rows),
        },
        "high_risk": sorted(high_risk, key=lambda score: -score.score),
    }