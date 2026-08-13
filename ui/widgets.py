import tkinter as tk
from tkinter import ttk

from ui.theme import PALETTE


class ScrollableCard(ttk.Frame):
    """A bordered card whose content scrolls vertically when it doesn't fit the window."""

    def __init__(self, parent, width=340, padding=24, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        canvas = tk.Canvas(
            self, background=PALETTE["card_bg"], highlightthickness=0, borderwidth=0, width=width
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.body = ttk.Frame(canvas, style="Card.TFrame", padding=padding)
        window = canvas.create_window((0, 0), window=self.body, anchor="nw")

        def on_body_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(window, width=event.width)

        self.body.bind("<Configure>", on_body_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))


def scrollable_treeview(parent, columns, height=15, show="headings"):
    """A Treeview with an attached vertical scrollbar, wrapped in a matching frame.
    Pass show="tree headings" for a hierarchical (parent/child) tree."""
    container = ttk.Frame(parent, style="Card.TFrame")
    tree = ttk.Treeview(container, columns=columns, show=show, height=height)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return container, tree
