from django.db import models
from .managers import UserManager
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        HR_ADMIN = "HR_ADMIN", "HR Admin"
        MANAGER = "MANAGER", "Manager"
        EMPLOYEE = "EMPLOYEE", "Employee"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    email_verified = models.BooleanField(default=False)

    objects = UserManager()

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"