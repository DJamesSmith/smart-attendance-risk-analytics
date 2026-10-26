from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.utils import get_employee_profile, is_hr, is_manager

from .forms import LeaveRequestForm, LeaveReviewForm
from .models import LeaveRequest


def can_review_leave(user, leave):
    if leave.status != LeaveRequest.Status.PENDING:
        return False
    profile = get_employee_profile(user)
    if profile is not None and leave.employee.manager_id == profile.pk:
        return True
    return is_hr(user) and leave.employee != profile


def leave_list(request):
    leaves = LeaveRequest.objects.select_related("employee__user", "employee__department", "reviewed_by")
    profile = get_employee_profile(request.user)
    if is_manager(request.user):
        leaves = leaves.filter(Q(employee__manager=profile) | Q(employee=profile))
    elif not is_hr(request.user):
        leaves = leaves.filter(employee=profile)

    status = request.GET.get("status", "")
    if status:
        leaves = leaves.filter(status=status)

    rows = [{"leave": leave, "can_review": can_review_leave(request.user, leave)} for leave in leaves[:200]]
    context = {
        "rows": rows,
        "statuses": LeaveRequest.Status.choices,
        "selected_status": status,
        "profile": profile,
    }
    return render(request, "leaves/leave_list.html", context)


def leave_create(request):
    profile = get_employee_profile(request.user)
    if profile is None:
        messages.error(request, "Only users with an employee profile can apply for leave.")
        return redirect("leaves:list")

    form = LeaveRequestForm(request.POST or None, request.FILES or None, employee=profile)
    if request.method == "POST" and form.is_valid():
        leave = form.save(commit=False)
        leave.employee = profile
        leave.save()
        messages.success(request, "Leave request submitted.")
        return redirect("leaves:list")

    return render(request, "leaves/leave_form.html", {"form": form})


@require_POST
def leave_review(request, pk):
    leave = get_object_or_404(LeaveRequest.objects.select_related("employee"), pk=pk)
    if not can_review_leave(request.user, leave):
        messages.error(request, "You cannot review this leave request.")
        return redirect("leaves:list")

    form = LeaveReviewForm(request.POST, instance=leave)
    if not form.is_valid():
        for errors in form.errors.values():
            messages.error(request, " ".join(errors))
        return redirect("leaves:list")

    leave = form.save(commit=False)
    approved = form.cleaned_data["decision"] == "approve"
    leave.status = LeaveRequest.Status.APPROVED if approved else LeaveRequest.Status.REJECTED
    leave.reviewed_by = request.user
    leave.save()
    messages.success(request, f"Leave request {leave.get_status_display().lower()}.")
    return redirect("leaves:list")


@require_POST
def leave_cancel(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk, employee=get_employee_profile(request.user))
    if leave.status != LeaveRequest.Status.PENDING:
        messages.error(request, "Only pending leave requests can be cancelled.")
        return redirect("leaves:list")

    leave.status = LeaveRequest.Status.CANCELLED
    leave.save(update_fields=["status", "updated_at"])
    messages.success(request, "Leave request cancelled.")
    return redirect("leaves:list")