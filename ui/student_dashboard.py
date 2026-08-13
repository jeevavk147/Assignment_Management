import os
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk, messagebox

from database import (
    UPLOADS_DIR,
    create_submission,
    list_assignments_by_course,
    list_enrolled_courses,
    list_submissions_by_student,
)
from ui.theme import PALETTE
from ui.widgets import ScrollableCard, scrollable_treeview


def show(app):
    app.build_header(app.container)

    notebook = ttk.Notebook(app.container)
    notebook.pack(fill="both", expand=True, padx=24, pady=(20, 24))

    submit_tab = ttk.Frame(notebook, padding=0)
    courses_tab = ttk.Frame(notebook, padding=0)

    notebook.add(submit_tab, text="  Submit Assignment  ")
    notebook.add(courses_tab, text="  My Courses  ")

    _build_submit_tab(app, submit_tab)
    _build_courses_tab(app, courses_tab)


def _my_enrolled_courses(app):
    return list_enrolled_courses(app.current_user["user_id"])


def _build_submit_tab(app, parent):
    left_card = ScrollableCard(parent, width=340)
    left_card.pack(side="left", fill="y", padx=(0, 20), pady=4)
    left_frame = left_card.body

    right_frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    right_frame.pack(side="right", fill="both", expand=True, pady=4)

    ttk.Label(left_frame, text="Submit Assignment", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 16))

    ttk.Label(left_frame, text="Course", style="Card.TLabel").pack(anchor="w")
    course_var = tk.StringVar()
    course_dropdown = ttk.Combobox(left_frame, textvariable=course_var, state="readonly", width=30)
    course_dropdown.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Assignment", style="Card.TLabel").pack(anchor="w")
    assignment_var = tk.StringVar()
    assignment_dropdown = ttk.Combobox(left_frame, textvariable=assignment_var, state="readonly", width=30)
    assignment_dropdown.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Notes (optional)", style="Card.TLabel").pack(anchor="w")
    comments_text = tk.Text(
        left_frame, width=30, height=4, font=("Segoe UI", 10),
        background="white", foreground=PALETTE["text"],
        relief="solid", borderwidth=1, highlightthickness=0,
    )
    comments_text.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Attach file", style="Card.TLabel").pack(anchor="w")
    file_row = ttk.Frame(left_frame, style="CardHeader.TFrame")
    file_row.pack(fill="x", pady=(2, 20))
    file_label = ttk.Label(file_row, text="No file selected", style="Muted.Card.TLabel")
    file_label.pack(side="left", fill="x", expand=True)
    selected_file = {"path": None}

    def browse_file():
        path = filedialog.askopenfilename(
            title="Select assignment file",
            filetypes=[("Documents & Archives", "*.pdf *.doc *.docx *.txt *.zip *.py"), ("All Files", "*.*")],
        )
        if path:
            selected_file["path"] = path
            file_label.configure(text=os.path.basename(path), foreground=PALETTE["text"])

    ttk.Button(file_row, text="Browse...", style="Secondary.TButton", command=browse_file).pack(side="right")

    ttk.Label(right_frame, text="Recent Submissions", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 14))
    columns = ("course", "title", "file", "submitted")
    tree_container, tree = scrollable_treeview(right_frame, columns, height=16)
    for col, label, width in (
        ("course", "Course", 90), ("title", "Assignment", 170), ("file", "File", 170), ("submitted", "Submitted", 150),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree_container.pack(fill="both", expand=True)

    course_lookup = {}
    assignment_lookup = {}

    def refresh_history():
        tree.delete(*tree.get_children())
        for s in list_submissions_by_student(app.current_user["user_id"]):
            tree.insert(
                "", "end",
                values=(s["course_code"], s["title"], os.path.basename(s["file_path"]), s["submitted_at"]),
            )

    def refresh_assignments():
        assignment_lookup.clear()
        labels = []
        course_id = course_lookup.get(course_var.get())
        if course_id is not None:
            # Group assignments aren't submittable here yet — that path needs a
            # group_id, which this student flow doesn't handle.
            for a in list_assignments_by_course(course_id):
                if a["type"] != "INDIVIDUAL":
                    continue
                labels.append(a["title"])
                assignment_lookup[a["title"]] = a["assignment_id"]
        assignment_dropdown["values"] = labels
        assignment_var.set(labels[0] if labels else "")

    def refresh_courses():
        course_lookup.clear()
        labels = []
        for c in _my_enrolled_courses(app):
            label = f"{c['course_code']} - {c['course_name']}"
            course_lookup[label] = c["course_id"]
            labels.append(label)
        course_dropdown["values"] = labels
        if labels and course_var.get() not in labels:
            course_var.set(labels[0])
        elif not labels:
            course_var.set("")
        refresh_assignments()

    def submit():
        assignment_id = assignment_lookup.get(assignment_var.get())
        if assignment_id is None:
            messagebox.showwarning(
                "No assignment available",
                "Select a course with an individual assignment first — group assignments aren't submitted here yet.",
            )
            return
        if not selected_file["path"] or not os.path.isfile(selected_file["path"]):
            messagebox.showwarning("Missing file", "Please browse and select a file before submitting.")
            return

        submission_dir = os.path.join(UPLOADS_DIR, str(assignment_id), "submissions")
        os.makedirs(submission_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = os.path.basename(selected_file["path"])
        saved_name = f"{app.current_user['user_id']}_{timestamp}_{original_name}"
        dest = os.path.join(submission_dir, saved_name)

        try:
            shutil.copy2(selected_file["path"], dest)
        except OSError as error:
            messagebox.showerror("Submission failed", f"The file could not be saved:\n{error}")
            return

        create_submission(assignment_id, app.current_user["user_id"], dest)

        messagebox.showinfo("Success", "Your assignment has been submitted successfully!")
        comments_text.delete("1.0", "end")
        selected_file["path"] = None
        file_label.configure(text="No file selected", foreground=PALETTE["text_muted"])
        refresh_history()

    course_dropdown.bind("<<ComboboxSelected>>", lambda event: refresh_assignments())
    ttk.Button(left_frame, text="Submit Assignment", style="Accent.TButton", command=submit).pack(fill="x")

    refresh_courses()
    refresh_history()


def _build_courses_tab(app, parent):
    card = ScrollableCard(parent, width=700)
    card.pack(fill="both", expand=True, padx=4, pady=4)
    body = card.body

    ttk.Label(body, text="Enrolled Courses", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 16))

    courses = _my_enrolled_courses(app)
    if not courses:
        ttk.Label(body, text="You are not enrolled in any courses yet.", style="Muted.Card.TLabel").pack(anchor="w")
        return

    for index, c in enumerate(courses):
        ttk.Label(
            body, text=f"{c['course_code']} - {c['course_name']}", style="Card.TLabel",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(12 if index else 0, 2))
        ttk.Label(
            body, text=f"Instructor: {c['faculty_name']} · Enrolled: {c['enrolled_at']}",
            style="Muted.Card.TLabel",
        ).pack(anchor="w")
        ttk.Frame(body, height=1, style="Card.TFrame").pack(fill="x", pady=(10, 0))
