import tkinter as tk
from tkinter import ttk, messagebox

from auth import login as auth_login
from ui.theme import PALETTE


def show(app):
    """Render the login screen inside app.container."""
    app.clear_screen()
    app.current_user = None

    card = ttk.Frame(app.container, style="Card.TFrame", padding=44)
    card.place(relx=0.5, rely=0.5, anchor="center")

    badge = tk.Frame(card, bg=PALETTE["accent"], width=52, height=52)
    badge.grid(row=0, column=0, columnspan=2, pady=(0, 14))
    badge.grid_propagate(False)
    tk.Label(badge, text="AM", bg=PALETTE["accent"], fg="white", font=("Segoe UI", 15, "bold")).place(
        relx=0.5, rely=0.5, anchor="center"
    )

    ttk.Label(card, text="Assignment Management System", style="Header.Card.TLabel").grid(
        row=1, column=0, columnspan=2, pady=(0, 4)
    )
    ttk.Label(card, text="Sign in to continue", style="Muted.Card.TLabel").grid(
        row=2, column=0, columnspan=2, pady=(0, 26)
    )

    ttk.Label(card, text="Email", style="Card.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 4))
    email_entry = ttk.Entry(card, width=34)
    email_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 16))

    ttk.Label(card, text="Password", style="Card.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))
    password_entry = ttk.Entry(card, width=34, show="•")
    password_entry.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 24))

    def attempt_login(event=None):
        email = email_entry.get().strip()
        password = password_entry.get().strip()
        if not email or not password:
            messagebox.showwarning("Login failed", "Please enter both email and password.")
            return

        user = auth_login(email, password)
        if user is None:
            messagebox.showerror("Login failed", "Invalid email or password.")
            return

        app.current_user = user
        app.show_dashboard_screen()

    ttk.Button(card, text="Login", style="Accent.TButton", command=attempt_login).grid(
        row=7, column=0, columnspan=2, sticky="ew"
    )

    password_entry.bind("<Return>", attempt_login)
    email_entry.focus_set()
