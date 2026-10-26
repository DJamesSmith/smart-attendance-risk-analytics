-- Smart Attendance Risk Analytics: raw SQL examples for PostgreSQL
-- Run with: psql -U <db_user> -d <db_name> -f sql_queries.sql
-- A punch is late when the first IN punch of the day is after shift_start + grace_minutes.


-- 1. SELECT: late arrivals (first IN punch of the day after the grace period)
SELECT e.employee_code,
       u.first_name || ' ' || u.last_name AS employee_name,
       a.punch_date,
       MIN(a.punch_time) AS first_in,
       s.shift_start,
       s.grace_minutes
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
JOIN accounts_user u ON u.id = e.user_id
JOIN organization_shiftrule s ON s.id = a.shift_rule_id
WHERE a.punch_type = 'IN'
GROUP BY e.employee_code, u.first_name, u.last_name, a.punch_date, s.shift_start, s.grace_minutes
HAVING MIN(a.punch_time) > s.shift_start + make_interval(mins => s.grace_minutes)
ORDER BY a.punch_date, e.employee_code;


-- 2. WHERE with AND / OR: IN punches on one day that came from the lobby reader or have a remark
SELECT e.employee_code, a.punch_date, a.punch_time, a.device_location, a.remarks
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_type = 'IN'
  AND a.punch_date = DATE '2026-10-20'
  AND (a.device_location = 'Lobby' OR a.remarks <> '')
ORDER BY a.punch_time;


-- 3. LIKE: search departments by name (ILIKE ignores upper/lower case)
SELECT d.name AS department, d.code, COUNT(e.id) AS employees
FROM organization_department d
LEFT JOIN organization_employee e ON e.department_id = d.id
WHERE d.name LIKE '%Support%' OR d.code LIKE 'HUMAN%' OR d.name ILIKE '%engineer%'
GROUP BY d.name, d.code
ORDER BY d.name;


-- 4. BETWEEN: all punches in a date range
SELECT e.employee_code, a.punch_date, a.punch_time, a.punch_type
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_date BETWEEN DATE '2026-10-05' AND DATE '2026-10-09'
ORDER BY a.punch_date, e.employee_code, a.punch_time;


-- 5. ORDER BY + LIMIT: the 5 latest IN punches of all time
SELECT e.employee_code, a.punch_date, a.punch_time
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_type = 'IN'
ORDER BY a.punch_time DESC, a.punch_date
LIMIT 5;


-- 6a. FETCH vs LIMIT: the same result as query 5 written with the SQL-standard FETCH clause
SELECT e.employee_code, a.punch_date, a.punch_time
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_type = 'IN'
ORDER BY a.punch_time DESC, a.punch_date
FETCH FIRST 5 ROWS ONLY;

-- 6b. Paging: LIMIT/OFFSET (PostgreSQL style) and OFFSET/FETCH (SQL standard) return the same rows 6-10
SELECT e.employee_code, a.punch_date, a.punch_time
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_type = 'IN'
ORDER BY a.punch_time DESC, a.punch_date, e.employee_code
LIMIT 5 OFFSET 5;

SELECT e.employee_code, a.punch_date, a.punch_time
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_type = 'IN'
ORDER BY a.punch_time DESC, a.punch_date, e.employee_code
OFFSET 5 ROWS FETCH NEXT 5 ROWS ONLY;

-- 6c. Only FETCH can do WITH TIES: rows that tie with the last row are also returned
SELECT e.employee_code, a.punch_date, a.punch_time
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_type = 'OUT'
ORDER BY a.punch_time
FETCH FIRST 3 ROWS WITH TIES;


-- 7. COUNT: late marks per employee
SELECT late.employee_code, COUNT(*) AS late_marks
FROM (
    SELECT e.employee_code, a.punch_date
    FROM attendance_attendancelog a
    JOIN organization_employee e ON e.id = a.employee_id
    JOIN organization_shiftrule s ON s.id = a.shift_rule_id
    WHERE a.punch_type = 'IN'
    GROUP BY e.employee_code, a.punch_date, s.shift_start, s.grace_minutes
    HAVING MIN(a.punch_time) > s.shift_start + make_interval(mins => s.grace_minutes)
) AS late
GROUP BY late.employee_code
ORDER BY late_marks DESC;


-- 8. SUM: total working hours per employee (first IN to last OUT on each day)
SELECT day.employee_code,
       COUNT(*) AS days_with_both_punches,
       ROUND(SUM(EXTRACT(EPOCH FROM (day.last_out - day.first_in)) / 3600)::numeric, 2) AS total_hours
FROM (
    SELECT e.employee_code,
           a.punch_date,
           MIN(a.punch_time) FILTER (WHERE a.punch_type = 'IN') AS first_in,
           MAX(a.punch_time) FILTER (WHERE a.punch_type = 'OUT') AS last_out
    FROM attendance_attendancelog a
    JOIN organization_employee e ON e.id = a.employee_id
    GROUP BY e.employee_code, a.punch_date
) AS day
WHERE day.first_in IS NOT NULL AND day.last_out IS NOT NULL
GROUP BY day.employee_code
ORDER BY total_hours DESC;


-- 9. MIN / MAX / AVG: arrival delay in minutes after shift start (only late days)
SELECT delay.employee_code,
       MIN(delay.minutes_late) AS min_delay,
       MAX(delay.minutes_late) AS max_delay,
       ROUND(AVG(delay.minutes_late), 1) AS avg_delay
FROM (
    SELECT e.employee_code,
           a.punch_date,
           EXTRACT(EPOCH FROM (MIN(a.punch_time) - s.shift_start)) / 60 AS minutes_late
    FROM attendance_attendancelog a
    JOIN organization_employee e ON e.id = a.employee_id
    JOIN organization_shiftrule s ON s.id = a.shift_rule_id
    WHERE a.punch_type = 'IN'
    GROUP BY e.employee_code, a.punch_date, s.shift_start, s.grace_minutes
    HAVING MIN(a.punch_time) > s.shift_start + make_interval(mins => s.grace_minutes)
) AS delay
GROUP BY delay.employee_code
ORDER BY avg_delay DESC;


-- 10. GROUP BY: late marks per department
SELECT late.department, COUNT(*) AS late_marks
FROM (
    SELECT d.name AS department, e.id, a.punch_date
    FROM attendance_attendancelog a
    JOIN organization_employee e ON e.id = a.employee_id
    JOIN organization_department d ON d.id = e.department_id
    JOIN organization_shiftrule s ON s.id = a.shift_rule_id
    WHERE a.punch_type = 'IN'
    GROUP BY d.name, e.id, a.punch_date, s.shift_start, s.grace_minutes
    HAVING MIN(a.punch_time) > s.shift_start + make_interval(mins => s.grace_minutes)
) AS late
GROUP BY late.department
ORDER BY late_marks DESC;


-- 11. HAVING: employees who were late 3 or more times
SELECT late.employee_code, COUNT(*) AS late_marks
FROM (
    SELECT e.employee_code, a.punch_date
    FROM attendance_attendancelog a
    JOIN organization_employee e ON e.id = a.employee_id
    JOIN organization_shiftrule s ON s.id = a.shift_rule_id
    WHERE a.punch_type = 'IN'
    GROUP BY e.employee_code, a.punch_date, s.shift_start, s.grace_minutes
    HAVING MIN(a.punch_time) > s.shift_start + make_interval(mins => s.grace_minutes)
) AS late
GROUP BY late.employee_code
HAVING COUNT(*) >= 3
ORDER BY late_marks DESC;


-- 12. INNER JOIN: employees with their attendance punches (only employees who have punches)
SELECT e.employee_code, u.first_name, d.name AS department, a.punch_date, a.punch_time, a.punch_type
FROM organization_employee e
INNER JOIN accounts_user u ON u.id = e.user_id
INNER JOIN organization_department d ON d.id = e.department_id
INNER JOIN attendance_attendancelog a ON a.employee_id = e.id
WHERE a.punch_date = DATE '2026-10-21'
ORDER BY e.employee_code, a.punch_time;


-- 13. FULL OUTER JOIN: employees with no punches in a date range (and punches with no employee, if any)
SELECT e.employee_code, logs.punch_count
FROM organization_employee e
FULL OUTER JOIN (
    SELECT employee_id, COUNT(*) AS punch_count
    FROM attendance_attendancelog
    WHERE punch_date BETWEEN DATE '2026-10-19' AND DATE '2026-10-21'
    GROUP BY employee_id
) AS logs ON logs.employee_id = e.id
WHERE logs.employee_id IS NULL OR e.id IS NULL
ORDER BY e.employee_code;


-- 14. NATURAL JOIN: both sides expose only one shared column name (employee_id), so the join is safe
SELECT emp.employee_code, punches.punch_date, punches.punch_time, punches.punch_type
FROM (SELECT id AS employee_id, employee_code FROM organization_employee) AS emp
NATURAL JOIN (SELECT employee_id, punch_date, punch_time, punch_type FROM attendance_attendancelog) AS punches
WHERE punches.punch_date = DATE '2026-10-20'
ORDER BY emp.employee_code, punches.punch_time;


-- 15. UNION ALL: one list of present rows and approved leave rows for a date range
SELECT e.employee_code, a.punch_date AS day, 'PRESENT' AS status
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
WHERE a.punch_type = 'IN' AND a.punch_date BETWEEN DATE '2026-10-19' AND DATE '2026-10-21'
GROUP BY e.employee_code, a.punch_date
UNION ALL
SELECT e.employee_code, day::date, 'ON_LEAVE ' || l.leave_type
FROM leaves_leaverequest l
JOIN organization_employee e ON e.id = l.employee_id
CROSS JOIN generate_series(l.start_date, l.end_date, INTERVAL '1 day') AS day
WHERE l.status = 'APPROVED' AND day::date BETWEEN DATE '2026-10-19' AND DATE '2026-10-21'
ORDER BY day, employee_code;


-- 16. INTERSECT: employees who were both late and absent (working day, no punch, no approved leave) in a range
SELECT e.employee_code
FROM attendance_attendancelog a
JOIN organization_employee e ON e.id = a.employee_id
JOIN organization_shiftrule s ON s.id = a.shift_rule_id
WHERE a.punch_type = 'IN' AND a.punch_date BETWEEN DATE '2026-10-05' AND DATE '2026-10-23'
GROUP BY e.employee_code, a.punch_date, s.shift_start, s.grace_minutes
HAVING MIN(a.punch_time) > s.shift_start + make_interval(mins => s.grace_minutes)
INTERSECT
SELECT e.employee_code
FROM organization_employee e
CROSS JOIN generate_series(DATE '2026-10-05', DATE '2026-10-23', INTERVAL '1 day') AS day
WHERE EXTRACT(ISODOW FROM day) < 6
  AND NOT EXISTS (
      SELECT 1 FROM attendance_attendancelog a
      WHERE a.employee_id = e.id AND a.punch_date = day::date
  )
  AND NOT EXISTS (
      SELECT 1 FROM leaves_leaverequest l
      WHERE l.employee_id = e.id AND l.status = 'APPROVED' AND day::date BETWEEN l.start_date AND l.end_date
  )
ORDER BY employee_code;
