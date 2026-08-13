import os
import tkinter as tk
from tkinter import messagebox, ttk

from database import list_group_membership_for_assignment, list_groups_by_assignment
from ui.group_editor import open_group_editor
from ui.theme import PALETTE
from ui.widgets import ScrollableCard, scrollable_treeview


def open_assignment_details(app, assignment):
    """Read-only full details for one assignment. GROUP assignments get a second
    tab showing their groups (view-only — editing stays in the Groups editor,
    reachable here via "Manage Groups")."""
    popup = tk.Toplevel(app)
    popup.title(f"Assignment — {assignment['title']}")
    popup.configure(background=PALETTE["card_bg"])
    popup.transient(app)
    popup.grab_set()
    popup.geometry("780x660")
    popup.minsize(640, 460)

    close_row = ttk.Frame(popup, style="Card.TFrame", padding=(24, 12, 24, 18))
    close_row.pack(side="bottom", fill="x")
    ttk.Button(close_row, text="Close", style="Accent.TButton", command=popup.destroy).pack(side="right")

    header = ttk.Frame(popup, style="Card.TFrame", padding=(24, 18, 24, 12))
    header.pack(side="top", fill="x")
    ttk.Label(header, text=assignment["title"], style="Header.Card.TLabel").pack(anchor="w")
    ttk.Label(
        header,
        text=f"{assignment['course_code']} - {assignment['course_name']}  ·  {assignment['type']}",
        style="Muted.Card.TLabel",
    ).pack(anchor="w", pady=(4, 0))

    if assignment["type"] == "GROUP":
        notebook = ttk.Notebook(popup)
        notebook.pack(side="top", fill="both", expand=True, padx=24, pady=(12, 0))
        details_tab = ttk.Frame(notebook, padding=0)
        groups_tab = ttk.Frame(notebook, padding=0)
        notebook.add(details_tab, text="  Details  ")
        notebook.add(groups_tab, text="  Groups  ")
        _build_details(details_tab, assignment)
        _build_groups_view(app, groups_tab, assignment)
    else:
        _build_details(popup, assignment)

    popup.update_idletasks()
    x = app.winfo_rootx() + 60
    y = app.winfo_rooty() + 40
    popup.geometry(f"+{x}+{y}")


def _build_details(parent, assignment):
    card = ScrollableCard(parent, width=700, padding=24)
    card.pack(side="top", fill="both", expand=True, padx=4, pady=4)
    body = card.body

    def field(label, value):
        ttk.Label(body, text=label, style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Label(body, text=value, style="Card.TLabel").pack(anchor="w", pady=(0, 14))

    field("Course", f"{assignment['course_code']} - {assignment['course_name']}")
    field("Type", assignment["type"])
    field("Max Marks", str(assignment["max_marks"]))
    field("Due Date", assignment["due_date"])
    field("Created", assignment["created_at"])

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


def _build_groups_view(app, parent, assignment):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=24)
    frame.pack(side="top", fill="both", expand=True, padx=4, pady=4)

    top_row = ttk.Frame(frame, style="CardHeader.TFrame")
    top_row.pack(fill="x", pady=(0, 12))
    ttk.Label(top_row, text="Groups", style="SubHeader.Card.TLabel").pack(side="left")
    ttk.Button(
        top_row, text="Manage Groups", style="Accent.TButton",
        command=lambda: open_group_editor(
            app, assignment["assignment_id"], assignment["course_id"], assignment["title"]
        ),
    ).pack(side="right")

    columns = ("email",)
    tree_container, tree = scrollable_treeview(frame, columns, height=14, show="tree headings")
    tree.heading("#0", text="Group / Student")
    tree.column("#0", width=260, anchor="w")
    tree.heading("email", text="Email")
    tree.column("email", width=220, anchor="w")
    tree.tag_configure("group_header", font=("Segoe UI", 10, "bold"), background=PALETTE["accent_soft"])
    tree_container.pack(fill="both", expand=True)

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
        ttk.Label(
            frame, text='No groups configured yet — use "Manage Groups" to set them up.',
            style="Muted.Card.TLabel",
        ).pack(anchor="w", pady=(8, 0))

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
