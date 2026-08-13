PALETTE = {
    "bg": "#eef1f7",
    "card_bg": "#ffffff",
    "border": "#dde2ea",
    "text": "#1f2933",
    "text_muted": "#64748b",
    "accent": "#4f46e5",
    "accent_hover": "#4338ca",
    "accent_soft": "#eef0fd",
    "danger": "#dc2626",
}


def apply(root):
    """Configure every ttk style used across the app. Call once from the root window."""
    from tkinter import ttk

    p = PALETTE
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=p["bg"])

    style.configure(".", background=p["bg"], foreground=p["text"], font=("Segoe UI", 10))
    style.configure("TFrame", background=p["bg"])
    style.configure("Card.TFrame", background=p["card_bg"], relief="solid", borderwidth=1)
    style.configure("CardHeader.TFrame", background=p["card_bg"])

    style.configure("TLabel", background=p["bg"], foreground=p["text"])
    style.configure("Card.TLabel", background=p["card_bg"], foreground=p["text"])
    style.configure("Muted.TLabel", background=p["bg"], foreground=p["text_muted"], font=("Segoe UI", 9))
    style.configure("Muted.Card.TLabel", background=p["card_bg"], foreground=p["text_muted"], font=("Segoe UI", 9))

    style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"), foreground=p["text"], background=p["bg"])
    style.configure("Header.Card.TLabel", font=("Segoe UI", 20, "bold"), foreground=p["text"], background=p["card_bg"])
    style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=p["text"], background=p["bg"])
    style.configure("SubHeader.Card.TLabel", font=("Segoe UI", 12, "bold"), foreground=p["text"], background=p["card_bg"])

    style.configure(
        "Accent.TButton",
        font=("Segoe UI", 10, "bold"),
        foreground="white",
        background=p["accent"],
        borderwidth=0,
        padding=(16, 9),
    )
    style.map(
        "Accent.TButton",
        background=[("active", p["accent_hover"]), ("disabled", "#c7c8f0")],
    )

    style.configure(
        "Secondary.TButton",
        font=("Segoe UI", 10),
        foreground=p["text"],
        background=p["card_bg"],
        bordercolor=p["border"],
        borderwidth=1,
        padding=(14, 7),
    )
    style.map("Secondary.TButton", background=[("active", p["bg"])])

    style.configure("TEntry", fieldbackground="white", bordercolor=p["border"], lightcolor=p["border"], padding=7)
    style.map("TEntry", bordercolor=[("focus", p["accent"])])

    style.configure(
        "TCombobox",
        fieldbackground="white",
        background="white",
        bordercolor=p["border"],
        padding=6,
        arrowsize=14,
    )
    style.map("TCombobox", bordercolor=[("focus", p["accent"])])

    style.configure("TNotebook", background=p["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        padding=(18, 10),
        font=("Segoe UI", 10, "bold"),
        background=p["bg"],
        foreground=p["text_muted"],
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", p["card_bg"])],
        foreground=[("selected", p["accent"])],
    )

    style.configure(
        "Treeview",
        rowheight=28,
        background="white",
        fieldbackground="white",
        foreground=p["text"],
        borderwidth=0,
        font=("Segoe UI", 10),
    )
    style.configure(
        "Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        background=p["accent_soft"],
        foreground=p["text"],
        relief="flat",
        padding=8,
    )
    style.map("Treeview.Heading", background=[("active", p["accent_soft"])])
    style.map(
        "Treeview",
        background=[("selected", p["accent_soft"])],
        foreground=[("selected", p["text"])],
    )
