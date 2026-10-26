import os
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_attendance_risk_analytics.settings")

import django

django.setup()

from django.core.files import File
from django.db import transaction

from accounts.models import User
from attendance.models import AttendanceLog
from leaves.models import LeaveRequest
from organization.models import Department, Employee, ShiftRule

DEMO_PASSWORD = os.getenv("SEED_USER_PASSWORD", "Demo@12345")
SAMPLE_DOCUMENT = BASE_DIR / "datasets" / "sample" / "sample_medical_certificate.pdf"

DEPARTMENTS = [
    ("Customer Support", "CUSTOMER_SUPPORT", "Handles customer calls, chats and tickets."),
    ("Field Service", "FIELD_SERVICE", "Technicians who visit customer sites."),
    ("Human Resources", "HUMAN_RESOURCES", "Hiring, attendance policy and employee welfare."),
    ("Finance", "FINANCE", "Payroll, billing and accounts."),
    ("Engineering", "ENGINEERING", "Builds and maintains the company's software."),
    ("IT Support", "IT_SUPPORT", "Laptops, network and internal tools."),
]

SHIFT_RULES = [
    ("General Shift", time(9, 0), time(18, 0), 10),
    ("Early Shift", time(7, 0), time(16, 0), 10),
    ("Late Shift", time(13, 0), time(22, 0), 15),
]

PEOPLE = [
    {"code": "HRA001", "first_name": "Meera", "last_name": "Kapoor", "email": "meera.kapoor@example.com", "role": User.Role.HR_ADMIN,
     "department": "Human Resources", "manager": "", "phone": "+91 98450 10001", "joined": date(2021, 4, 1)},
    {"code": "MGR101", "first_name": "Priya", "last_name": "Sharma", "email": "priya.sharma@example.com", "role": User.Role.MANAGER,
     "department": "Customer Support", "manager": "", "phone": "+91 98450 10101", "joined": date(2020, 6, 15)},
    {"code": "MGR102", "first_name": "Arjun", "last_name": "Mehta", "email": "arjun.mehta@example.com", "role": User.Role.MANAGER,
     "department": "Engineering", "manager": "", "phone": "+91 98450 10102", "joined": date(2019, 11, 4)},
    {"code": "EMP1001", "first_name": "Rahul", "last_name": "Verma", "email": "rahul.verma@example.com", "role": User.Role.EMPLOYEE,
     "department": "Customer Support", "manager": "MGR101", "phone": "+91 98450 11001", "joined": date(2023, 1, 9)},
    {"code": "EMP1002", "first_name": "Sneha", "last_name": "Iyer", "email": "sneha.iyer@example.com", "role": User.Role.EMPLOYEE,
     "department": "Customer Support", "manager": "MGR101", "phone": "+91 98450 11002", "joined": date(2022, 8, 22)},
    {"code": "EMP1003", "first_name": "Karan", "last_name": "Singh", "email": "karan.singh@example.com", "role": User.Role.EMPLOYEE,
     "department": "Engineering", "manager": "MGR102", "phone": "+91 98450 11003", "joined": date(2023, 5, 2)},
    {"code": "EMP1004", "first_name": "Ananya", "last_name": "Rao", "email": "ananya.rao@example.com", "role": User.Role.EMPLOYEE,
     "department": "Engineering", "manager": "MGR102", "phone": "+91 98450 11004", "joined": date(2024, 2, 12)},
    {"code": "EMP1005", "first_name": "Vikram", "last_name": "Nair", "email": "vikram.nair@example.com", "role": User.Role.EMPLOYEE,
     "department": "Human Resources", "manager": "HRA001", "phone": "+91 98450 11005", "joined": date(2022, 3, 28)},
]

LEAVES = [
    {"code": "EMP1001", "type": LeaveRequest.LeaveType.CASUAL, "start": date(2026, 10, 27), "end": date(2026, 10, 28),
     "reason": "Family function in my hometown.", "status": LeaveRequest.Status.PENDING, "reviewer": "", "remarks": ""},
    {"code": "EMP1002", "type": LeaveRequest.LeaveType.EARNED, "start": date(2026, 11, 9), "end": date(2026, 11, 13),
     "reason": "Planned vacation with family.", "status": LeaveRequest.Status.APPROVED, "reviewer": "mgr101", "remarks": "Approved. Please hand over open tickets."},
    {"code": "EMP1003", "type": LeaveRequest.LeaveType.SICK, "start": date(2026, 10, 12), "end": date(2026, 10, 12),
     "reason": "High fever, doctor advised rest.", "status": LeaveRequest.Status.APPROVED, "reviewer": "mgr102", "remarks": "Get well soon.", "document": True},
    {"code": "EMP1004", "type": LeaveRequest.LeaveType.UNPAID, "start": date(2026, 11, 20), "end": date(2026, 11, 21),
     "reason": "Personal work at the bank and registration office.", "status": LeaveRequest.Status.REJECTED, "reviewer": "mgr102", "remarks": "Release week. Please choose other dates."},
    {"code": "EMP1005", "type": LeaveRequest.LeaveType.OTHER, "start": date(2026, 10, 30), "end": date(2026, 10, 30),
     "reason": "Exam for a part-time course.", "status": LeaveRequest.Status.CANCELLED, "reviewer": "", "remarks": ""},
    {"code": "MGR101", "type": LeaveRequest.LeaveType.CASUAL, "start": date(2026, 11, 3), "end": date(2026, 11, 3),
     "reason": "Attending a friend's wedding.", "status": LeaveRequest.Status.PENDING, "reviewer": "", "remarks": ""},
    {"code": "MGR102", "type": LeaveRequest.LeaveType.EARNED, "start": date(2026, 12, 21), "end": date(2026, 12, 24),
     "reason": "Year-end holiday.", "status": LeaveRequest.Status.APPROVED, "reviewer": "hra001", "remarks": "Approved by HR."},
]

ATTENDANCE_START = date(2026, 10, 5)
ATTENDANCE_END = date(2026, 10, 16)
LATE_CHANCE = {"EMP1001": 0.7, "MGR102": 0.25, "EMP1005": 0.2}
MISSING_OUT_CHANCE = {"EMP1005": 0.2, "EMP1003": 0.1}
LOCATIONS = ["Main Gate", "Lobby", "Floor 2 Reader"]
LATE_REMARKS = ["Traffic jam on the way", "Bus was late", "Heavy rain in the morning", "Metro was delayed"]


def seed_departments():
    departments = {}
    for name, code, description in DEPARTMENTS:
        department, created = Department.objects.update_or_create(
            name=name,
            defaults={"code": code, "description": description, "is_active": True},
        )
        departments[name] = department
        print(f"Department {name}: {'created' if created else 'updated'}")
    return departments


def seed_shift_rules():
    for name, shift_start, shift_end, grace_minutes in SHIFT_RULES:
        existing = ShiftRule.objects.filter(shift_start=shift_start, shift_end=shift_end).first()
        if existing:
            print(f"Shift rule {shift_start:%H:%M}-{shift_end:%H:%M}: already exists as '{existing.name}'")
            continue
        ShiftRule.objects.create(name=name, shift_start=shift_start, shift_end=shift_end, grace_minutes=grace_minutes, is_active=True)
        print(f"Shift rule {name}: created")


def seed_user(person):
    employee = Employee.objects.select_related("user").filter(employee_code=person["code"]).first()
    if employee:
        user = employee.user
        created = False
    else:
        user, created = User.objects.get_or_create(username=person["code"].lower(), defaults={"email": person["email"]})

    user.first_name = person["first_name"]
    user.last_name = person["last_name"]
    user.role = person["role"]
    user.is_active = True
    user.email_verified = True
    if not User.objects.filter(email=person["email"]).exclude(pk=user.pk).exists():
        user.email = person["email"]

    if created or not user.password or not user.has_usable_password():
        user.set_password(DEMO_PASSWORD)
        password_note = "password set"
    else:
        password_note = "kept existing password"

    user.save()
    print(f"User {user.username} ({person['role']}): {'created' if created else 'updated'}, {password_note}")
    return user


def seed_employees(departments):
    employees = {}
    for person in PEOPLE:
        user = seed_user(person)
        employee, _ = Employee.objects.update_or_create(
            employee_code=person["code"],
            defaults={
                "user": user,
                "department": departments[person["department"]],
                "phone": person["phone"],
                "date_of_joining": person["joined"],
                "is_active": True,
            },
        )
        employees[person["code"]] = employee

    for person in PEOPLE:
        employee = employees[person["code"]]
        employee.manager = employees.get(person["manager"])
        employee.save(update_fields=["manager", "updated_at"])
    return employees


def seed_leaves(employees):
    for item in LEAVES:
        employee = employees[item["code"]]
        leave = LeaveRequest.objects.filter(employee=employee, start_date=item["start"], end_date=item["end"]).first()
        created = leave is None
        if created:
            leave = LeaveRequest(employee=employee, start_date=item["start"], end_date=item["end"])

        leave.leave_type = item["type"]
        leave.reason = item["reason"]
        leave.status = item["status"]
        leave.reviewed_by = User.objects.filter(username=item["reviewer"]).first() if item["reviewer"] else None
        leave.reviewer_remarks = item["remarks"]
        leave.full_clean()
        leave.save()

        if item.get("document") and not leave.supporting_document and SAMPLE_DOCUMENT.exists():
            with open(SAMPLE_DOCUMENT, "rb") as file:
                leave.supporting_document.save(SAMPLE_DOCUMENT.name, File(file), save=True)

        print(f"Leave {item['code']} {item['start']} to {item['end']} ({item['status']}): {'created' if created else 'updated'}")


def working_days(start, end):
    day = start
    while day <= end:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def shift_time(day, base, minutes):
    return (datetime.combine(day, base) + timedelta(minutes=minutes)).time()


def is_on_leave(employee, day):
    return LeaveRequest.objects.filter(
        employee=employee, status=LeaveRequest.Status.APPROVED, start_date__lte=day, end_date__gte=day
    ).exists()


def save_punch(employee, day, punch_time, punch_type, shift_rule, location, remarks=""):
    _, created = AttendanceLog.objects.get_or_create(
        employee=employee,
        punch_date=day,
        punch_time=punch_time,
        punch_type=punch_type,
        defaults={"shift_rule": shift_rule, "device_location": location, "remarks": remarks},
    )
    return created


def seed_attendance(employees):
    randomizer = random.Random(42)
    shift_rule = ShiftRule.objects.get(shift_start=time(9, 0), shift_end=time(18, 0))
    created_count = 0
    skipped_leave_days = 0

    for day in working_days(ATTENDANCE_START, ATTENDANCE_END):
        for code, employee in employees.items():
            is_late = randomizer.random() < LATE_CHANCE.get(code, 0.05)
            misses_out = randomizer.random() < MISSING_OUT_CHANCE.get(code, 0.02)
            in_offset = randomizer.randint(15, 45) if is_late else randomizer.randint(-15, 8)
            out_offset = randomizer.randint(-5, 40)
            location = randomizer.choice(LOCATIONS)
            remark = randomizer.choice(LATE_REMARKS) if is_late else ""

            if is_on_leave(employee, day):
                skipped_leave_days += 1
                continue

            punch_in = shift_time(day, shift_rule.shift_start, in_offset)
            created_count += save_punch(employee, day, punch_in, AttendanceLog.PunchType.IN, shift_rule, location, remark)
            if not misses_out:
                punch_out = shift_time(day, shift_rule.shift_end, out_offset)
                created_count += save_punch(employee, day, punch_out, AttendanceLog.PunchType.OUT, shift_rule, location)

    print(f"Attendance {ATTENDANCE_START} to {ATTENDANCE_END}: {created_count} punches created, {skipped_leave_days} leave days skipped")
    return created_count


def main():
    with transaction.atomic():
        departments = seed_departments()
        seed_shift_rules()
        employees = seed_employees(departments)
        seed_leaves(employees)
        seed_attendance(employees)

    sample = employees["EMP1001"].user
    sample.refresh_from_db()
    print()
    print(f"Done. {len(departments)} departments, {len(SHIFT_RULES)} shift rules, {len(employees)} employees, {len(LEAVES)} leave requests, attendance for every employee.")
    print(f"New users log in with the password: {DEMO_PASSWORD}")
    print(f"Stored value for {sample.username} starts with: {sample.password[:30]}...")
    print("Check in PostgreSQL: SELECT username, role, password FROM accounts_user;")


if __name__ == "__main__":
    main()