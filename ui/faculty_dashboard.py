import os
import shutil
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk, messagebox

from database import (
    UPLOADS_DIR,
    create_assignment,
    create_course,
    enroll_student,
    list_assignments_by_faculty,
    list_courses_by_faculty,
    list_enrolled_students,
    list_students_not_enrolled_in_course,
    unenroll_student,
    update_assignment_attachment,
)
from ui.assignment_details import open_assignment_details
from ui.date_picker import DateTimeEntry
from ui.group_editor import open_group_editor
from ui.theme import PALETTE
from ui.widgets import ScrollableCard, scrollable_treeview


def show(app):
    app.build_header(app.container)

    notebook = ttk.Notebook(app.container)
    notebook.pack(fill="both", expand=True, padx=24, pady=(20, 24))

    courses_tab = ttk.Frame(notebook, padding=0)
    create_assignment_tab = ttk.Frame(notebook, padding=0)
    assignments_list_tab = ttk.Frame(notebook, padding=0)
    enrollment_tab = ttk.Frame(notebook, padding=0)

    notebook.add(courses_tab, text="  My Courses  ")
    notebook.add(create_assignment_tab, text="  Create Assignment  ")
    notebook.add(assignments_list_tab, text="  Assignments  ")
    notebook.add(enrollment_tab, text="  Enrollment  ")

    # Built before the courses/create-assignment tabs so those tabs can trigger their refreshes.
    refresh_enrollment_courses = _build_enrollment_tab(app, enrollment_tab)
    refresh_assignments_list = _build_assignments_list_tab(app, assignments_list_tab)
    refresh_create_assignment_courses = _build_create_assignment_tab(
        app, create_assignment_tab, on_assignment_created=refresh_assignments_list,
    )
    _build_courses_tab(
        app, courses_tab,
        on_course_created=lambda: (refresh_create_assignment_courses(), refresh_enrollment_courses()),
    )


def _my_courses(app):
    return list_courses_by_faculty(app.current_user["user_id"])


def _panel_pair(parent, left_width=340):
    left_card = ScrollableCard(parent, width=left_width)
    left_card.pack(side="left", fill="y", padx=(0, 20), pady=4)

    right_frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    right_frame.pack(side="right", fill="both", expand=True, pady=4)

    return left_card.body, right_frame


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
    tree_container, tree = scrollable_treeview(right_frame, columns)
    for col, label, width in (("id", "ID", 40), ("code", "Code", 100), ("name", "Course Name", 250)):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree_container.pack(fill="both", expand=True)

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


def _build_create_assignment_tab(app, parent, on_assignment_created):
    card = ScrollableCard(parent, width=760, padding=32)
    card.pack(fill="both", expand=True, padx=4, pady=4)
    form = card.body
    form.columnconfigure(0, weight=1)
    form.columnconfigure(1, weight=1)

    row = 0
    ttk.Label(form, text="Create Assignment", style="Header.Card.TLabel").grid(
        row=row, column=0, columnspan=2, sticky="w"
    )
    row += 1
    ttk.Label(
        form, text="For GROUP assignments, set up groups afterward from the Assignments tab.",
        style="Muted.Card.TLabel",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 24))
    row += 1

    ttk.Label(form, text="ASSIGNMENT DETAILS", style="SubHeader.Card.TLabel").grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    row += 1

    ttk.Label(form, text="Course", style="Card.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 16))
    ttk.Label(form, text="Type", style="Card.TLabel").grid(row=row, column=1, sticky="w")
    row += 1
    course_var = tk.StringVar()
    course_dropdown = ttk.Combobox(form, textvariable=course_var, state="readonly")
    course_dropdown.grid(row=row, column=0, sticky="ew", padx=(0, 16), pady=(2, 16))
    type_var = tk.StringVar(value="INDIVIDUAL")
    type_dropdown = ttk.Combobox(
        form, textvariable=type_var, state="readonly", values=("INDIVIDUAL", "GROUP")
    )
    type_dropdown.grid(row=row, column=1, sticky="ew", pady=(2, 16))
    row += 1

    ttk.Label(form, text="Title", style="Card.TLabel").grid(row=row, column=0, columnspan=2, sticky="w")
    row += 1
    title_entry = ttk.Entry(form)
    title_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(2, 16))
    row += 1

    ttk.Label(form, text="Max marks", style="Card.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 16))
    ttk.Label(form, text="Due date", style="Card.TLabel").grid(row=row, column=1, sticky="w")
    row += 1
    marks_entry = ttk.Entry(form)
    marks_entry.grid(row=row, column=0, sticky="ew", padx=(0, 16), pady=(2, 20))
    due_picker = DateTimeEntry(form, width=16)
    due_picker.grid(row=row, column=1, sticky="w", pady=(2, 20))
    row += 1

    ttk.Label(form, text="DESCRIPTION", style="SubHeader.Card.TLabel").grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
    )
    row += 1
    ttk.Label(
        form, text="As long as you need — multi-paragraph briefs, requirements, rubrics all fit here.",
        style="Muted.Card.TLabel",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 12))
    row += 1

    desc_frame = ttk.Frame(form, style="Card.TFrame")
    desc_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 20))
    description_text = tk.Text(
        desc_frame, height=16, wrap="word", font=("Segoe UI", 10),
        background="white", foreground=PALETTE["text"],
        relief="solid", borderwidth=1, highlightthickness=0,
    )
    desc_scroll = ttk.Scrollbar(desc_frame, orient="vertical", command=description_text.yview)
    description_text.configure(yscrollcommand=desc_scroll.set)
    description_text.pack(side="left", fill="both", expand=True)
    desc_scroll.pack(side="right", fill="y")
    row += 1

    ttk.Label(form, text="ATTACHMENT (optional)", style="SubHeader.Card.TLabel").grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    row += 1
    attachment_row = ttk.Frame(form, style="CardHeader.TFrame")
    attachment_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 20))
    attachment_label = ttk.Label(attachment_row, text="No file selected", style="Muted.Card.TLabel")
    attachment_label.pack(side="left", fill="x", expand=True)
    attachment = {"path": None}

    def browse_attachment():
        path = filedialog.askopenfilename(title="Select assignment attachment")
        if path:
            attachment["path"] = path
            attachment_label.configure(text=os.path.basename(path), foreground=PALETTE["text"])

    ttk.Button(attachment_row, text="Browse...", style="Secondary.TButton", command=browse_attachment).pack(
        side="right"
    )
    row += 1

    create_button = ttk.Button(form, text="Create Assignment", style="Accent.TButton")
    create_button.grid(row=row, column=0, columnspan=2, sticky="ew")

    course_lookup = {}

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

    def create():
        course_id = course_lookup.get(course_var.get())
        title = title_entry.get().strip()
        description = description_text.get("1.0", "end").strip()
        type_ = type_var.get()
        marks_raw = marks_entry.get().strip()
        due_raw = due_picker.get().strip()

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
        if not due_raw:
            messagebox.showwarning("Missing due date", "Use 'Pick date...' to choose a due date.")
            return
        try:
            datetime.strptime(due_raw, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showwarning("Invalid due date", "Use 'Pick date...' to choose a valid due date.")
            return

        assignment_id = create_assignment(
            course_id, title, description, type_, max_marks, due_raw, app.current_user["user_id"]
        )

        if attachment["path"]:
            assignment_dir = os.path.join(UPLOADS_DIR, str(assignment_id))
            os.makedirs(assignment_dir, exist_ok=True)
            dest = os.path.join(assignment_dir, os.path.basename(attachment["path"]))
            shutil.copy2(attachment["path"], dest)
            update_assignment_attachment(assignment_id, dest)

        title_entry.delete(0, "end")
        description_text.delete("1.0", "end")
        marks_entry.delete(0, "end")
        due_picker.set("")
        attachment["path"] = None
        attachment_label.configure(text="No file selected", foreground=PALETTE["text_muted"])
        type_var.set("INDIVIDUAL")
        on_assignment_created()

        if type_ == "GROUP":
            messagebox.showinfo(
                "Assignment created",
                f"'{title}' created. Head to the Assignments tab and use \"Edit Groups\" to set up its groups.",
            )
        else:
            messagebox.showinfo("Assignment created", f"'{title}' created.")

    create_button.configure(command=create)

    refresh_courses()
    return refresh_courses


def _build_assignments_list_tab(app, parent):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    frame.pack(fill="both", expand=True, padx=4, pady=4)

    ttk.Label(frame, text="All Assignments", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 14))

    assignment_lookup = {}

    edit_groups_button = ttk.Button(frame, text="Edit Groups for Selected Assignment", style="Secondary.TButton")
    edit_groups_button.pack(anchor="w", pady=(0, 12))
    edit_groups_button.state(["disabled"])

    columns = ("id", "course", "title", "type", "max_marks", "due", "file")
    tree_container, tree = scrollable_treeview(frame, columns, height=14)
    for col, label, width in (
        ("id", "ID", 40),
        ("course", "Course", 90),
        ("title", "Title", 220),
        ("type", "Type", 90),
        ("max_marks", "Max", 60),
        ("due", "Due", 140),
        ("file", "Attachment", 150),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree_container.pack(fill="both", expand=True)

    def on_selection_changed(event=None):
        selection = tree.selection()
        if not selection:
            edit_groups_button.state(["disabled"])
            return
        assignment_id = tree.item(selection[0])["values"][0]
        a = assignment_lookup.get(assignment_id)
        if a and a["type"] == "GROUP":
            edit_groups_button.state(["!disabled"])
        else:
            edit_groups_button.state(["disabled"])

    def open_selected_groups():
        selection = tree.selection()
        if not selection:
            return
        assignment_id = tree.item(selection[0])["values"][0]
        a = assignment_lookup.get(assignment_id)
        if a:
            open_group_editor(app, a["assignment_id"], a["course_id"], a["title"])

    def open_details(event=None):
        selection = tree.selection()
        if not selection:
            return
        assignment_id = tree.item(selection[0])["values"][0]
        a = assignment_lookup.get(assignment_id)
        if a:
            open_assignment_details(app, a, on_updated=refresh)

    edit_groups_button.configure(command=open_selected_groups)
    tree.bind("<<TreeviewSelect>>", on_selection_changed)
    tree.bind("<Double-1>", open_details)

    def refresh():
        tree.delete(*tree.get_children())
        assignment_lookup.clear()
        for a in list_assignments_by_faculty(app.current_user["user_id"]):
            assignment_lookup[a["assignment_id"]] = a
            file_name = os.path.basename(a["attachment_path"]) if a["attachment_path"] else "—"
            tree.insert(
                "", "end",
                values=(a["assignment_id"], a["course_code"], a["title"], a["type"], a["max_marks"], a["due_date"], file_name),
            )
        on_selection_changed()

    refresh()
    return refresh


def _build_enrollment_tab(app, parent):
    left_frame, right_frame = _panel_pair(parent)

    ttk.Label(left_frame, text="Enroll Student", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 16))

    ttk.Label(left_frame, text="Course", style="Card.TLabel").pack(anchor="w")
    course_var = tk.StringVar()
    course_dropdown = ttk.Combobox(left_frame, textvariable=course_var, state="readonly", width=30)
    course_dropdown.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Student (not yet enrolled in this course)", style="Card.TLabel").pack(anchor="w")
    student_var = tk.StringVar()
    student_dropdown = ttk.Combobox(left_frame, textvariable=student_var, state="readonly", width=30)
    student_dropdown.pack(pady=(2, 20))

    ttk.Label(right_frame, text="Enrolled Students", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 4))
    course_caption = ttk.Label(right_frame, text="Select a course to see who's enrolled.", style="Muted.Card.TLabel")
    course_caption.pack(anchor="w", pady=(0, 10))

    remove_button = ttk.Button(right_frame, text="Remove Selected from Course", style="Secondary.TButton")
    remove_button.pack(anchor="e", pady=(0, 12))
    remove_button.state(["disabled"])

    columns = ("id", "name", "email", "enrolled")
    tree_container, tree = scrollable_treeview(right_frame, columns, height=12)
    for col, label, width in (
        ("id", "ID", 40), ("name", "Name", 150), ("email", "Email", 190), ("enrolled", "Enrolled On", 140),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree_container.pack(fill="both", expand=True)

    course_lookup = {}
    student_lookup = {}

    def refresh_available_students():
        student_lookup.clear()
        labels = []
        course_id = course_lookup.get(course_var.get())
        if course_id is not None:
            for student in list_students_not_enrolled_in_course(course_id):
                label = f"{student['name']} ({student['email']})"
                student_lookup[label] = student["user_id"]
                labels.append(label)
        student_dropdown["values"] = labels
        student_var.set(labels[0] if labels else "")

    def refresh_enrolled():
        tree.delete(*tree.get_children())
        course_id = course_lookup.get(course_var.get())
        if course_id is None:
            return
        students = list_enrolled_students(course_id)
        course_caption.configure(text=f"{len(students)} student(s) enrolled in {course_var.get()}.")
        for s in students:
            tree.insert("", "end", values=(s["user_id"], s["name"], s["email"], s["enrolled_at"]))

    def on_course_selected(event=None):
        refresh_enrolled()
        refresh_available_students()
        remove_button.state(["disabled"])

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
        on_course_selected()

    def enroll():
        course_id = course_lookup.get(course_var.get())
        student_id = student_lookup.get(student_var.get())
        if course_id is None:
            messagebox.showwarning("No course", "Create a course first, then select it here.")
            return
        if student_id is None:
            messagebox.showwarning("No student", "No unenrolled students available for this course.")
            return
        try:
            enroll_student(student_id, course_id)
        except sqlite3.IntegrityError:
            messagebox.showerror("Already enrolled", "That student is already enrolled in this course.")
            return
        messagebox.showinfo("Enrolled", "Student enrolled successfully.")
        on_course_selected()

    def on_enrolled_selection_changed(event=None):
        if tree.selection():
            remove_button.state(["!disabled"])
        else:
            remove_button.state(["disabled"])

    def remove_selected():
        selection = tree.selection()
        if not selection:
            return
        course_id = course_lookup.get(course_var.get())
        values = tree.item(selection[0])["values"]
        student_id, student_name = values[0], values[1]
        if not messagebox.askyesno(
            "Remove from course",
            f"Remove {student_name} from {course_var.get()}?\n\n"
            "They'll also be removed from any groups under this course's assignments.",
        ):
            return
        unenroll_student(student_id, course_id)
        on_course_selected()

    course_dropdown.bind("<<ComboboxSelected>>", on_course_selected)
    tree.bind("<<TreeviewSelect>>", on_enrolled_selection_changed)
    remove_button.configure(command=remove_selected)
    ttk.Button(left_frame, text="Enroll Student", style="Accent.TButton", command=enroll).pack(fill="x")

    refresh_courses()
    return refresh_courses
