import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from database import (
    create_assignment,
    create_course,
    enroll_student,
    list_assignments_by_course,
    list_courses_by_faculty,
    list_enrolled_students,
    list_users,
)
from ui.theme import PALETTE


def show(app):
    app.build_header(app.container)

    notebook = ttk.Notebook(app.container)
    notebook.pack(fill="both", expand=True, padx=24, pady=(20, 24))

    courses_tab = ttk.Frame(notebook, padding=0)
    assignments_tab = ttk.Frame(notebook, padding=0)
    enrollment_tab = ttk.Frame(notebook, padding=0)

    notebook.add(courses_tab, text="  My Courses  ")
    notebook.add(assignments_tab, text="  Assignments  ")
    notebook.add(enrollment_tab, text="  Enrollment  ")

    # Built before the courses tab so newly created courses can refresh their dropdowns.
    refresh_assignment_courses = _build_assignments_tab(app, assignments_tab)
    refresh_enrollment_courses = _build_enrollment_tab(app, enrollment_tab)
    _build_courses_tab(
        app, courses_tab,
        on_course_created=lambda: (refresh_assignment_courses(), refresh_enrollment_courses()),
    )


def _my_courses(app):
    return list_courses_by_faculty(app.current_user["user_id"])


def _panel_pair(parent):
    left_frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    left_frame.pack(side="left", fill="y", padx=(0, 20), pady=4)

    right_frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    right_frame.pack(side="right", fill="both", expand=True, pady=4)

    return left_frame, right_frame


def _build_courses_tab(app, parent, on_course_created):
    left_frame, right_frame = _panel_pair(parent)

    ttk.Label(left_frame, text="Create Course", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 16))

    ttk.Label(left_frame, text="Course code (e.g. CS501)", style="Card.TLabel").pack(anchor="w")
    code_entry = ttk.Entry(left_frame, width=30)
    code_entry.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Course name", style="Card.TLabel").pack(anchor="w")
    name_entry = ttk.Entry(left_frame, width=30)
    name_entry.pack(pady=(2, 20))

    ttk.Label(right_frame, text="My Courses", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 14))

    columns = ("id", "code", "name")
    tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=15)
    for col, label, width in (("id", "ID", 40), ("code", "Code", 100), ("name", "Course Name", 250)):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree.pack(fill="both", expand=True)

    def refresh():
        tree.delete(*tree.get_children())
        for course in _my_courses(app):
            tree.insert("", "end", values=(course["course_id"], course["course_code"], course["course_name"]))

    def create():
        code = code_entry.get().strip()
        name = name_entry.get().strip()
        if not code or not name:
            messagebox.showwarning("Missing information", "Course code and name are both required.")
            return
        try:
            create_course(code, name, app.current_user["user_id"])
        except sqlite3.IntegrityError:
            messagebox.showerror("Could not create course", f"Course code '{code}' is already in use.")
            return
        messagebox.showinfo("Course created", f"Course {code} created.")
        code_entry.delete(0, "end")
        name_entry.delete(0, "end")
        refresh()
        on_course_created()

    ttk.Button(left_frame, text="Create Course", style="Accent.TButton", command=create).pack(fill="x")

    refresh()


def _build_assignments_tab(app, parent):
    left_frame, right_frame = _panel_pair(parent)

    ttk.Label(left_frame, text="Create Assignment", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 16))

    ttk.Label(left_frame, text="Course", style="Card.TLabel").pack(anchor="w")
    course_var = tk.StringVar()
    course_dropdown = ttk.Combobox(left_frame, textvariable=course_var, state="readonly", width=30)
    course_dropdown.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Title", style="Card.TLabel").pack(anchor="w")
    title_entry = ttk.Entry(left_frame, width=30)
    title_entry.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Description", style="Card.TLabel").pack(anchor="w")
    description_text = tk.Text(
        left_frame, width=30, height=4, font=("Segoe UI", 10),
        background="white", foreground=PALETTE["text"],
        relief="solid", borderwidth=1, highlightthickness=0,
    )
    description_text.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Type", style="Card.TLabel").pack(anchor="w")
    type_var = tk.StringVar(value="INDIVIDUAL")
    type_dropdown = ttk.Combobox(
        left_frame, textvariable=type_var, state="readonly",
        values=("INDIVIDUAL", "GROUP"), width=27,
    )
    type_dropdown.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Max marks", style="Card.TLabel").pack(anchor="w")
    marks_entry = ttk.Entry(left_frame, width=30)
    marks_entry.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Due date (YYYY-MM-DD HH:MM)", style="Card.TLabel").pack(anchor="w")
    due_entry = ttk.Entry(left_frame, width=30)
    due_entry.pack(pady=(2, 20))

    ttk.Label(right_frame, text="Assignments", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 14))

    columns = ("id", "title", "type", "max_marks", "due")
    tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=15)
    for col, label, width in (
        ("id", "ID", 40),
        ("title", "Title", 160),
        ("type", "Type", 90),
        ("max_marks", "Max", 60),
        ("due", "Due", 140),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree.pack(fill="both", expand=True)

    course_lookup = {}

    def refresh_assignments():
        tree.delete(*tree.get_children())
        course_id = course_lookup.get(course_var.get())
        if course_id is None:
            return
        for a in list_assignments_by_course(course_id):
            tree.insert(
                "", "end",
                values=(a["assignment_id"], a["title"], a["type"], a["max_marks"], a["due_date"]),
            )

    def refresh_courses():
        courses = _my_courses(app)
        course_lookup.clear()
        labels = []
        for course in courses:
            label = f"{course['course_code']} - {course['course_name']}"
            course_lookup[label] = course["course_id"]
            labels.append(label)
        course_dropdown["values"] = labels
        if labels and course_var.get() not in labels:
            course_var.set(labels[0])
        elif not labels:
            course_var.set("")
        refresh_assignments()

    def create():
        course_id = course_lookup.get(course_var.get())
        title = title_entry.get().strip()
        description = description_text.get("1.0", "end").strip()
        type_ = type_var.get()
        marks_raw = marks_entry.get().strip()
        due_raw = due_entry.get().strip()

        if course_id is None:
            messagebox.showwarning("No course", "Create a course first, then select it here.")
            return
        if not title:
            messagebox.showwarning("Missing information", "Assignment title is required.")
            return
        try:
            max_marks = float(marks_raw)
        except ValueError:
            messagebox.showwarning("Invalid marks", "Max marks must be a number.")
            return
        try:
            datetime.strptime(due_raw, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showwarning("Invalid due date", "Use the format YYYY-MM-DD HH:MM, e.g. 2026-09-01 23:59.")
            return

        create_assignment(course_id, title, description, type_, max_marks, due_raw, app.current_user["user_id"])
        messagebox.showinfo("Assignment created", f"'{title}' created.")
        title_entry.delete(0, "end")
        description_text.delete("1.0", "end")
        marks_entry.delete(0, "end")
        due_entry.delete(0, "end")
        refresh_assignments()

    course_dropdown.bind("<<ComboboxSelected>>", lambda event: refresh_assignments())
    ttk.Button(left_frame, text="Create Assignment", style="Accent.TButton", command=create).pack(fill="x")

    refresh_courses()
    return refresh_courses


def _build_enrollment_tab(app, parent):
    left_frame, right_frame = _panel_pair(parent)

    ttk.Label(left_frame, text="Enroll Student", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 16))

    ttk.Label(left_frame, text="Course", style="Card.TLabel").pack(anchor="w")
    course_var = tk.StringVar()
    course_dropdown = ttk.Combobox(left_frame, textvariable=course_var, state="readonly", width=30)
    course_dropdown.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Student", style="Card.TLabel").pack(anchor="w")
    student_var = tk.StringVar()
    student_dropdown = ttk.Combobox(left_frame, textvariable=student_var, state="readonly", width=30)
    student_dropdown.pack(pady=(2, 20))

    ttk.Label(right_frame, text="Enrolled Students", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 14))

    columns = ("id", "name", "email")
    tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=15)
    for col, label, width in (("id", "ID", 40), ("name", "Name", 160), ("email", "Email", 200)):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree.pack(fill="both", expand=True)

    course_lookup = {}
    student_lookup = {}

    def refresh_students():
        student_lookup.clear()
        labels = []
        for student in list_users(role="student"):
            label = f"{student['name']} ({student['email']})"
            student_lookup[label] = student["user_id"]
            labels.append(label)
        student_dropdown["values"] = labels
        if labels and student_var.get() not in labels:
            student_var.set(labels[0])

    def refresh_enrolled():
        tree.delete(*tree.get_children())
        course_id = course_lookup.get(course_var.get())
        if course_id is None:
            return
        for s in list_enrolled_students(course_id):
            tree.insert("", "end", values=(s["user_id"], s["name"], s["email"]))

    def refresh_courses():
        courses = _my_courses(app)
        course_lookup.clear()
        labels = []
        for course in courses:
            label = f"{course['course_code']} - {course['course_name']}"
            course_lookup[label] = course["course_id"]
            labels.append(label)
        course_dropdown["values"] = labels
        if labels and course_var.get() not in labels:
            course_var.set(labels[0])
        elif not labels:
            course_var.set("")
        refresh_enrolled()

    def enroll():
        course_id = course_lookup.get(course_var.get())
        student_id = student_lookup.get(student_var.get())
        if course_id is None:
            messagebox.showwarning("No course", "Create a course first, then select it here.")
            return
        if student_id is None:
            messagebox.showwarning("No student", "No student accounts exist yet — ask an admin to create one.")
            return
        try:
            enroll_student(student_id, course_id)
        except sqlite3.IntegrityError:
            messagebox.showerror("Already enrolled", "That student is already enrolled in this course.")
            return
        messagebox.showinfo("Enrolled", "Student enrolled successfully.")
        refresh_enrolled()

    course_dropdown.bind("<<ComboboxSelected>>", lambda event: refresh_enrolled())
    ttk.Button(left_frame, text="Enroll Student", style="Accent.TButton", command=enroll).pack(fill="x")

    refresh_students()
    refresh_courses()
    return refresh_courses
