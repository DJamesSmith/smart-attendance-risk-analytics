from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsHRAdmin
from accounts.utils import api_response, form_errors, get_employee_profile, is_hr, is_manager

from attendance.forms import AttendanceCorrectionForm, HRFinalizeForm, ManagerReviewForm
from attendance.models import AttendanceCorrection, AttendanceImportBatch
from attendance.serializers import AttendanceCorrectionSerializer, ImportBatchSerializer
from attendance.services import apply_correction
from .views import can_finalize, can_manager_review, can_view_correction, get_correction

INVALID_INPUT = "Please correct the errors below."


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsHRAdmin])
def import_list(request):
    batches = AttendanceImportBatch.objects.select_related("uploaded_by")[:100]
    data = ImportBatchSerializer(batches, many=True).data
    return api_response("success", f"{len(data)} imports found.", data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsHRAdmin])
def import_detail(request, pk):
    batch = get_object_or_404(AttendanceImportBatch.objects.select_related("uploaded_by"), pk=pk)
    return api_response("success", f"Import is {batch.get_status_display().lower()}.", data=ImportBatchSerializer(batch).data)


def visible_corrections(user):
    corrections = AttendanceCorrection.objects.select_related(
        "attendance_log", "requested_by__user", "manager_reviewed_by", "reviewed_by"
    )
    if is_hr(user):
        return corrections
    profile = get_employee_profile(user)
    if is_manager(user):
        return corrections.filter(Q(requested_by__manager=profile) | Q(requested_by=profile))
    return corrections.filter(requested_by=profile)


@api_view(["GET", "POST"])
def correction_list(request):
    if request.method == "GET":
        data = AttendanceCorrectionSerializer(visible_corrections(request.user)[:200], many=True).data
        return api_response("success", f"{len(data)} corrections found.", data=data)

    profile = get_employee_profile(request.user)
    if profile is None:
        return api_response("error", "Only users with an employee profile can raise corrections.", http_status=http.HTTP_403_FORBIDDEN)

    form = AttendanceCorrectionForm(request.data, employee=profile)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    correction = form.save(commit=False)
    correction.requested_by = profile
    correction.save()
    return api_response("success", "Correction submitted to your manager.", data=AttendanceCorrectionSerializer(correction).data, http_status=http.HTTP_201_CREATED)


@api_view(["GET"])
def correction_detail(request, pk):
    correction = get_correction(pk)
    if not can_view_correction(request.user, correction):
        return api_response("error", "You cannot view this correction.", http_status=http.HTTP_403_FORBIDDEN)
    return api_response("success", "Correction loaded.", data=AttendanceCorrectionSerializer(correction).data)


@api_view(["POST"])
def correction_manager_review(request, pk):
    correction = get_correction(pk)
    if not can_manager_review(request.user, correction):
        return api_response("error", "Only the employee's manager can review a pending correction.", http_status=http.HTTP_403_FORBIDDEN)

    form = ManagerReviewForm(request.data, instance=correction)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    approved = form.cleaned_data["decision"] == "approve"
    correction = form.save(commit=False)
    correction.status = AttendanceCorrection.Status.MANAGER_APPROVED if approved else AttendanceCorrection.Status.MANAGER_REJECTED
    correction.manager_reviewed_by = request.user
    correction.save()
    message = "Approved and sent to HR for finalization." if approved else "Correction rejected."
    return api_response("success", message, data=AttendanceCorrectionSerializer(correction).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsHRAdmin])
def correction_finalize(request, pk):
    correction = get_correction(pk)
    if not can_finalize(request.user, correction):
        return api_response("error", "This correction is not waiting for HR finalization.", http_status=http.HTTP_400_BAD_REQUEST)

    form = HRFinalizeForm(request.data, instance=correction)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    approved = form.cleaned_data["decision"] == "approve"
    with transaction.atomic():
        correction = form.save(commit=False)
        correction.status = AttendanceCorrection.Status.FINALIZED if approved else AttendanceCorrection.Status.HR_REJECTED
        correction.reviewed_by = request.user
        correction.save()
        if approved:
            apply_correction(correction)

    message = "Correction finalized and attendance updated." if approved else "Correction rejected by HR."
    return api_response("success", message, data=AttendanceCorrectionSerializer(correction).data)