import re
from django import forms
from .models import Department, Employee, ShiftRule

DEPARTMENT_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{2,20}$")


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ("name", "code", "description", "is_active")

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper().replace(" ", "_")
        if not DEPARTMENT_CODE_PATTERN.match(code):
            raise forms.ValidationError("Use 2-20 capital letters, digits or underscores, for example FINANCE.")
        return code


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ("user", "employee_code", "department", "manager", "phone", "date_of_joining", "is_active")


class ShiftRuleForm(forms.ModelForm):
    class Meta:
        model = ShiftRule
        fields = ("name", "shift_start", "shift_end", "grace_minutes", "is_active")