from django.contrib import admin

from .models import LeaveRequest


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status", "reviewed_by")
    list_filter = ("status", "leave_type", "employee__department", ("start_date", admin.DateFieldListFilter))
    search_fields = ("employee__employee_code", "employee__user__first_name", "employee__user__last_name")
    date_hierarchy = "start_date"
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("employee__user", "reviewed_by")
    fieldsets = (
        ("Request", {"fields": ("employee", "leave_type", "start_date", "end_date", "reason", "supporting_document")}),
        ("Review", {"fields": ("status", "reviewed_by", "reviewer_remarks")}),
        ("Timeline", {"fields": ("created_at", "updated_at")}),
    )