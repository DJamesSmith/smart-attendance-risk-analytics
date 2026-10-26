from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from attendance.processor import EMPLOYEE_CODE_PATTERN
from organization.models import Department, Employee
from .models import User


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                css_class = "form-check-input"
            elif isinstance(widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css_class}".strip()


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


def find_claimable_user(employee_code):
    employee = Employee.objects.select_related("user").filter(employee_code=employee_code.strip().upper()).first()
    if employee and (not employee.user.password or not employee.user.has_usable_password()):
        return employee.user
    return None


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    employee_code = forms.CharField(max_length=10, help_text="Your code from the attendance system, for example EMP1001.")
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        help_text="Only needed if your employee code is not in the system yet.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True

    def clean_username(self):
        username = self.cleaned_data["username"]
        taken = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_employee_code(self):
        code = self.cleaned_data["employee_code"].strip().upper()
        if not EMPLOYEE_CODE_PATTERN.match(code):
            raise forms.ValidationError("Use a code like EMP1001: three letters and 3 to 5 digits.")

        employee = Employee.objects.select_related("user").filter(employee_code=code).first()
        if employee and employee.user != self.instance:
            raise forms.ValidationError("This employee code is already registered. Please log in instead.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        is_new_employee = self.instance.pk is None
        if is_new_employee and cleaned_data.get("employee_code") and not cleaned_data.get("department"):
            self.add_error("department", "Choose your department.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        is_new_employee = user.pk is None
        if is_new_employee:
            user.role = User.Role.EMPLOYEE
        user.save()
        if is_new_employee:
            Employee.objects.create(
                user=user,
                employee_code=self.cleaned_data["employee_code"],
                department=self.cleaned_data["department"],
            )
        return user

class HRRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email"):
            self.fields[name].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.HR_ADMIN
        user.is_active = False
        user.email_verified = False
        if commit:
            user.save()
        return user


class OTPVerifyForm(forms.Form):
    email = forms.EmailField()
    otp = forms.RegexField(regex=r"^\d{6}$", error_messages={"invalid": "The code must be exactly 6 digits."})


class APILoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(strip=False)


class RefreshTokenForm(forms.Form):
    refresh = forms.CharField()