import csv
from pathlib import Path

from openpyxl import Workbook

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "datasets" / "sample"
EDGE_DIR = OUTPUT_DIR / "edge_cases"

HEADER = [
    "employee_code", "employee_name", "department", "punch_date", "punch_time", "device_location",
    "punch_type", "shift_start", "shift_end", "leave_type", "manager_code", "remarks",
]

EMPLOYEES = [
    ("MGR101", "Priya Sharma", "Customer Support", ""),
    ("MGR102", "Arjun Mehta", "Engineering", ""),
    ("EMP1001", "Rahul Verma", "cs", "MGR101"),
    ("EMP1002", "Sneha Iyer", "customer_support", "MGR101"),
    ("EMP1003", "Karan Singh", "Engineering", "MGR102"),
    ("EMP1004", "Ananya Rao", "  engineering ", "MGR102"),
    ("EMP1005", "Vikram Nair", "HR", ""),
]

PUNCHES = {
    "2026-10-19": {
        "EMP1001": ("09:25", "18:05"), "EMP1002": ("08:55", "18:00"), "EMP1003": ("09:05", None),
        "EMP1004": ("09:00", "17:20"), "EMP1005": ("09:02", "18:10"), "MGR101": ("08:50", "18:30"),
        "MGR102": ("09:00", "18:00"),
    },
    "2026-10-20": {
        "EMP1001": ("09:40", "18:00"), "EMP1002": ("09:00", "18:02"), "EMP1003": ("09:01", "18:00"),
        "EMP1004": "SICK", "EMP1005": (None, "18:00"), "MGR101": ("08:58", "18:15"),
        "MGR102": ("09:20", "18:40"),
    },
    "2026-10-21": {
        "EMP1001": ("09:31", "18:00"), "EMP1002": ("08:59", "18:00"), "EMP1003": ("09:00", "18:01"),
        "EMP1004": ("08:57", "18:00"), "EMP1005": ("09:00", "18:00"), "MGR101": ("09:00", None),
        "MGR102": ("08:45", "18:00"),
    },
}

REMARKS = {
    ("EMP1001", "2026-10-19"): "Traffic jam near the flyover, bus was late",
    ("EMP1001", "2026-10-20"): "Heavy rain and transport delay again",
    ("EMP1003", "2026-10-19"): "Forgot to punch out, system was busy",
    ("EMP1004", "2026-10-20"): "Fever, doctor advised rest",
    ("MGR102", "2026-10-20"): "Client call ran late in the morning",
}

IN_STYLES = ["IN", "in", "Check-In", "Punch In"]
OUT_STYLES = ["OUT", "out", "Check-Out", "punch_out"]
LOCATIONS = ["main_gate", "Main Gate", "floor-2 reader", "  lobby  "]

INVALID_ROWS = [
    ["EMP10X", "Bad Code", "Engineering", "2026-10-21", "09:00", "Main Gate", "IN", "09:00", "18:00", "", "MGR102", ""],
    ["EMP1003", "Karan Singh", "Engineering", "2026-13-40", "09:00", "Main Gate", "IN", "09:00", "18:00", "", "MGR102", ""],
    ["EMP1002", "Sneha Iyer", "Customer Support", "21/10/2026", "25:61", "Main Gate", "IN", "09:00", "18:00", "", "MGR101", ""],
    ["EMP1005", "Vikram Nair", "HR", "2026-10-21", "18:30", "", "BREAK", "09:00", "18:00", "", "", ""],
]


def build_rows():
    rows = []
    style = 0
    for punch_date, day in PUNCHES.items():
        for code, name, department, manager in EMPLOYEES:
            entry = day[code]
            remark = REMARKS.get((code, punch_date), "")
            if entry == "SICK":
                rows.append([code, name, department, punch_date, "", "", "", "09:00", "18:00", "SICK", manager, remark])
                continue
            in_time, out_time = entry
            if in_time:
                rows.append([code, name, department, punch_date, in_time, LOCATIONS[style % 4], IN_STYLES[style % 4], "09:00", "18:00", "", manager, remark])
                style += 1
            if out_time:
                rows.append([code, name, department, punch_date, out_time, LOCATIONS[style % 4], OUT_STYLES[style % 4], "09:00", "18:00", "", manager, ""])
                style += 1
    rows.insert(3, list(rows[2]))
    return rows


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if header:
            writer.writerow(header)
        writer.writerows(rows)


def write_excel(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "attendance"
    sheet.append(HEADER)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def write_edge_cases():
    EDGE_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(
        EDGE_DIR / "missing_columns.csv",
        ["employee_code", "employee_name", "punch_date", "punch_time"],
        [["EMP1001", "Rahul Verma", "2026-10-19", "09:00"]],
    )
    (EDGE_DIR / "empty_file.csv").write_text("")
    write_csv(EDGE_DIR / "header_only.csv", HEADER, [])
    write_csv(
        EDGE_DIR / "duplicates_and_optional_blanks.csv",
        HEADER[:9],
        [
            ["EMP1001", "Rahul Verma", "CS", "2026-10-22", "09:00", "", "IN", "09:00", "18:00"],
            ["EMP1001", "Rahul Verma", "CS", "2026-10-22", "09:00", "", "IN", "09:00", "18:00"],
            ["EMP1001", "Rahul Verma", "CS", "2026-10-22", "18:00", "", "OUT", "09:00", "18:00"],
        ],
    )
    (EDGE_DIR / "wrong_format.txt").write_text("this is not an attendance file\n")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    write_csv(OUTPUT_DIR / "attendance_sample.csv", HEADER, rows + INVALID_ROWS)
    write_excel(OUTPUT_DIR / "attendance_sample.xlsx", rows)
    write_edge_cases()
    print(f"CSV rows: {len(rows) + len(INVALID_ROWS)}, Excel rows: {len(rows)}")
    print(f"Files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()