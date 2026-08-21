import os
import tkinter as tk
from tkinter import messagebox, ttk

from database import create_or_update_grade
from ui.theme import PALETTE


def open_grade_entry_dialog(app, submission, assignment, on_saved=None):
    """Faculty: enter or update marks + feedback for one submission."""
    submitter = submission["student_name"] or submission["group_name"] or "Unknown"

    popup = tk.Toplevel(app)
    popup.title(f"Grade — {submitter}")
    popup.configure(background=PALETTE["card_bg"])
    popup.transient(app)
    popup.grab_set()
    popup.resizable(False, False)

    card = ttk.Frame(popup, style="Card.TFrame", padding=24)
    card.pack(fill="both", expand=True)

    ttk.Label(card, text=f"Grade: {submitter}", style="Header.Card.TLabel").pack(anchor="w")
    ttk.Label(
        card, text=f"{assignment['title']} · Max marks: {assignment['max_marks']}",
        style="Muted.Card.TLabel",
    ).pack(anchor="w", pady=(2, 2))
    ttk.Label(card, text=f"Submitted: {submission['submitted_at']}", style="Muted.Card.TLabel").pack(
        anchor="w", pady=(0, 16)
    )

    file_row = ttk.Frame(card, style="CardHeader.TFrame")
    file_row.pack(fill="x", pady=(0, 16))
    ttk.Label(file_row, text=os.path.basename(submission["file_path"]), style="Card.TLabel").pack(side="left")

    def open_file():
        try:
            os.startfile(submission["file_path"])
        except OSError as error:
            messagebox.showerror("Could not open file", str(error))

    ttk.Button(file_row, text="Open File", style="Secondary.TButton", command=open_file).pack(
        side="left", padx=(12, 0)
    )

    ttk.Label(card, text="Marks obtained", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
    marks_entry = ttk.Entry(card, width=14)
    if submission["marks_obtained"] is not None:
        marks_entry.insert(0, str(submission["marks_obtained"]))
    marks_entry.pack(anchor="w", pady=(2, 16))

    ttk.Label(card, text="Feedback", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(
        anchor="w", pady=(0, 4)
    )
    feedback_frame = ttk.Frame(card, style="Card.TFrame")
    feedback_frame.pack(fill="both", expand=True, pady=(0, 16))
    feedback_text = tk.Text(
        feedback_frame, height=8, width=44, wrap="word", font=("Segoe UI", 10),
        background="white", foreground=PALETTE["text"],
        relief="solid", borderwidth=1, highlightthickness=0,
    )
    feedback_scroll = ttk.Scrollbar(feedback_frame, orient="vertical", command=feedback_text.yview)
    feedback_text.configure(yscrollcommand=feedback_scroll.set)
    feedback_text.pack(side="left", fill="both", expand=True)
    feedback_scroll.pack(side="right", fill="y")
    if submission["feedback"]:
        feedback_text.insert("1.0", submission["feedback"])

    def save():
        marks_raw = marks_entry.get().strip()
        try:
            marks = float(marks_raw)
        except ValueError:
            messagebox.showwarning("Invalid marks", "Marks obtained must be a number.")
            return
        if marks < 0 or marks > assignment["max_marks"]:
            messagebox.showwarning(
                "Invalid marks", f"Marks obtained must be between 0 and {assignment['max_marks']}."
            )
            return
        feedback = feedback_text.get("1.0", "end").strip()

        create_or_update_grade(submission["submission_id"], marks, feedback, app.current_user["user_id"])

        popup.destroy()
        if on_saved:
            on_saved()

    button_row = ttk.Frame(card, style="CardHeader.TFrame")
    button_row.pack(fill="x")
    ttk.Button(button_row, text="Cancel", style="Secondary.TButton", command=popup.destroy).pack(
        side="right", padx=(8, 0)
    )
    ttk.Button(button_row, text="Save Grade", style="Accent.TButton", command=save).pack(side="right")

    popup.update_idletasks()
    x = app.winfo_rootx() + 80
    y = app.winfo_rooty() + 60
    popup.geometry(f"+{x}+{y}")


def open_grade_view_dialog(app, submission):
    """Student: read-only grade + feedback for one of their own submissions."""
    popup = tk.Toplevel(app)
    popup.title("Grade & Feedback")
    popup.configure(background=PALETTE["card_bg"])
    popup.transient(app)
    popup.grab_set()
    popup.resizable(False, False)

    card = ttk.Frame(popup, style="Card.TFrame", padding=24)
    card.pack(fill="both", expand=True)

    ttk.Label(card, text=submission["title"], style="Header.Card.TLabel", wraplength=380).pack(anchor="w")

    marks = submission["marks_obtained"]
    if marks is None:
        ttk.Label(card, text="Status: Pending", style="Muted.Card.TLabel").pack(anchor="w", pady=(6, 16))
    else:
        ttk.Label(
            card, text=f"Grade: {marks} / {submission['max_marks']}",
            style="Card.TLabel", font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", pady=(6, 4))
        ttk.Label(card, text=f"Graded: {submission['graded_at']}", style="Muted.Card.TLabel").pack(
            anchor="w", pady=(0, 16)
        )

    ttk.Label(card, text="Feedback", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(
        anchor="w", pady=(0, 4)
    )
    feedback_frame = ttk.Frame(card, style="Card.TFrame")
    feedback_frame.pack(fill="both", expand=True, pady=(0, 16))
    feedback_text = tk.Text(
        feedback_frame, height=6, width=44, wrap="word", font=("Segoe UI", 10),
        background="white", foreground=PALETTE["text"],
        relief="solid", borderwidth=1, highlightthickness=0,
    )
    feedback_text.pack(side="left", fill="both", expand=True)
    feedback_text.insert(
        "1.0", submission["feedback"] or "No feedback yet — your submission hasn't been graded."
    )
    feedback_text.configure(state="disabled")

    ttk.Button(card, text="Close", style="Accent.TButton", command=popup.destroy).pack(fill="x")

    popup.update_idletasks()
    x = app.winfo_rootx() + 80
    y = app.winfo_rooty() + 60
    popup.geometry(f"+{x}+{y}")
