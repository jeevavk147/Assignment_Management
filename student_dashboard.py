# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 15:17:30 2026

@author: saura
"""

import tkinter as tk
from tkinter import messagebox, ttk

# --- MOCK DATABASE ---
# Pre-populated student data
STUDENT_DATA = {
    "saurabh": {
        "password": "pass1",
        "name": "Saurabh Kumar",
        "submissions": [
            {
                "assignment": "Assignment 1: Software Architecure",
                "file_name": "SA_assign_sk.pdf",
                "submitted_date": "2026-08-15",
                "grade": "A (95%)",
                "feedback": "Excellent work! Well-explained architecture and diagrams.",
            },
            {
                "assignment": "Assignment 2: Cloud Computing",
                "file_name": "cloud_sk.pdf",
                "submitted_date": "2026-08-13",
                "grade": "B+ (88%)",
                "feedback": "Good work but more detailed explaination required.",
            },
            {
                "assignment": "Assignment 3: Agile Software Process",
                "file_name": "agile.pdf",
                "submitted_date": "2026-08-20",
                "grade": "Pending",
                "feedback": "Submission received. Awaiting grading.",
            },
        ],
    },
    "jeeva": {
        "password": "pass2",
        "name": "Jeevandham V",
        "submissions": [
            {
                "assignment": "Assignment 1: Software Architecure",
                "file_name": "SA_assignment_jeeva.pdf",
                "submitted_date": "2026-08-16",
                "grade": "B+ (85%)",
                "feedback": "Good work but detailed diagram needed.",
            },
            {
                "assignment": "Assignment 2: Cloud Computing",
                "file_name": "cloud_jeeva.pdf",
                "submitted_date": "2026-08-11",
                "grade": "A (92%)",
                "feedback": "Excellent and good use of AWS.",
            },
            {
                "assignment": "Assignment 3: Agile Software Process",
                "file_name": "agile_assign.pdf",
                "submitted_date": "2026-08-18",
                "grade": "Pending",
                "feedback": "Submission received. Awaiting grading.",
            },
        ],
    },
}


class StudentPortalApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Student Academic Portal")
        self.root.geometry("800x550")
        self.root.resizable(False, False)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Container frame to hold screens
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        # Show Login Screen by default
        self.show_login_screen()

    # --- LOGIN SCREEN ---
    def show_login_screen(self):
        self.clear_container()

        login_frame = ttk.Frame(self.container, padding=30)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(
            login_frame, text="Student Portal Login", font=("Helvetica", 18, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Username
        ttk.Label(
            login_frame, text="Username:", font=("Helvetica", 11)
        ).grid(row=1, column=0, sticky="e", pady=8, padx=5)
        self.username_entry = ttk.Entry(login_frame, width=25, font=("Helvetica", 11))
        self.username_entry.grid(row=1, column=1, pady=8, padx=5)

        # Password
        ttk.Label(
            login_frame, text="Password:", font=("Helvetica", 11)
        ).grid(row=2, column=0, sticky="e", pady=8, padx=5)
        self.password_entry = ttk.Entry(
            login_frame, width=25, font=("Helvetica", 11), show="*"
        )
        self.password_entry.grid(row=2, column=1, pady=8, padx=5)

        # Login Button
        login_btn = ttk.Button(
            login_frame, text="Login", command=self.handle_login
        )
        login_btn.grid(row=3, column=0, columnspan=2, pady=(20, 0))

        # Demo Credentials Hint
        hint_label = ttk.Label(
            login_frame,
            #text="Demo Login -> User: john_doe | Pass: password123",
            font=("Helvetica", 9, "italic"),
            foreground="gray",
        )
        hint_label.grid(row=4, column=0, columnspan=2, pady=(15, 0))

    def handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if username in STUDENT_DATA and STUDENT_DATA[username]["password"] == password:
            self.show_dashboard(username)
        else:
            messagebox.showerror("Error", "Invalid Username or Password!")

    # --- DASHBOARD SCREEN ---
    def show_dashboard(self, username):
        self.clear_container()
        student = STUDENT_DATA[username]

        # Top Bar
        top_bar = ttk.Frame(self.container, padding=10)
        top_bar.pack(fill="x", side="top")

        ttk.Label(
            top_bar,
            text=f"Welcome, {student['name']}",
            font=("Helvetica", 14, "bold"),
        ).pack(side="left")
        logout_btn = ttk.Button(
            top_bar, text="Logout", command=self.show_login_screen
        )
        logout_btn.pack(side="right")

        ttk.Separator(self.container, orient="horizontal").pack(
            fill="x", pady=5
        )

        # Notebook (Tabbed View)
        notebook = ttk.Notebook(self.container)
        notebook.pack(fill="both", expand=True, padx=15, pady=10)

        # Tab 1: Submission History
        history_tab = ttk.Frame(notebook, padding=10)
        notebook.add(history_tab, text=" Submission History ")
        self.build_history_tab(history_tab, student["submissions"])

        # Tab 2: Grades & Feedback
        grades_tab = ttk.Frame(notebook, padding=10)
        notebook.add(grades_tab, text=" Grades & Feedback ")
        self.build_grades_tab(grades_tab, student["submissions"])

    # --- TAB 1: SUBMISSION HISTORY ---
    def build_history_tab(self, parent, submissions):
        columns = ("assignment", "file_name", "date", "status")
        tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )

        tree.heading("assignment", text="Assignment Name")
        tree.heading("file_name", text="Submitted File")
        tree.heading("date", text="Date Submitted")
        tree.heading("status", text="Grading Status")

        tree.column("assignment", width=220)
        tree.column("file_name", width=220)
        tree.column("date", width=120, anchor="center")
        tree.column("status", width=120, anchor="center")

        for item in submissions:
            status = "Graded" if item["grade"] != "Pending" else "Pending"
            tree.insert(
                "",
                "end",
                values=(
                    item["assignment"],
                    item["file_name"],
                    item["submitted_date"],
                    status,
                ),
            )

        tree.pack(fill="both", expand=True)

    # --- TAB 2: GRADES & FEEDBACK ---
    def build_grades_tab(self, parent, submissions):
        columns = ("assignment", "grade", "feedback")
        tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=8
        )

        tree.heading("assignment", text="Assignment Name")
        tree.heading("grade", text="Grade")
        tree.heading("feedback", text="Teacher Feedback")

        tree.column("assignment", width=200)
        tree.column("grade", width=100, anchor="center")
        tree.column("feedback", width=420)

        for item in submissions:
            tree.insert(
                "",
                "end",
                values=(item["assignment"], item["grade"], item["feedback"]),
            )

        tree.pack(fill="both", expand=True, pady=(0, 10))

        # Instruction label for details
        info_lbl = ttk.Label(
            parent,
            text="* Double-click any row to view full detailed feedback.",
            font=("Helvetica", 9, "italic"),
            foreground="gray",
        )
        info_lbl.pack(anchor="w")

        # Double-click event to open detailed modal window
        def on_row_double_click(event):
            selected = tree.selection()
            if selected:
                item_data = tree.item(selected[0])["values"]
                self.show_feedback_modal(
                    item_data[0], item_data[1], item_data[2]
                )

        tree.bind("<Double-1>", on_row_double_click)

    # --- FEEDBACK DETAIL MODAL WINDOW ---
    def show_feedback_modal(self, assignment, grade, feedback):
        modal = tk.Toplevel(self.root)
        modal.title("Grade & Feedback Details")
        modal.geometry("400x250")
        modal.grab_set()  # Make modal focus-exclusive

        ttk.Label(
            modal, text=assignment, font=("Helvetica", 12, "bold"), wraplength=380
        ).pack(anchor="w", padx=15, pady=(15, 5))
        ttk.Label(
            modal, text=f"Grade: {grade}", font=("Helvetica", 11, "bold"), foreground="green"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ttk.Label(modal, text="Teacher Feedback:", font=("Helvetica", 10, "underline")).pack(
            anchor="w", padx=15
        )

        fb_text = tk.Text(
            modal,
            height=5,
            width=40,
            wrap="word",
            font=("Helvetica", 10),
            bg="#f0f0f0",
            bd=0,
        )
        fb_text.insert("1.0", feedback)
        fb_text.config(state="disabled")
        fb_text.pack(fill="both", expand=True, padx=15, pady=5)

        ttk.Button(modal, text="Close", command=modal.destroy).pack(pady=10)

    # --- UTILITY METHODS ---
    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()


# --- ENTRY POINT ---
if __name__ == "__main__":
    root = tk.Tk()
    app = StudentPortalApp(root)
    root.mainloop()