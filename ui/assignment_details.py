import os
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from database import (
    UPLOADS_DIR,
    list_group_membership_for_assignment,
    list_groups_by_assignment,
    list_submissions_for_assignment,
    update_assignment,
    update_assignment_attachment,
)
from ui.date_picker import DateTimeEntry
from ui.grading import open_grade_entry_dialog
from ui.group_editor import open_group_editor
from ui.theme import PALETTE
from ui.widgets import ScrollableCard, scrollable_treeview


def open_assignment_details(app, assignment, on_updated=None):
    """Full details for one assignment. Faculty get an editable form (title, marks,
    due date, attachment, description); students get a strictly read-only view.
    Course and type are never editable here — changing either has structural
    implications (existing groups, existing submissions) handled elsewhere.

    GROUP assignments get a second tab showing their groups (view-only for everyone;
    editing membership stays in the Groups editor, reachable here via "Manage Groups"
    for faculty only). Faculty also get a Submissions tab (any type) to see who's
    turned something in and enter grades — never shown to students, since it would
    expose other students' submissions."""
    editable = app.current_user["role"] == "faculty"

    popup = tk.Toplevel(app)
    popup.title(f"Assignment — {assignment['title']}")
    popup.configure(background=PALETTE["card_bg"])
    popup.transient(app)
    popup.grab_set()
    popup.geometry("780x680")
    popup.minsize(640, 480)

    close_row = ttk.Frame(popup, style="Card.TFrame", padding=(24, 12, 24, 18))
    close_row.pack(side="bottom", fill="x")
    ttk.Button(close_row, text="Close", style="Accent.TButton", command=popup.destroy).pack(side="right")

    header = ttk.Frame(popup, style="Card.TFrame", padding=(24, 18, 24, 12))
    header.pack(side="top", fill="x")
    header_title_label = ttk.Label(header, text=assignment["title"], style="Header.Card.TLabel")
    header_title_label.pack(anchor="w")
    ttk.Label(
        header,
        text=f"{assignment['course_code']} - {assignment['course_name']}  ·  {assignment['type']}",
        style="Muted.Card.TLabel",
    ).pack(anchor="w", pady=(4, 0))

    tabs = [("Details", lambda parent: _build_details(parent, assignment, editable, on_updated, popup, header_title_label))]
    if assignment["type"] == "GROUP":
        tabs.append(("Groups", lambda parent: _build_groups_view(app, parent, assignment, editable)))
    if editable:
        tabs.append(("Submissions", lambda parent: _build_submissions_view(app, parent, assignment)))

    if len(tabs) > 1:
        notebook = ttk.Notebook(popup)
        notebook.pack(side="top", fill="both", expand=True, padx=24, pady=(12, 0))
        for label, builder in tabs:
            tab_frame = ttk.Frame(notebook, padding=0)
            notebook.add(tab_frame, text=f"  {label}  ")
            builder(tab_frame)
    else:
        tabs[0][1](popup)

    popup.update_idletasks()
    x = app.winfo_rootx() + 60
    y = app.winfo_rooty() + 40
    popup.geometry(f"+{x}+{y}")


def _build_details(parent, assignment, editable, on_updated, popup, header_title_label):
    card = ScrollableCard(parent, width=700, padding=24)
    card.pack(side="top", fill="both", expand=True, padx=4, pady=4)
    body = card.body

    def field_label(text):
        ttk.Label(body, text=text, style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")

    def static_field(label, value, pady=(0, 14)):
        field_label(label)
        ttk.Label(body, text=value, style="Card.TLabel").pack(anchor="w", pady=pady)

    # Course and type are shown but never editable here.
    static_field("Course", f"{assignment['course_code']} - {assignment['course_name']}")
    static_field("Type", assignment["type"])

    if not editable:
        _build_read_only_rest(body, assignment)
        return

    field_label("Title")
    title_entry = ttk.Entry(body, width=50)
    title_entry.insert(0, assignment["title"])
    title_entry.pack(anchor="w", fill="x", pady=(2, 14))

    marks_row = ttk.Frame(body, style="CardHeader.TFrame")
    marks_row.pack(fill="x", pady=(0, 14))
    marks_col = ttk.Frame(marks_row, style="CardHeader.TFrame")
    marks_col.pack(side="left", padx=(0, 24))
    ttk.Label(marks_col, text="Max Marks", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
    marks_entry = ttk.Entry(marks_col, width=14)
    marks_entry.insert(0, str(assignment["max_marks"]))
    marks_entry.pack(anchor="w", pady=(2, 0))

    due_col = ttk.Frame(marks_row, style="CardHeader.TFrame")
    due_col.pack(side="left")
    ttk.Label(due_col, text="Due Date", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
    due_picker = DateTimeEntry(due_col, width=16)
    due_picker.set(assignment["due_date"])
    due_picker.pack(anchor="w", pady=(2, 0))

    field_label("Attachment")
    attachment_row = ttk.Frame(body, style="CardHeader.TFrame")
    attachment_row.pack(fill="x", pady=(2, 14))
    current_name = os.path.basename(assignment["attachment_path"]) if assignment["attachment_path"] else "No file attached"
    attachment_label = ttk.Label(attachment_row, text=current_name, style="Muted.Card.TLabel")
    attachment_label.pack(side="left", fill="x", expand=True)
    attachment_state = {"path": assignment["attachment_path"], "changed": False}

    def browse_attachment():
        path = filedialog.askopenfilename(title="Select assignment attachment")
        if path:
            attachment_state["path"] = path
            attachment_state["changed"] = True
            attachment_label.configure(text=os.path.basename(path), foreground=PALETTE["text"])

    def remove_attachment():
        attachment_state["path"] = None
        attachment_state["changed"] = True
        attachment_label.configure(text="No file attached", foreground=PALETTE["text_muted"])

    ttk.Button(attachment_row, text="Remove", style="Secondary.TButton", command=remove_attachment).pack(
        side="right", padx=(8, 0)
    )
    ttk.Button(attachment_row, text="Replace...", style="Secondary.TButton", command=browse_attachment).pack(
        side="right"
    )

    field_label("Description")
    desc_frame = ttk.Frame(body, style="Card.TFrame")
    desc_frame.pack(fill="both", expand=True, pady=(4, 16))
    description_text = tk.Text(
        desc_frame, height=12, wrap="word", font=("Segoe UI", 10),
        background="white", foreground=PALETTE["text"],
        relief="solid", borderwidth=1, highlightthickness=0,
    )
    desc_scroll = ttk.Scrollbar(desc_frame, orient="vertical", command=description_text.yview)
    description_text.configure(yscrollcommand=desc_scroll.set)
    description_text.pack(side="left", fill="both", expand=True)
    desc_scroll.pack(side="right", fill="y")
    description_text.insert("1.0", assignment["description"] or "")

    def save_changes():
        title = title_entry.get().strip()
        if not title:
            messagebox.showwarning("Missing information", "Title is required.")
            return
        try:
            max_marks = float(marks_entry.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid marks", "Max marks must be a number.")
            return
        due_raw = due_picker.get().strip()
        try:
            datetime.strptime(due_raw, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showwarning("Invalid due date", "Use 'Pick date...' to choose a valid due date.")
            return
        description = description_text.get("1.0", "end").strip()

        update_assignment(assignment["assignment_id"], title, description, max_marks, due_raw)

        if attachment_state["changed"]:
            new_path = attachment_state["path"]
            if new_path and new_path != assignment["attachment_path"]:
                assignment_dir = os.path.join(UPLOADS_DIR, str(assignment["assignment_id"]))
                os.makedirs(assignment_dir, exist_ok=True)
                dest = os.path.join(assignment_dir, os.path.basename(new_path))
                shutil.copy2(new_path, dest)
                update_assignment_attachment(assignment["assignment_id"], dest)
                assignment["attachment_path"] = dest
            elif new_path is None:
                update_assignment_attachment(assignment["assignment_id"], None)
                assignment["attachment_path"] = None
            attachment_state["changed"] = False

        assignment["title"] = title
        assignment["description"] = description
        assignment["max_marks"] = max_marks
        assignment["due_date"] = due_raw
        popup.title(f"Assignment — {title}")
        header_title_label.configure(text=title)

        messagebox.showinfo("Saved", "Assignment updated.")
        if on_updated:
            on_updated()

    ttk.Button(body, text="Save Changes", style="Accent.TButton", command=save_changes).pack(fill="x")


def _build_read_only_rest(body, assignment):
    def static_field(label, value):
        ttk.Label(body, text=label, style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Label(body, text=value, style="Card.TLabel").pack(anchor="w", pady=(0, 14))

    static_field("Max Marks", str(assignment["max_marks"]))
    static_field("Due Date", assignment["due_date"])
    static_field("Created", assignment["created_at"])

    ttk.Label(body, text="Attachment", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
    attachment_path = assignment["attachment_path"]
    if attachment_path:
        att_row = ttk.Frame(body, style="CardHeader.TFrame")
        att_row.pack(anchor="w", fill="x", pady=(0, 14))
        ttk.Label(att_row, text=os.path.basename(attachment_path), style="Card.TLabel").pack(side="left")

        def open_attachment():
            try:
                os.startfile(attachment_path)
            except OSError as error:
                messagebox.showerror("Could not open file", str(error))

        ttk.Button(att_row, text="Open", style="Secondary.TButton", command=open_attachment).pack(
            side="left", padx=(12, 0)
        )
    else:
        ttk.Label(body, text="No attachment", style="Muted.Card.TLabel").pack(anchor="w", pady=(0, 14))

    ttk.Label(body, text="Description", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(
        anchor="w", pady=(0, 4)
    )
    desc_frame = ttk.Frame(body, style="Card.TFrame")
    desc_frame.pack(fill="both", expand=True)
    desc_text = tk.Text(
        desc_frame, height=12, wrap="word", font=("Segoe UI", 10),
        background="white", foreground=PALETTE["text"],
        relief="solid", borderwidth=1, highlightthickness=0,
    )
    desc_scroll = ttk.Scrollbar(desc_frame, orient="vertical", command=desc_text.yview)
    desc_text.configure(yscrollcommand=desc_scroll.set)
    desc_text.pack(side="left", fill="both", expand=True)
    desc_scroll.pack(side="right", fill="y")
    desc_text.insert("1.0", assignment["description"] or "No description provided.")
    desc_text.configure(state="disabled")


def _build_groups_view(app, parent, assignment, editable):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    frame.pack(side="top", fill="both", expand=True, padx=4, pady=4)

    top_row = ttk.Frame(frame, style="CardHeader.TFrame")
    top_row.pack(fill="x", pady=(0, 12))
    ttk.Label(top_row, text="Groups", style="SubHeader.Card.TLabel").pack(side="left")

    columns = ("email",)
    tree_container, tree = scrollable_treeview(frame, columns, height=14, show="tree headings")
    tree.heading("#0", text="Group / Student")
    tree.column("#0", width=260, anchor="w")
    tree.heading("email", text="Email")
    tree.column("email", width=220, anchor="w")
    tree.tag_configure("group_header", font=("Segoe UI", 10, "bold"), background=PALETTE["accent_soft"])
    tree_container.pack(fill="both", expand=True)

    empty_label = ttk.Label(frame, style="Muted.Card.TLabel")

    def refresh():
        tree.delete(*tree.get_children())
        empty_label.pack_forget()

        groups = list_groups_by_assignment(assignment["assignment_id"])
        membership = list_group_membership_for_assignment(assignment["course_id"], assignment["assignment_id"])

        by_group = {}
        unassigned = []
        for m in membership:
            if m["group_id"] is None:
                unassigned.append(m)
            else:
                by_group.setdefault(m["group_id"], []).append(m)

        if not groups:
            message = (
                'No groups configured yet — use "Manage Groups" to set them up.'
                if editable else "No groups have been set up for this assignment yet."
            )
            empty_label.configure(text=message)
            empty_label.pack(anchor="w", pady=(8, 0))

        for g in groups:
            node = f"g{g['group_id']}"
            tree.insert(
                "", "end", iid=node, text=f"{g['group_name']} ({g['member_count']})",
                open=True, tags=("group_header",),
            )
            for s in by_group.get(g["group_id"], []):
                tree.insert(node, "end", text=s["name"], values=(s["email"],))

        if unassigned:
            tree.insert(
                "", "end", iid="unassigned", text=f"Unassigned ({len(unassigned)})",
                open=True, tags=("group_header",),
            )
            for s in unassigned:
                tree.insert("unassigned", "end", text=s["name"], values=(s["email"],))

    if editable:
        ttk.Button(
            top_row, text="Manage Groups", style="Accent.TButton",
            command=lambda: open_group_editor(
                app, assignment["assignment_id"], assignment["course_id"], assignment["title"],
                on_change=refresh,
            ),
        ).pack(side="right")

    refresh()


def _build_submissions_view(app, parent, assignment):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    frame.pack(side="top", fill="both", expand=True, padx=4, pady=4)

    ttk.Label(frame, text="Submissions", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 4))
    ttk.Label(
        frame, text="Double-click a row to enter or update its grade.", style="Muted.Card.TLabel"
    ).pack(anchor="w", pady=(0, 14))

    columns = ("submitter", "file", "submitted", "grade")
    tree_container, tree = scrollable_treeview(frame, columns, height=14)
    for col, label, width in (
        ("submitter", "Submitted By", 160),
        ("file", "File", 220),
        ("submitted", "Submitted At", 150),
        ("grade", "Grade", 100),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree_container.pack(fill="both", expand=True)

    empty_label = ttk.Label(frame, text="No submissions yet.", style="Muted.Card.TLabel")
    submission_lookup = {}

    def refresh():
        tree.delete(*tree.get_children())
        submission_lookup.clear()
        empty_label.pack_forget()

        submissions = list_submissions_for_assignment(assignment["assignment_id"])
        if not submissions:
            empty_label.pack(anchor="w", pady=(8, 0))
            return

        for s in submissions:
            submitter = s["student_name"] or s["group_name"] or "Unknown"
            grade_text = (
                f"{s['marks_obtained']} / {assignment['max_marks']}"
                if s["marks_obtained"] is not None else "Not graded"
            )
            iid = f"sub{s['submission_id']}"
            submission_lookup[iid] = s
            tree.insert(
                "", "end", iid=iid,
                values=(submitter, os.path.basename(s["file_path"]), s["submitted_at"], grade_text),
            )

    def open_grading(event=None):
        selection = tree.selection()
        if not selection:
            return
        s = submission_lookup.get(selection[0])
        if s:
            open_grade_entry_dialog(app, s, assignment, on_saved=refresh)

    tree.bind("<Double-1>", open_grading)
    refresh()
