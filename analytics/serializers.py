from rest_framework import serializers
from .models import RiskScore


class RiskScoreSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_code")
    employee_name = serializers.SerializerMethodField()
    department = serializers.CharField(source="employee.department.name")

    class Meta:
        model = RiskScore
        fields = (
            "id", "employee_code", "employee_name", "department", "score", "risk_level",
            "model_name", "model_version", "feature_snapshot", "calculated_at",
        )
        read_only_fields = fields

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username