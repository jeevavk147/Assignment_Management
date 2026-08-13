import calendar
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ui.theme import PALETTE

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class DateTimeEntry(ttk.Frame):
    """A read-only entry + button that opens a calendar/time popup.

    .get() / .set() work with 'YYYY-MM-DD HH:MM' strings, matching what
    ASSIGNMENTS.due_date expects.
    """

    def __init__(self, parent, width=20, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self.var = tk.StringVar(value="")

        entry = ttk.Entry(self, textvariable=self.var, width=width, state="readonly")
        entry.pack(side="left")
        ttk.Button(self, text="Pick date...", style="Secondary.TButton", command=self._open_picker).pack(
            side="left", padx=(8, 0)
        )

    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value)

    def _open_picker(self):
        now = datetime.now()
        try:
            current = datetime.strptime(self.var.get(), "%Y-%m-%d %H:%M")
        except ValueError:
            current = now

        popup = tk.Toplevel(self)
        popup.title("Select due date")
        popup.configure(background=PALETTE["card_bg"])
        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        popup.resizable(False, False)

        state = {"year": current.year, "month": current.month, "day": current.day}

        header = ttk.Frame(popup, style="Card.TFrame", padding=10)
        header.pack(fill="x")
        ttk.Button(header, text="<", width=3, style="Secondary.TButton", command=lambda: shift_month(-1)).pack(
            side="left"
        )
        month_label = ttk.Label(header, style="SubHeader.Card.TLabel", anchor="center")
        month_label.pack(side="left", expand=True, fill="x")
        ttk.Button(header, text=">", width=3, style="Secondary.TButton", command=lambda: shift_month(1)).pack(
            side="right"
        )

        grid_frame = ttk.Frame(popup, style="Card.TFrame", padding=(10, 0, 10, 10))
        grid_frame.pack()

        def render_month():
            for widget in grid_frame.winfo_children():
                widget.destroy()
            month_label.configure(text=f"{MONTH_NAMES[state['month'] - 1]} {state['year']}")

            for col, name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
                ttk.Label(grid_frame, text=name, style="Muted.Card.TLabel", width=4, anchor="center").grid(
                    row=0, column=col, pady=(0, 4)
                )

            cal = calendar.Calendar(firstweekday=0)
            row = 1
            for week in cal.monthdayscalendar(state["year"], state["month"]):
                for col, day in enumerate(week):
                    if day == 0:
                        ttk.Label(grid_frame, text="", width=4).grid(row=row, column=col)
                        continue
                    selected = day == state["day"]
                    btn = tk.Button(
                        grid_frame,
                        text=str(day),
                        width=3,
                        relief="flat",
                        borderwidth=0,
                        background=PALETTE["accent"] if selected else PALETTE["card_bg"],
                        foreground="white" if selected else PALETTE["text"],
                        activebackground=PALETTE["accent_soft"],
                        command=lambda d=day: pick_day(d),
                    )
                    btn.grid(row=row, column=col, padx=1, pady=1)
                row += 1

        def shift_month(delta):
            total = state["month"] - 1 + delta
            state["year"] += total // 12
            state["month"] = total % 12 + 1
            last_day = calendar.monthrange(state["year"], state["month"])[1]
            state["day"] = min(state["day"], last_day)
            render_month()

        def pick_day(day):
            state["day"] = day
            render_month()

        render_month()

        time_frame = ttk.Frame(popup, style="Card.TFrame", padding=(10, 0, 10, 10))
        time_frame.pack(fill="x")
        ttk.Label(time_frame, text="Time:", style="Card.TLabel").pack(side="left")
        hour_var = tk.StringVar(value=f"{current.hour:02d}")
        minute_var = tk.StringVar(value=f"{current.minute:02d}")
        ttk.Spinbox(time_frame, from_=0, to=23, width=3, textvariable=hour_var, format="%02.0f", wrap=True).pack(
            side="left", padx=(8, 2)
        )
        ttk.Label(time_frame, text=":", style="Card.TLabel").pack(side="left")
        ttk.Spinbox(time_frame, from_=0, to=59, width=3, textvariable=minute_var, format="%02.0f", wrap=True).pack(
            side="left", padx=(2, 0)
        )

        button_row = ttk.Frame(popup, style="Card.TFrame", padding=10)
        button_row.pack(fill="x")

        def confirm():
            try:
                hour = int(hour_var.get())
                minute = int(minute_var.get())
            except ValueError:
                hour, minute = 23, 59
            value = f"{state['year']:04d}-{state['month']:02d}-{state['day']:02d} {hour:02d}:{minute:02d}"
            self.var.set(value)
            popup.destroy()

        ttk.Button(button_row, text="Cancel", style="Secondary.TButton", command=popup.destroy).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(button_row, text="Use this date", style="Accent.TButton", command=confirm).pack(side="right")

        popup.update_idletasks()
        x = self.winfo_toplevel().winfo_rootx() + 60
        y = self.winfo_toplevel().winfo_rooty() + 60
        popup.geometry(f"+{x}+{y}")
