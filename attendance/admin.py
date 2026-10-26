from django.contrib import admin
from .models import AttendanceCorrection, AttendanceImportBatch, AttendanceLog


@admin.register(AttendanceImportBatch)
class AttendanceImportBatchAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "uploaded_by", "status", "total_rows", "processed_rows", "created_at")
    list_filter = ("status", ("created_at", admin.DateFieldListFilter))
    search_fields = ("original_filename", "uploaded_by__username", "uploaded_by__email")
    readonly_fields = ("status", "total_rows", "processed_rows", "error_message", "created_at", "started_at", "completed_at")
    list_select_related = ("uploaded_by",)
    fieldsets = (
        ("File", {"fields": ("uploaded_by", "original_filename", "file")}),
        ("Processing", {"fields": ("status", "total_rows", "processed_rows", "error_message")}),
        ("Timeline", {"fields": ("created_at", "started_at", "completed_at")}),)


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ("employee", "department", "punch_date", "punch_time", "punch_type", "device_location")
    list_filter = ("punch_type", ("punch_date", admin.DateFieldListFilter), "employee__department", "shift_rule")
    search_fields = ("employee__employee_code", "employee__user__first_name", "employee__user__last_name")
    date_hierarchy = "punch_date"
    readonly_fields = ("import_batch", "created_at")
    list_select_related = ("employee__user", "employee__department")
    fieldsets = (
        ("Employee", {"fields": ("employee", "shift_rule")}),
        ("Punch", {"fields": ("punch_date", "punch_time", "punch_type", "device_location", "remarks")}),
        ("Source", {"fields": ("import_batch", "created_at")}),)

    @admin.display(description="Department", ordering="employee__department__name")
    def department(self, obj):
        return obj.employee.department


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = ("id", "requested_by", "correction_type", "attendance_log", "status", "manager_reviewed_by", "reviewed_by", "created_at")
    list_filter = ("status", "correction_type", "requested_by__department", ("created_at", admin.DateFieldListFilter))
    search_fields = ("requested_by__employee_code", "requested_by__user__first_name", "requested_by__user__last_name")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("requested_by__user", "attendance_log", "manager_reviewed_by", "reviewed_by")
    fieldsets = (
        ("Request", {"fields": ("requested_by", "attendance_log", "correction_type", "requested_punch_date", "requested_punch_time", "reason")}),
        ("Manager review", {"fields": ("manager_reviewed_by", "manager_remarks")}),
        ("HR finalization", {"fields": ("status", "reviewed_by", "reviewer_remarks")}),
        ("Timeline", {"fields": ("created_at", "updated_at")}),)