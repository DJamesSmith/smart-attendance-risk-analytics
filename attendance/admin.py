from django.contrib import admin
from .models import AttendanceCorrection, AttendanceImportBatch, AttendanceLog


@admin.register(AttendanceImportBatch)
class AttendanceImportBatchAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "uploaded_by", "status", "total_rows", "processed_rows", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("original_filename", "uploaded_by__username", "uploaded_by__email")
    readonly_fields = ("status", "total_rows", "processed_rows", "error_message", "created_at", "started_at", "completed_at")


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ("employee", "punch_date", "punch_time", "punch_type", "device_location")
    list_filter = ("punch_type", "punch_date", "employee__department")
    search_fields = ("employee__employee_code", "employee__user__first_name", "employee__user__last_name")
    date_hierarchy = "punch_date"
    readonly_fields = ("created_at",)


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = ("attendance_log", "requested_by", "status", "reviewed_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("attendance_log__employee__employee_code", "requested_by__employee_code")
    readonly_fields = ("created_at", "updated_at")