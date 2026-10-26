from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RiskScore(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    employee = models.ForeignKey("organization.Employee", on_delete=models.PROTECT, related_name="risk_scores")
    score = models.DecimalField(max_digits=5, decimal_places=4, validators=[MinValueValidator(0), MaxValueValidator(1)])
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices)
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50, blank=True)
    feature_snapshot = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-calculated_at",)
        indexes = [models.Index(fields=("employee", "calculated_at"))]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.risk_level} ({self.score})"


class EmployeeRemark(models.Model):
    class Sentiment(models.TextChoices):
        POSITIVE = "POSITIVE", "Positive"
        NEUTRAL = "NEUTRAL", "Neutral"
        NEGATIVE = "NEGATIVE", "Negative"
        UNCLASSIFIED = "UNCLASSIFIED", "Unclassified"

    class ConcernCategory(models.TextChoices):
        NONE = "NONE", "None"
        ATTENDANCE = "ATTENDANCE", "Attendance"
        HEALTH = "HEALTH", "Health"
        TRANSPORT = "TRANSPORT", "Transport"
        WORKLOAD = "WORKLOAD", "Workload"
        OTHER = "OTHER", "Other"

    employee = models.ForeignKey("organization.Employee", on_delete=models.PROTECT, related_name="remarks")
    remark = models.TextField()
    sentiment = models.CharField(max_length=20, choices=Sentiment.choices, default=Sentiment.UNCLASSIFIED)
    concern_category = models.CharField(max_length=20, choices=ConcernCategory.choices, default=ConcernCategory.NONE)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Remark #{self.pk} - {self.employee.employee_code}"