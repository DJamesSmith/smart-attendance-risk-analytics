from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import UserCreateForm
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = UserCreateForm
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active", "email_verified")
    list_filter = ("role", "is_active", "email_verified", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Organization Access", {"fields": ("role", "email_verified")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Organization Access", {"fields": ("email", "role", "email_verified")}),
    )