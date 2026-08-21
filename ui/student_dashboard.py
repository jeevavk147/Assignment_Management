import os
import shutil
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, ttk, messagebox

from database import (
    UPLOADS_DIR,
    create_submission,
    list_assignments_by_course,
    list_assignments_for_student_with_status,
    list_enrolled_courses,
    list_submissions_by_student,
)
from ui.assignment_details import open_assignment_details
from ui.grading import open_grade_view_dialog
from ui.theme import PALETTE
from ui.widgets import ScrollableCard, scrollable_treeview

DUE_SOON_DAYS = 3


def show(app):
    app.build_header(app.container)
    _build_deadline_banner(app, app.container)

    notebook = ttk.Notebook(app.container)
    notebook.pack(fill="both", expand=True, padx=24, pady=(0, 24))

    assignments_tab = ttk.Frame(notebook, padding=0)
    submit_tab = ttk.Frame(notebook, padding=0)
    courses_tab = ttk.Frame(notebook, padding=0)

    notebook.add(assignments_tab, text="  Assignments  ")
    notebook.add(submit_tab, text="  Submit Assignment  ")
    notebook.add(courses_tab, text="  My Courses  ")

    _build_assignments_tab(app, assignments_tab)
    _build_submit_tab(app, submit_tab)
    _build_courses_tab(app, courses_tab)


def _my_enrolled_courses(app):
    return list_enrolled_courses(app.current_user["user_id"])


def _is_submitted(a):
    return bool(a["submitted_individually"]) or bool(a["submitted_as_group"])


def _assignment_status(a, now):
    """('Submitted' | 'Overdue' | 'Due Soon' | 'Upcoming', tag_name)."""
    if _is_submitted(a):
        return "Submitted", "status_submitted"
    due = datetime.strptime(a["due_date"], "%Y-%m-%d %H:%M")
    if due < now:
        return "Overdue", "status_overdue"
    if due <= now + timedelta(days=DUE_SOON_DAYS):
        return "Due Soon", "status_due_soon"
    return "Upcoming", "status_upcoming"


def _build_deadline_banner(app, parent):
    now = datetime.now()
    assignments = list_assignments_for_student_with_status(app.current_user["user_id"])
    alerts = [
        a for a in assignments
        if not _is_submitted(a) and datetime.strptime(a["due_date"], "%Y-%m-%d %H:%M") <= now + timedelta(days=DUE_SOON_DAYS)
    ]
    if not alerts:
        return

    banner = ttk.Frame(parent, style="Card.TFrame", padding=16)
    banner.pack(fill="x", padx=24, pady=(20, 0))

    overdue_count = sum(1 for a in alerts if datetime.strptime(a["due_date"], "%Y-%m-%d %H:%M") < now)
    due_soon_count = len(alerts) - overdue_count
    summary_bits = []
    if overdue_count:
        summary_bits.append(f"{overdue_count} overdue")
    if due_soon_count:
        summary_bits.append(f"{due_soon_count} due within {DUE_SOON_DAYS} days")
    ttk.Label(
        banner, text="Deadline Alerts — " + ", ".join(summary_bits), style="SubHeader.Card.TLabel"
    ).pack(anchor="w", pady=(0, 10))

    for a in alerts[:5]:
        due = datetime.strptime(a["due_date"], "%Y-%m-%d %H:%M")
        overdue = due < now
        tag_text = "OVERDUE" if overdue else "DUE SOON"
        tag_color = PALETTE["danger"] if overdue else PALETTE["warning"]

        row = ttk.Frame(banner, style="CardHeader.TFrame")
        row.pack(fill="x", pady=2)
        tk.Label(
            row, text=tag_text, bg=tag_color, fg="white", font=("Segoe UI", 8, "bold"), padx=6, pady=1
        ).pack(side="left")
        ttk.Label(
            row, text=f"  {a['title']} · {a['course_code']} — due {a['due_date']}",
            style="Card.TLabel",
        ).pack(side="left")

    if len(alerts) > 5:
        ttk.Label(
            banner, text=f"...and {len(alerts) - 5} more.", style="Muted.Card.TLabel"
        ).pack(anchor="w", pady=(4, 0))


def _build_assignments_tab(app, parent):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    frame.pack(fill="both", expand=True, padx=4, pady=4)

    ttk.Label(frame, text="Assignments", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 4))
    ttk.Label(
        frame, text="Double-click an assignment to see full details.", style="Muted.Card.TLabel"
    ).pack(anchor="w", pady=(0, 14))

    columns = ("course", "title", "type", "max_marks", "due", "file", "status")
    tree_container, tree = scrollable_treeview(frame, columns, height=16)
    for col, label, width in (
        ("course", "Course", 80),
        ("title", "Title", 190),
        ("type", "Type", 80),
        ("max_marks", "Max", 50),
        ("due", "Due", 130),
        ("file", "Attachment", 110),
        ("status", "Status", 90),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree.tag_configure("status_overdue", foreground=PALETTE["danger"])
    tree.tag_configure("status_due_soon", foreground=PALETTE["warning"])
    tree.tag_configure("status_submitted", foreground=PALETTE["text_muted"])
    tree_container.pack(fill="both", expand=True)

    assignment_lookup = {}

    def open_details(event=None):
        selection = tree.selection()
        if not selection:
            return
        a = assignment_lookup.get(selection[0])
        if a:
            open_assignment_details(app, a)

    tree.bind("<Double-1>", open_details)

    def refresh():
        tree.delete(*tree.get_children())
        assignment_lookup.clear()
        now = datetime.now()
        for a in list_assignments_for_student_with_status(app.current_user["user_id"]):
            iid = f"a{a['assignment_id']}"
            assignment_lookup[iid] = a
            file_name = os.path.basename(a["attachment_path"]) if a["attachment_path"] else "—"
            status_text, status_tag = _assignment_status(a, now)
            tree.insert(
                "", "end", iid=iid, tags=(status_tag,),
                values=(
                    a["course_code"], a["title"], a["type"], a["max_marks"], a["due_date"], file_name, status_text,
                ),
            )

    refresh()
    return refresh


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

    ttk.Label(right_frame, text="Recent Submissions", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 4))
    ttk.Label(
        right_frame, text="Double-click a row to see your grade and feedback.", style="Muted.Card.TLabel"
    ).pack(anchor="w", pady=(0, 14))
    columns = ("course", "title", "file", "submitted", "grade", "status")
    tree_container, tree = scrollable_treeview(right_frame, columns, height=16)
    for col, label, width in (
        ("course", "Course", 80),
        ("title", "Assignment", 150),
        ("file", "File", 140),
        ("submitted", "Submitted", 130),
        ("grade", "Grade", 80),
        ("status", "Status", 80),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree_container.pack(fill="both", expand=True)

    course_lookup = {}
    assignment_lookup = {}
    submission_lookup = {}

    def refresh_history():
        tree.delete(*tree.get_children())
        submission_lookup.clear()
        for s in list_submissions_by_student(app.current_user["user_id"]):
            graded = s["marks_obtained"] is not None
            grade_text = f"{s['marks_obtained']} / {s['max_marks']}" if graded else "—"
            iid = f"sub{s['submission_id']}"
            submission_lookup[iid] = s
            tree.insert(
                "", "end", iid=iid,
                values=(
                    s["course_code"], s["title"], os.path.basename(s["file_path"]), s["submitted_at"],
                    grade_text, "Graded" if graded else "Pending",
                ),
            )

    def open_grade(event=None):
        selection = tree.selection()
        if not selection:
            return
        s = submission_lookup.get(selection[0])
        if s:
            open_grade_view_dialog(app, s)

    tree.bind("<Double-1>", open_grade)

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
                # Keying/labeling by title alone breaks when two assignments share a
                # title (a real occurrence, not hypothetical) — whichever was
                # processed last silently wins the dict slot, so picking the other
                # one from the dropdown would still submit against the wrong
                # assignment_id. Folding the due date in, with a numbered fallback,
                # keeps every label distinct.
                label = f"{a['title']}  (due {a['due_date']})"
                suffix = 2
                unique_label = label
                while unique_label in assignment_lookup:
                    unique_label = f"{label} #{suffix}"
                    suffix += 1
                assignment_lookup[unique_label] = a["assignment_id"]
                labels.append(unique_label)
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
