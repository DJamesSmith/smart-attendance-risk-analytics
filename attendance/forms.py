from django import forms
from .models import AttendanceCorrection


class AttendanceCorrectionForm(forms.ModelForm):
    class Meta:
        model = AttendanceCorrection
        fields = ("attendance_log", "requested_punch_date", "requested_punch_time", "reason")