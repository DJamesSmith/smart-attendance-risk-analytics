from django.conf import settings
from django.db import models


class AttendanceImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="attendance_import_batches")
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="attendance/imports/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.original_filename} ({self.status})"


class AttendanceLog(models.Model):
    class PunchType(models.TextChoices):
        IN = "IN", "In"
        OUT = "OUT", "Out"

    employee = models.ForeignKey("organization.Employee", on_delete=models.PROTECT, related_name="attendance_logs")
    import_batch = models.ForeignKey(AttendanceImportBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_logs")
    punch_date = models.DateField()
    punch_time = models.TimeField()
    device_location = models.CharField(max_length=150, blank=True)
    punch_type = models.CharField(max_length=10, choices=PunchType.choices)
    shift_rule = models.ForeignKey("organization.ShiftRule", on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_logs")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-punch_date", "-punch_time")
        constraints = [
            models.UniqueConstraint(
                fields=("employee", "punch_date", "punch_time", "punch_type"),
                name="unique_employee_punch_timestamp_type",
            )
        ]
        indexes = [
            models.Index(fields=("punch_date", "punch_type")),
            models.Index(fields=("employee", "punch_date")),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.punch_date} {self.punch_time} ({self.punch_type})"


class AttendanceCorrection(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        MANAGER_APPROVED = "MANAGER_APPROVED", "Manager Approved"
        MANAGER_REJECTED = "MANAGER_REJECTED", "Manager Rejected"
        FINALIZED = "FINALIZED", "Finalized"
        HR_REJECTED = "HR_REJECTED", "HR Rejected"

    class CorrectionType(models.TextChoices):
        FIX_TIME = "FIX_TIME", "Fix punch time"
        ADD_MISSING_PUNCH = "ADD_MISSING_PUNCH", "Add missing punch"

    attendance_log = models.ForeignKey(AttendanceLog, on_delete=models.PROTECT, related_name="correction_requests")
    requested_by = models.ForeignKey("organization.Employee", on_delete=models.PROTECT, related_name="correction_requests")
    correction_type = models.CharField(max_length=20, choices=CorrectionType.choices, default=CorrectionType.FIX_TIME)
    requested_punch_date = models.DateField(null=True, blank=True)
    requested_punch_time = models.TimeField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    manager_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="manager_reviewed_attendance_corrections")
    manager_remarks = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_attendance_corrections")
    reviewer_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Correction #{self.pk} - {self.status}"