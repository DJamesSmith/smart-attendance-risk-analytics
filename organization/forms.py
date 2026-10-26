from django import forms
from .models import Department, Employee, ShiftRule


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ("name", "code", "description", "is_active")


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ("user", "employee_code", "department", "manager", "phone", "date_of_joining", "is_active")


class ShiftRuleForm(forms.ModelForm):
    class Meta:
        model = ShiftRule
        fields = ("name", "shift_start", "shift_end", "grace_minutes", "is_active")