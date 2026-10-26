from rest_framework import serializers

from .models import Employee


class EmployeeLookupSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email")
    role = serializers.CharField(source="user.role")
    department = serializers.CharField(source="department.name")
    manager_code = serializers.CharField(source="manager.employee_code", default=None)

    class Meta:
        model = Employee
        fields = ("employee_code", "name", "email", "role", "department", "manager_code", "phone", "date_of_joining", "is_active")
        read_only_fields = fields

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username