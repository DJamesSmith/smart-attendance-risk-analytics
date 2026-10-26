from pathlib import Path
from django import forms
from .models import LeaveRequest

DOCUMENT_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
MAX_DOCUMENT_MB = 2
ACTIVE_STATUSES = (LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED)


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ("leave_type", "start_date", "end_date", "reason", "supporting_document")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee

    def clean_supporting_document(self):
        document = self.cleaned_data.get("supporting_document")
        if not document:
            return document
        if Path(document.name).suffix.lower() not in DOCUMENT_EXTENSIONS:
            raise forms.ValidationError("Upload a PDF, JPG or PNG file.")
        if document.size > MAX_DOCUMENT_MB * 1024 * 1024:
            raise forms.ValidationError(f"The document must be smaller than {MAX_DOCUMENT_MB} MB.")
        return document

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if not (self.employee and start_date and end_date) or end_date < start_date:
            return cleaned_data

        overlapping = LeaveRequest.objects.filter(
            employee=self.employee,
            status__in=ACTIVE_STATUSES,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if overlapping.exists():
            raise forms.ValidationError("You already have a pending or approved leave in these dates.")
        return cleaned_data


class LeaveReviewForm(forms.ModelForm):
    decision = forms.ChoiceField(choices=(("approve", "Approve"), ("reject", "Reject")))

    class Meta:
        model = LeaveRequest
        fields = ("reviewer_remarks",)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("decision") == "reject" and not cleaned_data.get("reviewer_remarks", "").strip():
            self.add_error("reviewer_remarks", "Please give a reason for rejecting.")
        return cleaned_data