from rest_framework import serializers
from .models import AttendanceCorrection, AttendanceImportBatch, AttendanceLog
from .services import report_links


class ImportBatchSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.CharField(source="uploaded_by.username")
    reports = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceImportBatch
        fields = (
            "id", "original_filename", "status", "total_rows", "processed_rows", "error_message",
            "uploaded_by", "created_at", "started_at", "completed_at", "reports",
        )
        read_only_fields = fields

    def get_reports(self, obj):
        return report_links(obj)


class AttendanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceLog
        fields = ("id", "punch_date", "punch_time", "punch_type", "device_location")
        read_only_fields = fields


class AttendanceCorrectionSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="requested_by.employee_code")
    employee_name = serializers.SerializerMethodField()
    attendance_log = AttendanceLogSerializer()
    manager_reviewed_by = serializers.CharField(source="manager_reviewed_by.username", default=None)
    reviewed_by = serializers.CharField(source="reviewed_by.username", default=None)

    class Meta:
        model = AttendanceCorrection
        fields = (
            "id", "employee_code", "employee_name", "attendance_log", "correction_type",
            "requested_punch_date", "requested_punch_time", "reason", "status",
            "manager_reviewed_by", "manager_remarks", "reviewed_by", "reviewer_remarks", "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_employee_name(self, obj):
        return obj.requested_by.user.get_full_name() or obj.requested_by.user.username