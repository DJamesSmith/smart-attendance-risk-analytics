from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.utils import get_employee_profile, is_hr, is_manager
from leaves.models import LeaveRequest

from .forms import (
    AttendanceCorrectionForm,
    AttendanceUploadForm,
    DailyAttendanceFilterForm,
    HRFinalizeForm,
    ManagerReviewForm,
)
from .models import AttendanceCorrection, AttendanceImportBatch, AttendanceLog
from .services import apply_correction, build_daily_rows, import_attendance_file, read_report, report_links

DEPARTMENT_COOKIE = "last_department"
DATE_SESSION_KEY = "selected_attendance_date"
COOKIE_AGE = 60 * 60 * 24 * 30


def attendance_upload(request):
    form = AttendanceUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        batch = form.save(commit=False)
        batch.uploaded_by = request.user
        batch.original_filename = request.FILES["file"].name
        batch.save()
        import_attendance_file(batch)
        if batch.status == AttendanceImportBatch.Status.COMPLETED:
            messages.success(request, f"Imported {batch.processed_rows} new punches from {batch.original_filename}.")
        else:
            messages.error(request, f"Import failed: {batch.error_message}")
        return redirect("attendance:batch_detail", pk=batch.pk)

    recent_batches = AttendanceImportBatch.objects.select_related("uploaded_by")[:5]
    return render(request, "attendance/upload.html", {"form": form, "recent_batches": recent_batches})


def batch_list(request):
    batches = AttendanceImportBatch.objects.select_related("uploaded_by")
    status = request.GET.get("status", "")
    if status:
        batches = batches.filter(status=status)
    context = {"batches": batches[:100], "statuses": AttendanceImportBatch.Status.choices, "selected_status": status}
    return render(request, "attendance/batch_list.html", context)


def batch_detail(request, pk):
    batch = get_object_or_404(AttendanceImportBatch.objects.select_related("uploaded_by"), pk=pk)
    context = {
        "batch": batch,
        "reports": report_links(batch),
        "anomalies": read_report(batch, "anomaly_report.csv"),
        "corrections_needed": read_report(batch, "correction_required.csv"),
    }
    return render(request, "attendance/batch_detail.html", context)


def default_attendance_date():
    latest = AttendanceLog.objects.aggregate(latest=Max("punch_date"))["latest"]
    return latest or date.today()


def daily_attendance_list(request):
    if "date" in request.GET or "department" in request.GET:
        form = DailyAttendanceFilterForm(request.GET)
    else:
        initial = {
            "date": request.session.get(DATE_SESSION_KEY) or default_attendance_date(),
            "department": request.COOKIES.get(DEPARTMENT_COOKIE, ""),
        }
        form = DailyAttendanceFilterForm(initial)

    selected_date = default_attendance_date()
    department = None
    if form.is_valid():
        selected_date = form.cleaned_data["date"] or selected_date
        department = form.cleaned_data["department"]

    request.session[DATE_SESSION_KEY] = selected_date.isoformat()

    logs = AttendanceLog.objects.filter(punch_date=selected_date).select_related(
        "employee__user", "employee__department", "shift_rule"
    )
    leaves = LeaveRequest.objects.filter(
        status=LeaveRequest.Status.APPROVED, start_date__lte=selected_date, end_date__gte=selected_date
    ).select_related("employee__user", "employee__department")

    if department:
        logs = logs.filter(employee__department=department)
        leaves = leaves.filter(employee__department=department)
    if is_manager(request.user):
        profile = get_employee_profile(request.user)
        logs = logs.filter(employee__manager=profile)
        leaves = leaves.filter(employee__manager=profile)

    rows = build_daily_rows(logs, [(leave, selected_date) for leave in leaves])
    statuses = ("PRESENT", "LATE", "MISSING_PUNCH", "ON_LEAVE")
    status_counts = {status: len([row for row in rows if row["status"] == status]) for status in statuses}

    context = {"form": form, "rows": rows, "selected_date": selected_date, "department": department, "status_counts": status_counts}
    response = render(request, "attendance/daily_list.html", context)
    if "department" in request.GET:
        response.set_cookie(DEPARTMENT_COOKIE, department.pk if department else "", max_age=COOKIE_AGE, samesite="Lax")
    return response


def can_view_correction(user, correction):
    profile = get_employee_profile(user)
    requester = correction.requested_by
    return is_hr(user) or requester == profile or (profile is not None and requester.manager_id == profile.pk)


def can_manager_review(user, correction):
    if correction.status != AttendanceCorrection.Status.PENDING:
        return False
    profile = get_employee_profile(user)
    requester = correction.requested_by
    if profile is not None and requester.manager_id == profile.pk:
        return True
    return is_hr(user) and requester.manager_id is None


def can_finalize(user, correction):
    return is_hr(user) and correction.status == AttendanceCorrection.Status.MANAGER_APPROVED


def correction_list(request):
    corrections = AttendanceCorrection.objects.select_related(
        "attendance_log", "requested_by__user", "requested_by__department"
    )
    profile = get_employee_profile(request.user)
    if is_manager(request.user):
        corrections = corrections.filter(Q(requested_by__manager=profile) | Q(requested_by=profile))
    elif not is_hr(request.user):
        corrections = corrections.filter(requested_by=profile)

    status = request.GET.get("status", "")
    if status:
        corrections = corrections.filter(status=status)

    context = {
        "corrections": corrections[:200],
        "statuses": AttendanceCorrection.Status.choices,
        "selected_status": status,
        "can_create": profile is not None,
    }
    return render(request, "attendance/correction_list.html", context)


def correction_create(request):
    profile = get_employee_profile(request.user)
    if profile is None:
        messages.error(request, "Only users with an employee profile can raise corrections.")
        return redirect("attendance:correction_list")

    initial = {"attendance_log": request.GET.get("log")}
    form = AttendanceCorrectionForm(request.POST or None, employee=profile, initial=initial)
    if request.method == "POST" and form.is_valid():
        correction = form.save(commit=False)
        correction.requested_by = profile
        correction.save()
        messages.success(request, "Correction request submitted to your manager.")
        return redirect("attendance:correction_detail", pk=correction.pk)

    return render(request, "attendance/correction_form.html", {"form": form, "title": "Raise attendance correction"})


def get_own_pending_correction(request, pk):
    correction = get_object_or_404(AttendanceCorrection, pk=pk)
    is_owner = correction.requested_by == get_employee_profile(request.user)
    if not is_owner or correction.status != AttendanceCorrection.Status.PENDING:
        return None
    return correction


def correction_update(request, pk):
    correction = get_own_pending_correction(request, pk)
    if correction is None:
        messages.error(request, "Only your own pending corrections can be edited.")
        return redirect("attendance:correction_list")

    form = AttendanceCorrectionForm(request.POST or None, instance=correction, employee=correction.requested_by)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Correction request updated.")
        return redirect("attendance:correction_detail", pk=correction.pk)

    return render(request, "attendance/correction_form.html", {"form": form, "title": f"Edit correction #{correction.pk}"})


def correction_delete(request, pk):
    correction = get_own_pending_correction(request, pk)
    if correction is None:
        messages.error(request, "Only your own pending corrections can be deleted.")
        return redirect("attendance:correction_list")

    if request.method == "POST":
        correction.delete()
        messages.success(request, "Correction request deleted.")
        return redirect("attendance:correction_list")

    return render(request, "attendance/correction_confirm_delete.html", {"correction": correction})


def render_correction_detail(request, correction, manager_form=None, hr_form=None, status=200):
    context = {
        "correction": correction,
        "can_edit": correction.requested_by == get_employee_profile(request.user)
        and correction.status == AttendanceCorrection.Status.PENDING,
        "manager_form": manager_form or (ManagerReviewForm() if can_manager_review(request.user, correction) else None),
        "hr_form": hr_form or (HRFinalizeForm() if can_finalize(request.user, correction) else None),
    }
    return render(request, "attendance/correction_detail.html", context, status=status)


def get_correction(pk):
    queryset = AttendanceCorrection.objects.select_related(
        "attendance_log__employee", "requested_by__user", "requested_by__manager__user", "manager_reviewed_by", "reviewed_by"
    )
    return get_object_or_404(queryset, pk=pk)


def correction_detail(request, pk):
    correction = get_correction(pk)
    if not can_view_correction(request.user, correction):
        return render(request, "403.html", status=403)
    return render_correction_detail(request, correction)


@require_POST
def correction_manager_review(request, pk):
    correction = get_correction(pk)
    if not can_manager_review(request.user, correction):
        messages.error(request, "You cannot review this correction.")
        return redirect("attendance:correction_detail", pk=pk)

    form = ManagerReviewForm(request.POST, instance=correction)
    if not form.is_valid():
        return render_correction_detail(request, correction, manager_form=form, status=400)

    correction = form.save(commit=False)
    approved = form.cleaned_data["decision"] == "approve"
    correction.status = AttendanceCorrection.Status.MANAGER_APPROVED if approved else AttendanceCorrection.Status.MANAGER_REJECTED
    correction.manager_reviewed_by = request.user
    correction.save()
    messages.success(request, "Sent to HR for finalization." if approved else "Correction rejected.")
    return redirect("attendance:correction_detail", pk=pk)


@require_POST
def correction_finalize(request, pk):
    correction = get_correction(pk)
    if not can_finalize(request.user, correction):
        messages.error(request, "This correction is not waiting for HR finalization.")
        return redirect("attendance:correction_detail", pk=pk)

    form = HRFinalizeForm(request.POST, instance=correction)
    if not form.is_valid():
        return render_correction_detail(request, correction, hr_form=form, status=400)

    approved = form.cleaned_data["decision"] == "approve"
    with transaction.atomic():
        correction = form.save(commit=False)
        correction.status = AttendanceCorrection.Status.FINALIZED if approved else AttendanceCorrection.Status.HR_REJECTED
        correction.reviewed_by = request.user
        correction.save()
        if approved:
            apply_correction(correction)

    messages.success(request, "Correction finalized and attendance updated." if approved else "Correction rejected by HR.")
    return redirect("attendance:correction_detail", pk=pk)