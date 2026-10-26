from django.contrib import admin
from .models import EmployeeRemark, RiskScore


@admin.register(RiskScore)
class RiskScoreAdmin(admin.ModelAdmin):
    list_display = ("employee", "score", "risk_level", "model_name", "calculated_at")
    list_filter = ("risk_level", "model_name", "calculated_at")
    search_fields = ("employee__employee_code", "employee__user__first_name", "employee__user__last_name")
    readonly_fields = ("calculated_at",)


@admin.register(EmployeeRemark)
class EmployeeRemarkAdmin(admin.ModelAdmin):
    list_display = ("employee", "sentiment", "concern_category", "analyzed_at", "created_at")
    list_filter = ("sentiment", "concern_category", "created_at")
    search_fields = ("employee__employee_code", "remark")
    readonly_fields = ("created_at", "analyzed_at")