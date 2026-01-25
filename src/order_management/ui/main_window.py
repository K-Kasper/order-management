import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk

PRIMARY_BLUE = "#1F3A5F"
BG_MAIN = "#c0c0c0"


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._layout = {
            "body_padding": 6,
            "panel_padx": 6,
            "section_padx": 6,
            "section_pady": 4,
            "nav_button_width": 16,
            "entry_width": 24,
        }
        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkFixedFont",
            "TkMenuFont",
            "TkHeadingFont",
        ):
            tkfont.nametofont(name).configure(size=8)
        self.title("BP Order Management")
        self.minsize(960, 620)
        self.configure(bg=BG_MAIN)

        self._configure_style()
        self._load_assets()
        self.iconphoto(True, self._logo_image)

        self._build_menu()
        self._build_toolbar()
        self._build_main_content()
        self._build_statusbar()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Toolbar.TFrame", padding=(self._layout["panel_padx"], 4))
        style.configure("Header.TFrame", background=PRIMARY_BLUE)
        style.configure("Header.TLabel", background=PRIMARY_BLUE, foreground="#ffffff")
        style.configure(
            "Nav.TButton",
            width=self._layout["nav_button_width"],
            anchor="w",
            padding=(self._layout["panel_padx"], 2),
        )
        style.configure(
            "Nav.Selected.TButton",
            width=self._layout["nav_button_width"],
            anchor="w",
            padding=(self._layout["panel_padx"], 2),
        )
        style.map(
            "Nav.Selected.TButton",
            background=[("!disabled", "#e8e8e8")],
            relief=[("!disabled", "sunken")],
        )

    def _load_assets(self) -> None:
        assets_dir = Path(__file__).resolve().parents[1] / "assets"
        logo_path = assets_dir / "bp-logo.png"
        self._logo_image = tk.PhotoImage(file=str(logo_path))

    def _build_menu(self) -> None:
        menubar = tk.Menu(self, tearoff=False)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New Order", state="disabled")
        file_menu.add_command(label="Open...", state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Cut", state="disabled")
        edit_menu.add_command(label="Copy", state="disabled")
        edit_menu.add_command(label="Paste", state="disabled")

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Help Topics", state="disabled")
        help_menu.add_command(label="About", state="disabled")

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(fill="x")

        for label in ("New", "Save", "Print", "Search", "Export"):
            btn = ttk.Button(toolbar, text=label, state="disabled")
            btn.pack(side="left", padx=(0, 6))

        ttk.Separator(self, orient="horizontal").pack(fill="x")

    def _build_main_content(self) -> None:
        body = ttk.Frame(self, padding=self._layout["body_padding"])
        body.pack(fill="both", expand=True)

        nav_panel = ttk.Frame(body)
        nav_panel.pack(side="left", fill="y", padx=(0, self._layout["panel_padx"]))

        nav_frame = ttk.LabelFrame(
            nav_panel,
            text="Modules",
        )
        nav_frame.pack(fill="y", padx=4, pady=4)

        nav_body = ttk.Frame(
            nav_frame,
            padding=(
                self._layout["section_padx"],
                self._layout["section_pady"],
                self._layout["section_padx"],
                self._layout["section_padx"],
            ),
        )
        nav_body.pack(fill="y")

        for index, item in enumerate(
            [
                "Orders",
                "Customers",
                "Products",
                "Invoices",
                "Reports",
                "Settings",
            ]
        ):
            style = "Nav.Selected.TButton" if index == 0 else "Nav.TButton"
            btn = ttk.Button(nav_body, text=item, style=style, state="disabled")
            btn.pack(fill="x", pady=2)

        right_panel = ttk.Frame(body)
        right_panel.pack(side="left", fill="both", expand=True)

        header = ttk.Frame(right_panel, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, image=self._logo_image, style="Header.TLabel").pack(
            side="left", padx=(self._layout["panel_padx"], 4), pady=2
        )
        header_label = ttk.Label(
            header,
            text="Order Entry",
            style="Header.TLabel",
            anchor="w",
        )
        header_label.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=2)
        ttk.Label(
            header,
            text="Order: ORD-000142 • Open",
            style="Header.TLabel",
            anchor="e",
        ).pack(side="right", padx=self._layout["panel_padx"], pady=2)

        form = ttk.LabelFrame(
            right_panel,
            text="General",
        )
        form.pack(fill="x", pady=(self._layout["section_padx"], self._layout["section_pady"]))

        form_body = ttk.Frame(
            form,
            padding=(self._layout["section_padx"], self._layout["section_pady"]),
        )
        form_body.pack(fill="x")

        labels = [
            ("Order ID:", 0, 0),
            ("Customer:", 0, 2),
            ("Order Date:", 1, 0),
            ("Status:", 1, 2),
        ]
        for text, row, col in labels:
            label = ttk.Label(
                form_body,
                text=text,
                anchor="e",
                width=12,
            )
            label.grid(row=row, column=col, sticky="e", padx=3, pady=2)

        entries = []
        for row, col in [(0, 1), (0, 3), (1, 1), (1, 3)]:
            entry = ttk.Entry(form_body, width=self._layout["entry_width"])
            entry.grid(row=row, column=col, sticky="w", padx=3, pady=2)
            entries.append(entry)
        entries[0].insert(0, "ORD-000142")
        entries[1].insert(0, "Acme Industrial Supply")
        entries[2].insert(0, "01/25/2026")
        entries[3].insert(0, "Open")

        ttk.Separator(right_panel, orient="horizontal").pack(fill="x", pady=2)

        items = ttk.LabelFrame(
            right_panel,
            text="Line Items",
        )
        items.pack(fill="both", expand=True)

        items_body = ttk.Frame(
            items,
            padding=(self._layout["section_padx"], self._layout["section_pady"]),
        )
        items_body.pack(fill="both", expand=True)

        columns = ("SKU", "Description", "Qty", "Price", "Total")
        tree = ttk.Treeview(items_body, columns=columns, show="headings", height=10)
        for col in columns:
            tree.heading(col, text=col, anchor="w")
            tree.column(col, width=120, anchor="w")
        tree.column("Description", width=260)
        tree.column("Qty", width=60, anchor="e")
        tree.column("Price", width=80, anchor="e")
        tree.column("Total", width=90, anchor="e")

        for row in [
            ("A-103", "Thermal Printer Roll", "12", "3.50", "42.00"),
            ("B-220", "Label Stock 4x6", "4", "18.00", "72.00"),
            ("C-810", "Shipping Tape", "6", "2.75", "16.50"),
        ]:
            tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True)

        totals = ttk.Frame(right_panel)
        totals.pack(
            fill="x",
            padx=self._layout["section_padx"],
            pady=(self._layout["section_pady"], 0),
        )
        totals.columnconfigure(0, weight=1)

        for text, value, row in [
            ("Subtotal", "130.50", 0),
            ("Tax", "10.44", 1),
            ("Total", "140.94", 2),
        ]:
            ttk.Label(totals, text=text + ":").grid(
                row=row, column=1, sticky="e", padx=(0, 6), pady=2
            )
            ttk.Label(totals, text=value, width=10, anchor="e").grid(
                row=row, column=2, sticky="e", pady=2
            )

    def _build_statusbar(self) -> None:
        status = ttk.Frame(
            self,
            relief="sunken",
            padding=(self._layout["panel_padx"], 2),
        )
        status.pack(fill="x", side="bottom")

        left = ttk.Label(status, text="Ready", anchor="w")
        left.pack(side="left", fill="x", expand=True)

        right = ttk.Label(status, text="User: Kasper | Branch: HQ", anchor="e")
        right.pack(side="right")
