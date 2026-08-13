import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from auth import hash_password
from database import create_user, list_users
from ui.widgets import ScrollableCard, scrollable_treeview


def show(app):
    app.build_header(app.container)

    notebook = ttk.Notebook(app.container)
    notebook.pack(fill="both", expand=True, padx=24, pady=(20, 24))

    users_tab = ttk.Frame(notebook, padding=0)
    notebook.add(users_tab, text="  Manage Users  ")

    _build_users_tab(users_tab)


def _build_users_tab(parent):
    left_card = ScrollableCard(parent, width=300)
    left_card.pack(side="left", fill="y", padx=(0, 20), pady=4)
    left_frame = left_card.body

    right_frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    right_frame.pack(side="right", fill="both", expand=True, pady=4)

    ttk.Label(left_frame, text="Create User", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 4))
    ttk.Label(left_frame, text="Add a student, faculty, or admin account.", style="Muted.Card.TLabel").pack(
        anchor="w", pady=(0, 16)
    )

    ttk.Label(left_frame, text="Full name", style="Card.TLabel").pack(anchor="w")
    name_entry = ttk.Entry(left_frame, width=30)
    name_entry.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Email", style="Card.TLabel").pack(anchor="w")
    email_entry = ttk.Entry(left_frame, width=30)
    email_entry.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Temporary password", style="Card.TLabel").pack(anchor="w")
    password_entry = ttk.Entry(left_frame, width=30, show="•")
    password_entry.pack(pady=(2, 12))

    ttk.Label(left_frame, text="Role", style="Card.TLabel").pack(anchor="w")
    role_var = tk.StringVar(value="student")
    role_dropdown = ttk.Combobox(
        left_frame,
        textvariable=role_var,
        state="readonly",
        values=("student", "faculty", "admin"),
        width=27,
    )
    role_dropdown.pack(pady=(2, 20))

    ttk.Label(right_frame, text="All Users", style="SubHeader.Card.TLabel").pack(anchor="w", pady=(0, 14))

    columns = ("id", "name", "email", "role", "created")
    tree_container, tree = scrollable_treeview(right_frame, columns)
    for col, label, width in (
        ("id", "ID", 40),
        ("name", "Name", 140),
        ("email", "Email", 190),
        ("role", "Role", 80),
        ("created", "Created", 140),
    ):
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor="w")
    tree_container.pack(fill="both", expand=True)

    def refresh():
        tree.delete(*tree.get_children())
        for user in list_users():
            tree.insert(
                "", "end",
                values=(user["user_id"], user["name"], user["email"], user["role"], user["created_at"]),
            )

    def create():
        name = name_entry.get().strip()
        email = email_entry.get().strip()
        password = password_entry.get().strip()
        role = role_var.get()

        if not name or not email or not password:
            messagebox.showwarning("Missing information", "Name, email, and password are all required.")
            return

        try:
            create_user(name, email, hash_password(password), role)
        except sqlite3.IntegrityError:
            messagebox.showerror("Could not create user", f"A user with email '{email}' already exists.")
            return

        messagebox.showinfo("User created", f"{role.capitalize()} account created for {name}.")
        name_entry.delete(0, "end")
        email_entry.delete(0, "end")
        password_entry.delete(0, "end")
        refresh()

    ttk.Button(left_frame, text="Create User", style="Accent.TButton", command=create).pack(fill="x")

    refresh()
