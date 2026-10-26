from datetime import timedelta
from pathlib import Path

from django import forms
from django.utils import timezone

from accounts.forms import BootstrapFormMixin
from organization.models import Department

from .models import AttendanceCorrection, AttendanceImportBatch, AttendanceLog
from .processor import ALLOWED_EXTENSIONS

MAX_UPLOAD_MB = 5
OPEN_STATUSES = (AttendanceCorrection.Status.PENDING, AttendanceCorrection.Status.MANAGER_APPROVED)
DECISIONS = (("approve", "Approve"), ("reject", "Reject"))


class AttendanceUploadForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AttendanceImportBatch
        fields = ("file",)
        widgets = {"file": forms.ClearableFileInput(attrs={"accept": ".csv,.xlsx"})}

    def clean_file(self):
        file = self.cleaned_data["file"]
        extension = Path(file.name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Only .csv and .xlsx files are allowed.")
        if file.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"The file must be smaller than {MAX_UPLOAD_MB} MB.")
        return file


class DailyAttendanceFilterForm(BootstrapFormMixin, forms.Form):
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="All departments")


class AttendanceCorrectionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AttendanceCorrection
        fields = ("attendance_log", "correction_type", "requested_punch_date", "requested_punch_time", "reason")
        widgets = {
            "requested_punch_date": forms.DateInput(attrs={"type": "date"}),
            "requested_punch_time": forms.TimeInput(attrs={"type": "time"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {"attendance_log": "Punch to correct"}
        help_texts = {
            "requested_punch_date": "Leave blank to keep the date of the selected punch.",
            "correction_type": "Choose 'Add missing punch' when the IN or OUT punch for that day is missing.",
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee
        since = timezone.localdate() - timedelta(days=60)
        self.fields["attendance_log"].queryset = AttendanceLog.objects.filter(
            employee=employee, punch_date__gte=since
        ).order_by("-punch_date", "-punch_time")
        self.fields["requested_punch_time"].required = True

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if len(reason) < 10:
            raise forms.ValidationError("Please explain the reason in at least 10 characters.")
        return reason

    def clean_requested_punch_date(self):
        requested_date = self.cleaned_data.get("requested_punch_date")
        if requested_date and requested_date > timezone.localdate():
            raise forms.ValidationError("The corrected date cannot be in the future.")
        return requested_date

    def clean(self):
        cleaned_data = super().clean()
        log = cleaned_data.get("attendance_log")
        if not log:
            return cleaned_data

        open_requests = AttendanceCorrection.objects.filter(attendance_log=log, status__in=OPEN_STATUSES)
        if self.instance.pk:
            open_requests = open_requests.exclude(pk=self.instance.pk)
        if open_requests.exists():
            self.add_error("attendance_log", "This punch already has an open correction request.")

        if cleaned_data.get("correction_type") == AttendanceCorrection.CorrectionType.ADD_MISSING_PUNCH:
            missing_type = AttendanceLog.PunchType.OUT if log.punch_type == AttendanceLog.PunchType.IN else AttendanceLog.PunchType.IN
            punch_date = cleaned_data.get("requested_punch_date") or log.punch_date
            already_there = AttendanceLog.objects.filter(employee=log.employee, punch_date=punch_date, punch_type=missing_type)
            if already_there.exists():
                self.add_error("correction_type", f"An {missing_type} punch already exists for {punch_date}. Use 'Fix punch time' instead.")

        return cleaned_data


class ManagerReviewForm(BootstrapFormMixin, forms.ModelForm):
    decision = forms.ChoiceField(choices=DECISIONS)

    class Meta:
        model = AttendanceCorrection
        fields = ("manager_remarks",)
        widgets = {"manager_remarks": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("decision") == "reject" and not cleaned_data.get("manager_remarks", "").strip():
            self.add_error("manager_remarks", "Please give a reason for rejecting.")
        return cleaned_data


class HRFinalizeForm(BootstrapFormMixin, forms.ModelForm):
    decision = forms.ChoiceField(choices=DECISIONS)

    class Meta:
        model = AttendanceCorrection
        fields = ("reviewer_remarks",)
        labels = {"reviewer_remarks": "HR remarks"}
        widgets = {"reviewer_remarks": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get("decision")
        if decision == "reject" and not cleaned_data.get("reviewer_remarks", "").strip():
            self.add_error("reviewer_remarks", "Please give a reason for rejecting.")

        correction = self.instance
        if decision == "approve" and correction.correction_type == AttendanceCorrection.CorrectionType.FIX_TIME:
            log = correction.attendance_log
            clash = AttendanceLog.objects.filter(
                employee=log.employee,
                punch_date=correction.requested_punch_date or log.punch_date,
                punch_time=correction.requested_punch_time,
                punch_type=log.punch_type,
            ).exclude(pk=log.pk)
            if clash.exists():
                raise forms.ValidationError("Another punch already exists at the requested date and time.")
        return cleaned_data