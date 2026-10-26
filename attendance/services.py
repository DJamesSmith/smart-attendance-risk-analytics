import csv
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from leaves.models import LeaveRequest
from organization.models import Department, Employee, ShiftRule

from .models import AttendanceCorrection, AttendanceImportBatch, AttendanceLog
from .processor import DEFAULT_SHIFT, AttendanceFileError, AttendanceProcessor, make_shift_rule, summarize_day

REPORT_NAMES = ("daily_summary.csv", "anomaly_report.csv", "correction_required.csv")


def report_folder(batch):
    return Path(settings.MEDIA_ROOT) / "reports" / f"batch_{batch.pk}"


def report_links(batch):
    links = []
    for name in REPORT_NAMES:
        if (report_folder(batch) / name).exists():
            links.append({"name": name, "url": f"{settings.MEDIA_URL}reports/batch_{batch.pk}/{name}"})
    return links


def read_report(batch, name, limit=50):
    path = report_folder(batch) / name
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as file:
        return [row for number, row in enumerate(csv.DictReader(file)) if number < limit]


def import_attendance_file(batch):
    batch.status = AttendanceImportBatch.Status.PROCESSING
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at"])

    try:
        processor = AttendanceProcessor(batch.file.path).run()
        with transaction.atomic():
            saved_rows = save_records(processor.records, batch)
        processor.write_reports(report_folder(batch))
    except AttendanceFileError as error:
        return mark_failed(batch, str(error))
    except Exception as error:
        return mark_failed(batch, f"Unexpected error while importing: {error}")

    counters = processor.counters
    skipped = counters["valid_rows"] - counters["leave_rows"] - saved_rows
    batch.status = AttendanceImportBatch.Status.COMPLETED
    batch.total_rows = counters["total_rows"]
    batch.processed_rows = saved_rows
    batch.error_message = (
        f"Invalid rows: {counters['invalid_rows']}, duplicate rows in file: {counters['duplicate_rows']}, "
        f"already imported earlier: {skipped}, leave rows: {counters['leave_rows']}"
    )
    batch.completed_at = timezone.now()
    batch.save()
    return batch


def mark_failed(batch, message):
    batch.status = AttendanceImportBatch.Status.FAILED
    batch.error_message = message
    batch.completed_at = timezone.now()
    batch.save()
    return batch


def save_records(records, batch):
    departments = {}
    employees = {}
    shift_rules = {}
    saved_rows = 0

    for record in records:
        employee = get_or_create_employee(record, departments, employees)
        if record["punch_time"] is None:
            save_leave_row(record, employee, batch.uploaded_by)
            continue

        _, created = AttendanceLog.objects.get_or_create(
            employee=employee,
            punch_date=record["punch_date"],
            punch_time=record["punch_time"],
            punch_type=record["punch_type"],
            defaults={
                "import_batch": batch,
                "device_location": record["device_location"],
                "shift_rule": get_or_create_shift_rule(record["shift"], shift_rules),
                "remarks": record["remarks"],
            },
        )
        if created:
            saved_rows += 1

    link_managers(records, employees)
    return saved_rows


def get_or_create_department(name, departments):
    if name not in departments:
        departments[name], _ = Department.objects.get_or_create(
            name=name, defaults={"code": name.upper().replace(" ", "_")[:20]}
        )
    return departments[name]


def get_or_create_employee(record, departments, employees):
    code = record["employee_code"]
    if code in employees:
        return employees[code]

    employee = Employee.objects.select_related("user").filter(employee_code=code).first()
    if employee is None:
        first_name, _, last_name = record["employee_name"].partition(" ")
        user, _ = User.objects.get_or_create(
            username=code.lower(),
            defaults={
                "email": f"{code.lower()}@employees.local",
                "first_name": first_name,
                "last_name": last_name,
                "role": User.Role.EMPLOYEE,
            },
        )
        employee = Employee.objects.create(
            user=user,
            employee_code=code,
            department=get_or_create_department(record["department"], departments),
        )

    employees[code] = employee
    return employee


def get_or_create_shift_rule(rule, shift_rules):
    if rule not in shift_rules:
        values = dict(rule)
        shift_rule = ShiftRule.objects.filter(shift_start=values["shift_start"], shift_end=values["shift_end"]).first()
        if shift_rule is None:
            shift_rule = ShiftRule.objects.create(
                name=f"Shift {values['shift_start']:%H:%M}-{values['shift_end']:%H:%M}",
                shift_start=values["shift_start"],
                shift_end=values["shift_end"],
                grace_minutes=values["grace_minutes"],
            )
        shift_rules[rule] = shift_rule
    return shift_rules[rule]


def save_leave_row(record, employee, approved_by):
    LeaveRequest.objects.get_or_create(
        employee=employee,
        start_date=record["punch_date"],
        end_date=record["punch_date"],
        defaults={
            "leave_type": record["leave_type"],
            "reason": record["remarks"] or "Imported from attendance file",
            "status": LeaveRequest.Status.APPROVED,
            "reviewed_by": approved_by,
        },
    )


def link_managers(records, employees):
    manager_codes = {record["employee_code"]: record["manager_code"] for record in records if record["manager_code"]}
    for employee_code, manager_code in manager_codes.items():
        manager = employees.get(manager_code) or Employee.objects.select_related("user").filter(employee_code=manager_code).first()
        employee = employees[employee_code]
        if manager is None or manager.pk == employee.pk:
            continue
        if employee.manager_id != manager.pk:
            employee.manager = manager
            employee.save(update_fields=["manager"])
        if manager.user.role == User.Role.EMPLOYEE:
            manager.user.role = User.Role.MANAGER
            manager.user.save(update_fields=["role"])


def log_to_record(log):
    shift = DEFAULT_SHIFT
    if log.shift_rule:
        shift = make_shift_rule(log.shift_rule.shift_start, log.shift_rule.shift_end, log.shift_rule.grace_minutes)
    return {
        "employee_code": log.employee.employee_code,
        "employee_name": log.employee.user.get_full_name() or log.employee.user.username,
        "department": log.employee.department.name,
        "punch_date": log.punch_date,
        "punch_time": log.punch_time,
        "punch_type": log.punch_type,
        "leave_type": "",
        "shift": shift,
    }


def leave_to_record(leave, on_date):
    return {
        "employee_code": leave.employee.employee_code,
        "employee_name": leave.employee.user.get_full_name() or leave.employee.user.username,
        "department": leave.employee.department.name,
        "punch_date": on_date,
        "punch_time": None,
        "punch_type": "",
        "leave_type": leave.leave_type,
        "shift": DEFAULT_SHIFT,
    }


def build_daily_rows(logs, leaves=()):
    groups = {}
    for log in logs:
        groups.setdefault((log.punch_date, log.employee.employee_code), []).append(log_to_record(log))
    for leave, on_date in leaves:
        groups.setdefault((on_date, leave.employee.employee_code), []).append(leave_to_record(leave, on_date))
    return [summarize_day(records) for _, records in sorted(groups.items())]


def apply_correction(correction):
    log = correction.attendance_log
    new_date = correction.requested_punch_date or log.punch_date

    if correction.correction_type == AttendanceCorrection.CorrectionType.ADD_MISSING_PUNCH:
        missing_type = AttendanceLog.PunchType.OUT if log.punch_type == AttendanceLog.PunchType.IN else AttendanceLog.PunchType.IN
        AttendanceLog.objects.get_or_create(
            employee=log.employee,
            punch_date=new_date,
            punch_time=correction.requested_punch_time,
            punch_type=missing_type,
            defaults={
                "device_location": "HR Correction",
                "shift_rule": log.shift_rule,
                "remarks": f"Added by correction #{correction.pk}",
            },
        )
        return

    log.punch_date = new_date
    log.punch_time = correction.requested_punch_time
    log.save(update_fields=["punch_date", "punch_time"])