from django.contrib import admin
from .models import Department, Employee, ShiftRule


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Department", {"fields": ("name", "code", "description", "is_active")}),
        ("Timeline", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "full_name", "department", "manager", "is_active")
    list_filter = ("department", "is_active", ("date_of_joining", admin.DateFieldListFilter))
    search_fields = ("employee_code", "user__first_name", "user__last_name", "user__email")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user", "department", "manager")
    autocomplete_fields = ("manager",)
    fieldsets = (
        ("Identity", {"fields": ("user", "employee_code", "phone")}),
        ("Organization", {"fields": ("department", "manager", "date_of_joining", "is_active")}),
        ("Timeline", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Name", ordering="user__first_name")
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


@admin.register(ShiftRule)
class ShiftRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "shift_start", "shift_end", "grace_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Shift", {"fields": ("name", "shift_start", "shift_end", "grace_minutes", "is_active")}),
        ("Timeline", {"fields": ("created_at", "updated_at")}),
    )