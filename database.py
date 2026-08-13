import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assignment_app.db")

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
    created_by INTEGER NOT NULL REFERENCES USERS(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS GROUPS (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES ASSIGNMENTS(assignment_id),
    group_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
    conn.close()


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


def list_enrolled_students(course_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT USERS.* FROM USERS
           JOIN ENROLLMENTS ON ENROLLMENTS.student_id = USERS.user_id
           WHERE ENROLLMENTS.course_id = ?
           ORDER BY USERS.name""",
        (course_id,),
    ).fetchall()
    conn.close()
    return rows
