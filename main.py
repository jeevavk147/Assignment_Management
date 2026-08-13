import tkinter as tk
from tkinter import ttk

from database import initialize_db
from ui import admin_dashboard, faculty_dashboard, login_screen, student_dashboard, theme


class AssignmentApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assignment Management System")
        self.current_user = None

        theme.apply(self)
        self._center_window(1000, 650)

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        login_screen.show(self)

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(860, 560)

    def clear_screen(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def build_header(self, parent):
        header = ttk.Frame(parent, style="Card.TFrame", padding=(24, 16))
        header.pack(fill="x")

        title_frame = ttk.Frame(header, style="CardHeader.TFrame")
        title_frame.pack(side="left")
        ttk.Label(title_frame, text="Assignment Management System", style="SubHeader.Card.TLabel").pack(anchor="w")
        ttk.Label(
            title_frame,
            text=f"{self.current_user['name']} · {self.current_user['role'].capitalize()}",
            style="Muted.Card.TLabel",
        ).pack(anchor="w")

        ttk.Button(header, text="Logout", style="Secondary.TButton", command=lambda: login_screen.show(self)).pack(
            side="right"
        )

        ttk.Frame(parent, height=1, style="Card.TFrame").pack(fill="x")

    def show_dashboard_screen(self):
        self.clear_screen()

        role = self.current_user["role"]
        if role == "admin":
            admin_dashboard.show(self)
        elif role == "faculty":
            faculty_dashboard.show(self)
        else:
            student_dashboard.show(self)


if __name__ == "__main__":
    initialize_db()
    app = AssignmentApp()
    app.mainloop()
