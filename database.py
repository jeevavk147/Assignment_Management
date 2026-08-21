import math
import os
import random
import sqlite3
import sys

# When PyInstaller freezes this into an .exe, __file__ resolves inside the temporary
# extraction folder — the database and uploads must instead live next to the .exe
# itself so they persist across runs.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "assignment_app.db")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

SCHEMA = """
CREATE TABLE IF NOT EXISTS USERS (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student','faculty','admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS COURSES (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    faculty_id INTEGER NOT NULL REFERENCES USERS(user_id)
);

CREATE TABLE IF NOT EXISTS ENROLLMENTS (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES USERS(user_id),
    course_id INTEGER NOT NULL REFERENCES COURSES(course_id),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, course_id)
);

CREATE TABLE IF NOT EXISTS ASSIGNMENTS (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES COURSES(course_id),
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL CHECK (type IN ('INDIVIDUAL','GROUP')),
    max_marks REAL NOT NULL,
    due_date DATETIME NOT NULL,
    attachment_path TEXT,
    created_by INTEGER NOT NULL REFERENCES USERS(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS GROUPS (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES ASSIGNMENTS(assignment_id),
    group_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_groups_assignment_name ON GROUPS(assignment_id, group_name);

CREATE TABLE IF NOT EXISTS GROUP_MEMBERS (
    group_id INTEGER NOT NULL REFERENCES GROUPS(group_id),
    student_id INTEGER NOT NULL REFERENCES USERS(user_id),
    PRIMARY KEY (group_id, student_id)
);

CREATE TABLE IF NOT EXISTS SUBMISSIONS (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES ASSIGNMENTS(assignment_id),
    student_id INTEGER REFERENCES USERS(user_id),
    group_id INTEGER REFERENCES GROUPS(group_id),
    file_path TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (student_id IS NOT NULL AND group_id IS NULL) OR
        (student_id IS NULL AND group_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS GRADES (
    grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL UNIQUE REFERENCES SUBMISSIONS(submission_id),
    marks_obtained REAL NOT NULL,
    feedback TEXT,
    graded_by INTEGER NOT NULL REFERENCES USERS(user_id),
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
    conn.close()
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def _migrate(conn):
    """Add columns that were introduced after some databases were already created."""
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(ASSIGNMENTS)").fetchall()]
    if "attachment_path" not in columns:
        conn.execute("ALTER TABLE ASSIGNMENTS ADD COLUMN attachment_path TEXT")
        conn.commit()


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT * FROM USERS WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def create_user(name, email, password_hash, role):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO USERS (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, role),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def list_users(role=None):
    conn = get_connection()
    if role:
        rows = conn.execute(
            "SELECT * FROM USERS WHERE role = ? ORDER BY name", (role,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM USERS ORDER BY role, name").fetchall()
    conn.close()
    return rows


def create_course(course_code, course_name, faculty_id):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO COURSES (course_code, course_name, faculty_id) VALUES (?, ?, ?)",
        (course_code, course_name, faculty_id),
    )
    conn.commit()
    course_id = cur.lastrowid
    conn.close()
    return course_id


def list_courses_by_faculty(faculty_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM COURSES WHERE faculty_id = ? ORDER BY course_code", (faculty_id,)
    ).fetchall()
    conn.close()
    return rows


def create_assignment(course_id, title, description, type_, max_marks, due_date, created_by):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO ASSIGNMENTS (course_id, title, description, type, max_marks, due_date, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (course_id, title, description, type_, max_marks, due_date, created_by),
    )
    conn.commit()
    assignment_id = cur.lastrowid
    conn.close()
    return assignment_id


def list_assignments_by_course(course_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ASSIGNMENTS WHERE course_id = ? ORDER BY due_date", (course_id,)
    ).fetchall()
    conn.close()
    return rows


def enroll_student(student_id, course_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO ENROLLMENTS (student_id, course_id) VALUES (?, ?)",
        (student_id, course_id),
    )
    conn.commit()
    conn.close()


def unenroll_student(student_id, course_id):
    """Drop a student from a course, and scrub them from any groups belonging to
    that course's assignments so group member counts don't go stale."""
    conn = get_connection()
    conn.execute(
        """DELETE FROM GROUP_MEMBERS WHERE student_id = ? AND group_id IN (
               SELECT GROUPS.group_id FROM GROUPS
               JOIN ASSIGNMENTS ON ASSIGNMENTS.assignment_id = GROUPS.assignment_id
               WHERE ASSIGNMENTS.course_id = ?
           )""",
        (student_id, course_id),
    )
    conn.execute(
        "DELETE FROM ENROLLMENTS WHERE student_id = ? AND course_id = ?",
        (student_id, course_id),
    )
    conn.commit()
    conn.close()


def list_enrolled_students(course_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT USERS.*, ENROLLMENTS.enrolled_at FROM USERS
           JOIN ENROLLMENTS ON ENROLLMENTS.student_id = USERS.user_id
           WHERE ENROLLMENTS.course_id = ?
           ORDER BY USERS.name""",
        (course_id,),
    ).fetchall()
    conn.close()
    return rows


def list_students_not_enrolled_in_course(course_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM USERS
           WHERE role = 'student'
           AND user_id NOT IN (SELECT student_id FROM ENROLLMENTS WHERE course_id = ?)
           ORDER BY name""",
        (course_id,),
    ).fetchall()
    conn.close()
    return rows


def list_enrolled_courses(student_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT COURSES.*, USERS.name AS faculty_name, ENROLLMENTS.enrolled_at
           FROM COURSES
           JOIN ENROLLMENTS ON ENROLLMENTS.course_id = COURSES.course_id
           JOIN USERS ON USERS.user_id = COURSES.faculty_id
           WHERE ENROLLMENTS.student_id = ?
           ORDER BY COURSES.course_code""",
        (student_id,),
    ).fetchall()
    conn.close()
    return rows


def create_submission(assignment_id, student_id, file_path):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO SUBMISSIONS (assignment_id, student_id, file_path) VALUES (?, ?, ?)",
        (assignment_id, student_id, file_path),
    )
    conn.commit()
    submission_id = cur.lastrowid
    conn.close()
    return submission_id


def list_submissions_by_student(student_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT SUBMISSIONS.*, ASSIGNMENTS.title, ASSIGNMENTS.max_marks, COURSES.course_code,
                  GRADES.marks_obtained, GRADES.feedback, GRADES.graded_at
           FROM SUBMISSIONS
           JOIN ASSIGNMENTS ON ASSIGNMENTS.assignment_id = SUBMISSIONS.assignment_id
           JOIN COURSES ON COURSES.course_id = ASSIGNMENTS.course_id
           LEFT JOIN GRADES ON GRADES.submission_id = SUBMISSIONS.submission_id
           WHERE SUBMISSIONS.student_id = ?
           ORDER BY SUBMISSIONS.submitted_at DESC""",
        (student_id,),
    ).fetchall()
    conn.close()
    return rows


def list_submissions_for_assignment(assignment_id):
    """Every submission for one assignment (individual or group), with the
    submitter's display name and any existing grade — the faculty grading view."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT SUBMISSIONS.*,
                  USERS.name AS student_name,
                  GROUPS.group_name AS group_name,
                  GRADES.grade_id, GRADES.marks_obtained, GRADES.feedback, GRADES.graded_at
           FROM SUBMISSIONS
           LEFT JOIN USERS ON USERS.user_id = SUBMISSIONS.student_id
           LEFT JOIN GROUPS ON GROUPS.group_id = SUBMISSIONS.group_id
           LEFT JOIN GRADES ON GRADES.submission_id = SUBMISSIONS.submission_id
           WHERE SUBMISSIONS.assignment_id = ?
           ORDER BY SUBMISSIONS.submitted_at DESC""",
        (assignment_id,),
    ).fetchall()
    conn.close()
    return rows


def list_submissions_for_faculty(faculty_id):
    """Every submission across all of this faculty member's courses — the
    consolidated submission history / grading queue, independent of which
    assignment it belongs to."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT SUBMISSIONS.*,
                  ASSIGNMENTS.title AS assignment_title, ASSIGNMENTS.max_marks,
                  COURSES.course_code, COURSES.course_name,
                  USERS.name AS student_name,
                  GROUPS.group_name AS group_name,
                  GRADES.marks_obtained, GRADES.feedback, GRADES.graded_at
           FROM SUBMISSIONS
           JOIN ASSIGNMENTS ON ASSIGNMENTS.assignment_id = SUBMISSIONS.assignment_id
           JOIN COURSES ON COURSES.course_id = ASSIGNMENTS.course_id
           LEFT JOIN USERS ON USERS.user_id = SUBMISSIONS.student_id
           LEFT JOIN GROUPS ON GROUPS.group_id = SUBMISSIONS.group_id
           LEFT JOIN GRADES ON GRADES.submission_id = SUBMISSIONS.submission_id
           WHERE COURSES.faculty_id = ?
           ORDER BY SUBMISSIONS.submitted_at DESC""",
        (faculty_id,),
    ).fetchall()
    conn.close()
    return rows


def create_or_update_grade(submission_id, marks_obtained, feedback, graded_by):
    """One grade per submission (GRADES.submission_id is UNIQUE) — re-grading
    updates the existing row instead of inserting a second one."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT grade_id FROM GRADES WHERE submission_id = ?", (submission_id,)
    ).fetchone()
    if existing:
        conn.execute(
            """UPDATE GRADES SET marks_obtained = ?, feedback = ?, graded_by = ?,
                                  graded_at = CURRENT_TIMESTAMP
               WHERE submission_id = ?""",
            (marks_obtained, feedback, graded_by, submission_id),
        )
    else:
        conn.execute(
            "INSERT INTO GRADES (submission_id, marks_obtained, feedback, graded_by) VALUES (?, ?, ?, ?)",
            (submission_id, marks_obtained, feedback, graded_by),
        )
    conn.commit()
    conn.close()


def update_assignment(assignment_id, title, description, max_marks, due_date):
    conn = get_connection()
    conn.execute(
        "UPDATE ASSIGNMENTS SET title = ?, description = ?, max_marks = ?, due_date = ? WHERE assignment_id = ?",
        (title, description, max_marks, due_date, assignment_id),
    )
    conn.commit()
    conn.close()


def update_assignment_attachment(assignment_id, attachment_path):
    conn = get_connection()
    conn.execute(
        "UPDATE ASSIGNMENTS SET attachment_path = ? WHERE assignment_id = ?",
        (attachment_path, assignment_id),
    )
    conn.commit()
    conn.close()


def list_assignments_for_student_with_status(student_id):
    """Every assignment across the student's enrolled courses, annotated with
    whether they (individually) or their group have already submitted —
    backs both the Assignments tab's status column and the deadline banner."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT ASSIGNMENTS.*, COURSES.course_code, COURSES.course_name,
                  EXISTS (
                      SELECT 1 FROM SUBMISSIONS
                      WHERE SUBMISSIONS.assignment_id = ASSIGNMENTS.assignment_id
                      AND SUBMISSIONS.student_id = ?
                  ) AS submitted_individually,
                  EXISTS (
                      SELECT 1 FROM SUBMISSIONS
                      JOIN GROUP_MEMBERS ON GROUP_MEMBERS.group_id = SUBMISSIONS.group_id
                      WHERE SUBMISSIONS.assignment_id = ASSIGNMENTS.assignment_id
                      AND GROUP_MEMBERS.student_id = ?
                  ) AS submitted_as_group
           FROM ASSIGNMENTS
           JOIN COURSES ON COURSES.course_id = ASSIGNMENTS.course_id
           JOIN ENROLLMENTS ON ENROLLMENTS.course_id = COURSES.course_id
           WHERE ENROLLMENTS.student_id = ?
           ORDER BY ASSIGNMENTS.due_date""",
        (student_id, student_id, student_id),
    ).fetchall()
    conn.close()
    return rows


def list_assignments_by_faculty(faculty_id, type_=None):
    conn = get_connection()
    query = """SELECT ASSIGNMENTS.*, COURSES.course_code, COURSES.course_name
               FROM ASSIGNMENTS JOIN COURSES ON COURSES.course_id = ASSIGNMENTS.course_id
               WHERE COURSES.faculty_id = ?"""
    params = [faculty_id]
    if type_:
        query += " AND ASSIGNMENTS.type = ?"
        params.append(type_)
    query += " ORDER BY ASSIGNMENTS.due_date"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def create_group(assignment_id, group_name):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO GROUPS (assignment_id, group_name) VALUES (?, ?)",
        (assignment_id, group_name),
    )
    conn.commit()
    group_id = cur.lastrowid
    conn.close()
    return group_id


def list_groups_by_assignment(assignment_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT GROUPS.*, COUNT(GROUP_MEMBERS.student_id) AS member_count
           FROM GROUPS LEFT JOIN GROUP_MEMBERS ON GROUP_MEMBERS.group_id = GROUPS.group_id
           WHERE GROUPS.assignment_id = ?
           GROUP BY GROUPS.group_id
           ORDER BY GROUPS.group_name""",
        (assignment_id,),
    ).fetchall()
    conn.close()
    return rows


def list_group_membership_for_assignment(course_id, assignment_id):
    """Every student enrolled in the course, with whichever group (if any) they hold
    specifically under this assignment. Never reflects group membership from any
    other assignment — each assignment's groups are entirely its own."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT USERS.user_id, USERS.name, USERS.email, ag.group_id, ag.group_name
           FROM USERS
           JOIN ENROLLMENTS ON ENROLLMENTS.student_id = USERS.user_id AND ENROLLMENTS.course_id = ?
           LEFT JOIN (
               SELECT GROUP_MEMBERS.student_id AS student_id,
                      GROUPS.group_id AS group_id,
                      GROUPS.group_name AS group_name
               FROM GROUP_MEMBERS
               JOIN GROUPS ON GROUPS.group_id = GROUP_MEMBERS.group_id
               WHERE GROUPS.assignment_id = ?
           ) AS ag ON ag.student_id = USERS.user_id
           ORDER BY USERS.name""",
        (course_id, assignment_id),
    ).fetchall()
    conn.close()
    return rows


def set_student_group(assignment_id, student_id, group_id):
    """Move a student to `group_id` within this assignment's groups (or unassign with group_id=None)."""
    conn = get_connection()
    conn.execute(
        """DELETE FROM GROUP_MEMBERS WHERE student_id = ? AND group_id IN (
               SELECT group_id FROM GROUPS WHERE assignment_id = ?
           )""",
        (student_id, assignment_id),
    )
    if group_id is not None:
        conn.execute(
            "INSERT INTO GROUP_MEMBERS (group_id, student_id) VALUES (?, ?)",
            (group_id, student_id),
        )
    conn.commit()
    conn.close()


def auto_distribute_groups(course_id, assignment_id, group_size):
    """Ensure enough "Group N" groups exist to hold every enrolled student at roughly
    `group_size` students each, then randomly fill in only the currently-unassigned
    students, topping up whichever groups have the fewest members. Safe to call more
    than once (e.g. after new students enroll) — never moves someone already placed."""
    total_enrolled = len(list_enrolled_students(course_id))
    if total_enrolled == 0 or group_size < 1:
        return
    needed_groups = max(1, math.ceil(total_enrolled / group_size))

    existing = list_groups_by_assignment(assignment_id)
    group_ids = [g["group_id"] for g in existing]
    existing_names = {g["group_name"] for g in existing}

    next_num = 1
    while len(group_ids) < needed_groups:
        name = f"Group {next_num}"
        next_num += 1
        if name in existing_names:
            continue
        group_ids.append(create_group(assignment_id, name))
        existing_names.add(name)

    if not group_ids:
        return

    membership = list_group_membership_for_assignment(course_id, assignment_id)
    counts = {gid: 0 for gid in group_ids}
    unassigned = []
    for m in membership:
        if m["group_id"] in counts:
            counts[m["group_id"]] += 1
        elif m["group_id"] is None:
            unassigned.append(m)

    random.shuffle(unassigned)
    for student in unassigned:
        target = min(counts, key=counts.get)
        set_student_group(assignment_id, student["user_id"], target)
        counts[target] += 1
