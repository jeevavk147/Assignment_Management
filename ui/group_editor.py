import tkinter as tk
from tkinter import ttk, messagebox

from database import auto_distribute_groups, list_group_membership_for_assignment, list_groups_by_assignment, set_student_group
from ui.theme import PALETTE
from ui.widgets import scrollable_treeview

UNASSIGNED_NODE = "unassigned"


def open_group_editor(app, assignment_id, course_id, assignment_title, on_change=None):
    """Per-assignment group roster: only students enrolled in `course_id`, only groups
    belonging to `assignment_id`. Nothing here is shared with any other assignment.

    Groups are always auto-named "Group 1", "Group 2"... and only ever created via the
    size-based generator below — there's no manual add/rename/delete of a group.
    Membership is changed by dragging a student onto another group's section, or by
    removing them back to Unassigned; nothing here ever evicts an existing member just
    because a group grows past its target size."""
    popup = tk.Toplevel(app)
    popup.title(f"Groups — {assignment_title}")
    popup.configure(background=PALETTE["card_bg"])
    popup.transient(app)
    popup.grab_set()
    popup.geometry("820x680")
    popup.minsize(680, 460)

    # Footer pinned to the bottom FIRST so it's always visible regardless of roster size.
    close_row = ttk.Frame(popup, style="Card.TFrame", padding=(24, 12, 24, 18))
    close_row.pack(side="bottom", fill="x")
    ttk.Button(close_row, text="Done", style="Accent.TButton", command=popup.destroy).pack(side="right")

    header = ttk.Frame(popup, style="Card.TFrame", padding=(24, 18, 24, 12))
    header.pack(side="top", fill="x")
    ttk.Label(header, text=f"Groups for: {assignment_title}", style="SubHeader.Card.TLabel").pack(anchor="w")
    ttk.Label(
        header,
        text="Only students enrolled in this course are listed, and these groups belong to this "
             "assignment only — no other assignment shares them.",
        style="Muted.Card.TLabel",
    ).pack(anchor="w", pady=(4, 0))

    setup_row = ttk.Frame(popup, style="Card.TFrame", padding=(24, 0, 24, 8))
    setup_row.pack(side="top", fill="x")
    ttk.Label(setup_row, text="Students per group:", style="Card.TLabel").pack(side="left")
    size_var = tk.StringVar(value="3")
    ttk.Spinbox(setup_row, from_=1, to=30, width=5, textvariable=size_var).pack(side="left", padx=(8, 8))
    generate_button = ttk.Button(setup_row, text="Generate / Fill Groups", style="Accent.TButton")
    generate_button.pack(side="left")
    ttk.Label(
        popup,
        text="Creates enough \"Group N\" groups for that size, randomly places only students with no "
             "group yet, and tops up the smallest groups first. Safe to run again after new enrollments "
             "— it never moves someone already placed. Group sizes can end up uneven; that's expected.",
        style="Muted.Card.TLabel", wraplength=760, justify="left",
    ).pack(side="top", anchor="w", padx=24, pady=(0, 12))

    move_section = ttk.Frame(popup, style="Card.TFrame", padding=(24, 0, 24, 12))
    move_section.pack(side="top", fill="x")
    ttk.Label(
        move_section,
        text="Drag a student onto another group to move them there, or select a student and remove "
             "them back to Unassigned:",
        style="Muted.Card.TLabel", wraplength=760, justify="left",
    ).pack(anchor="w", pady=(0, 8))
    remove_button = ttk.Button(move_section, text="Remove from Group", style="Secondary.TButton")
    remove_button.pack(anchor="w")

    body = ttk.Frame(popup, style="Card.TFrame", padding=(24, 0, 24, 12))
    body.pack(side="top", fill="both", expand=True)

    columns = ("email",)
    tree_container, tree = scrollable_treeview(body, columns, height=16, show="tree headings")
    tree.heading("#0", text="Group / Student")
    tree.column("#0", width=260, anchor="w")
    tree.heading("email", text="Email")
    tree.column("email", width=220, anchor="w")
    tree.tag_configure("group_header", font=("Segoe UI", 10, "bold"), background=PALETTE["accent_soft"])
    tree_container.pack(fill="both", expand=True)

    node_to_group_id = {}  # tree node iid -> group_id (or None for the Unassigned bucket)

    def student_id_from_item(item):
        if not item or not item.startswith("s"):
            return None
        return int(item[1:])

    def refresh_roster():
        tree.delete(*tree.get_children())
        node_to_group_id.clear()

        groups = list_groups_by_assignment(assignment_id)
        membership = list_group_membership_for_assignment(course_id, assignment_id)

        by_group = {}
        unassigned = []
        for m in membership:
            if m["group_id"] is None:
                unassigned.append(m)
            else:
                by_group.setdefault(m["group_id"], []).append(m)

        for g in groups:
            node = f"g{g['group_id']}"
            node_to_group_id[node] = g["group_id"]
            tree.insert(
                "", "end", iid=node, text=f"{g['group_name']} ({g['member_count']})",
                open=True, tags=("group_header",),
            )
            for s in by_group.get(g["group_id"], []):
                tree.insert(node, "end", iid=f"s{s['user_id']}", text=s["name"], values=(s["email"],))

        # Unassigned always renders last, so newly-enrolled/unplaced students land in a final row.
        node_to_group_id[UNASSIGNED_NODE] = None
        tree.insert(
            "", "end", iid=UNASSIGNED_NODE, text=f"Unassigned ({len(unassigned)})",
            open=True, tags=("group_header",),
        )
        for s in unassigned:
            tree.insert(UNASSIGNED_NODE, "end", iid=f"s{s['user_id']}", text=s["name"], values=(s["email"],))

    # --- Actions ---
    def generate_click():
        try:
            size = int(size_var.get())
            if size < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid size", "Students per group must be a whole number of 1 or more.")
            return
        auto_distribute_groups(course_id, assignment_id, size)
        refresh_roster()
        if on_change:
            on_change()

    def selected_student():
        selection = tree.selection()
        if not selection:
            return None
        return student_id_from_item(selection[0])

    def remove_click():
        student_id = selected_student()
        if student_id is None:
            messagebox.showwarning("No student selected", "Select a student in the list first.")
            return
        set_student_group(assignment_id, student_id, None)
        refresh_roster()
        if on_change:
            on_change()

    generate_button.configure(command=generate_click)
    remove_button.configure(command=remove_click)

    # --- Drag and drop: grab a student row, drop it on another group's section.
    # Moving someone in only ever adds them there — it never removes anyone else,
    # so a group can end up bigger (or smaller) than the target size. ---
    drag_state = {"item": None}

    def on_press(event):
        item = tree.identify_row(event.y)
        drag_state["item"] = item if student_id_from_item(item) is not None else None

    def on_motion(event):
        if drag_state["item"]:
            tree.configure(cursor="hand2")

    def on_release(event):
        tree.configure(cursor="")
        dragged = drag_state["item"]
        drag_state["item"] = None
        if not dragged:
            return
        target_item = tree.identify_row(event.y)
        if not target_item:
            return
        target_node = target_item if tree.parent(target_item) == "" else tree.parent(target_item)
        if target_node == tree.parent(dragged):
            return
        student_id = student_id_from_item(dragged)
        set_student_group(assignment_id, student_id, node_to_group_id.get(target_node))
        refresh_roster()
        if on_change:
            on_change()

    tree.bind("<ButtonPress-1>", on_press)
    tree.bind("<B1-Motion>", on_motion)
    tree.bind("<ButtonRelease-1>", on_release)

    refresh_roster()

    popup.update_idletasks()
    x = app.winfo_rootx() + 50
    y = app.winfo_rooty() + 30
    popup.geometry(f"+{x}+{y}")
