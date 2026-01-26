import shutil
import os
import subprocess
import sys
from shutil import which
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from order_management.data.db import APP_DIR
from order_management.services.customer_service import CustomerService
from order_management.services.order_service import (
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    OrderFilters,
    OrderService,
)
from order_management.services.seed_service import SeedService
from tkcalendar import DateEntry

PRIMARY_BLUE = "#1F3A5F"
BG_MAIN = "#c0c0c0"
DATE_DISPLAY = "%d/%m/%Y"
DATE_STORAGE = "%Y-%m-%d"


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._layout = {
            "body_padding": 6,
            "panel_padx": 6,
            "section_padx": 6,
            "section_pady": 4,
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
        self.minsize(1120, 720)
        self.configure(bg=BG_MAIN)

        self._order_service = OrderService()
        self._customer_service = CustomerService()
        self._seed_service = SeedService()
        self._current_order_id: int | None = None
        self._current_customer_id: int | None = None
        self._orders_cache: list[dict[str, object]] = []
        self._images_cache: list[dict[str, object]] = []
        self._customers_cache: list[dict[str, object]] = []
        self._status_summary_cache: list[dict[str, object]] = []
        self._overdue_cache: list[dict[str, object]] = []
        self._due_soon_cache: list[dict[str, object]] = []
        self._customers_by_name: dict[str, int] = {}
        self._customers_by_id: dict[int, dict[str, object]] = {}
        self._sort_column = "deadline"
        self._sort_desc = False

        self._configure_style()
        self._load_assets()
        self.iconphoto(True, self._logo_image)

        self._build_menu()
        self._build_main_content()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._load_customers()
        self._load_orders()
        self._load_reports()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Toolbar.TFrame", padding=(self._layout["panel_padx"], 4))
        style.configure("Header.TFrame", background=PRIMARY_BLUE)
        style.configure("Header.TLabel", background=PRIMARY_BLUE, foreground="#ffffff")
        style.configure("Filter.TLabel", padding=(0, 0, 6, 0))
        style.configure("Action.TButton", padding=(8, 2))

    def _load_assets(self) -> None:
        assets_dir = Path(__file__).resolve().parents[1] / "assets"
        logo_path = assets_dir / "bp-logo.png"
        self._logo_image = tk.PhotoImage(file=str(logo_path))

    def _build_menu(self) -> None:
        menubar = tk.Menu(self, tearoff=False)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New Order", command=self._new_order)
        file_menu.add_command(label="Save Order", command=self._save_order)
        file_menu.add_command(label="Delete Order", command=self._delete_order)
        file_menu.add_separator()
        file_menu.add_command(label="Export Form", command=self._export_form)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)

        customer_menu = tk.Menu(menubar, tearoff=False)
        customer_menu.add_command(label="New Customer", command=self._new_customer)
        customer_menu.add_command(label="Save Customer", command=self._save_customer)
        customer_menu.add_command(
            label="Delete Customer", command=self._delete_customer
        )

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label="Seed Demo Data", command=self._seed_demo_data)
        tools_menu.add_command(label="Refresh Reports", command=self._load_reports)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Help Topics", state="disabled")
        help_menu.add_command(label="About", state="disabled")

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Customers", menu=customer_menu)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _build_main_content(self) -> None:
        body = ttk.Frame(self, padding=self._layout["body_padding"])
        body.pack(fill="both", expand=True)

        header = ttk.Frame(body, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, image=self._logo_image, style="Header.TLabel").pack(
            side="left", padx=(self._layout["panel_padx"], 4), pady=2
        )
        header_label = ttk.Label(
            header,
            text="Order Management",
            style="Header.TLabel",
            anchor="w",
        )
        header_label.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=2)
        ttk.Label(
            header,
            text="SQLite Local Storage",
            style="Header.TLabel",
            anchor="e",
        ).pack(side="right", padx=self._layout["panel_padx"], pady=2)

        self._notebook = ttk.Notebook(body)
        self._notebook.pack(fill="both", expand=True, pady=(6, 0))

        orders_tab = ttk.Frame(self._notebook)
        customers_tab = ttk.Frame(self._notebook)
        reports_tab = ttk.Frame(self._notebook)
        self._notebook.add(orders_tab, text="Orders")
        self._notebook.add(customers_tab, text="Customers")
        self._notebook.add(reports_tab, text="Reports")

        self._build_orders_tab(orders_tab)
        self._build_customers_tab(customers_tab)
        self._build_reports_tab(reports_tab)

    def _build_orders_tab(self, parent: ttk.Frame) -> None:
        filters = ttk.LabelFrame(parent, text="Order Filters")
        filters.pack(fill="x", pady=(self._layout["section_padx"], 4))

        self._filter_status = tk.StringVar()
        self._filter_customer = tk.StringVar()
        self._filter_search = tk.StringVar()
        self._filter_deadline_from = tk.StringVar()
        self._filter_deadline_to = tk.StringVar()
        self._filter_show_closed = tk.BooleanVar(value=False)

        filter_body = ttk.Frame(filters, padding=(self._layout["section_padx"], 4))
        filter_body.pack(fill="x")

        ttk.Label(filter_body, text="Status", style="Filter.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        status_combo = ttk.Combobox(
            filter_body,
            textvariable=self._filter_status,
            values=("",) + STATUS_OPTIONS,
            width=12,
            state="readonly",
        )
        status_combo.grid(row=1, column=0, sticky="w", padx=(0, 10))

        ttk.Label(filter_body, text="Customer", style="Filter.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        self._filter_customer_combo = ttk.Combobox(
            filter_body,
            textvariable=self._filter_customer,
            values=(),
            width=20,
            state="readonly",
        )
        self._filter_customer_combo.grid(row=1, column=1, sticky="w", padx=(0, 10))

        ttk.Label(filter_body, text="Search", style="Filter.TLabel").grid(
            row=0, column=2, sticky="w"
        )
        ttk.Entry(filter_body, textvariable=self._filter_search, width=22).grid(
            row=1, column=2, sticky="w", padx=(0, 10)
        )

        ttk.Label(
            filter_body, text="Deadline From (DD/MM/YYYY)", style="Filter.TLabel"
        ).grid(row=0, column=3, sticky="w")
        ttk.Entry(filter_body, textvariable=self._filter_deadline_from, width=16).grid(
            row=1, column=3, sticky="w", padx=(0, 10)
        )

        ttk.Label(
            filter_body, text="Deadline To (DD/MM/YYYY)", style="Filter.TLabel"
        ).grid(row=0, column=4, sticky="w")
        ttk.Entry(filter_body, textvariable=self._filter_deadline_to, width=16).grid(
            row=1, column=4, sticky="w", padx=(0, 10)
        )

        ttk.Checkbutton(
            filter_body,
            text="Show Closed",
            variable=self._filter_show_closed,
            command=self._load_orders,
        ).grid(row=1, column=5, sticky="w", padx=(0, 10))

        ttk.Button(
            filter_body, text="Apply", style="Action.TButton", command=self._load_orders
        ).grid(row=1, column=6, padx=(6, 4))
        ttk.Button(
            filter_body,
            text="Clear",
            style="Action.TButton",
            command=self._clear_filters,
        ).grid(row=1, column=7, padx=(0, 6))

        list_frame = ttk.LabelFrame(parent, text="Orders")
        list_frame.pack(fill="both", expand=True)

        columns = (
            "order_no",
            "title",
            "customer_display",
            "status",
            "deadline",
            "value",
            "priority",
            "updated_at",
        )
        self._orders_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=10
        )
        headings = {
            "order_no": "Order",
            "title": "Title",
            "customer_display": "Customer",
            "status": "Status",
            "deadline": "Deadline",
            "value": "Value",
            "priority": "Priority",
            "updated_at": "Updated",
        }
        for col in columns:
            self._orders_tree.heading(
                col, text=headings[col], command=lambda c=col: self._sort_orders(c)
            )
            anchor = "e" if col in {"value"} else "w"
            width = 130 if col in {"title", "customer_display"} else 90
            if col == "updated_at":
                width = 140
            self._orders_tree.column(col, width=width, anchor=anchor)
        self._orders_tree.column("title", width=200)
        self._orders_tree.column("customer_display", width=180)
        self._orders_tree.tag_configure("overdue", background="#ffe6e6")
        self._orders_tree.tag_configure("due_today", background="#fff4cc")
        self._orders_tree.tag_configure("due_soon", background="#fff8de")
        self._orders_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self._orders_tree.bind("<<TreeviewSelect>>", self._on_select_order)

        detail_frame = ttk.LabelFrame(parent, text="Order Detail")
        detail_frame.pack(fill="x", pady=(4, 4))

        form = ttk.Frame(detail_frame, padding=(self._layout["section_padx"], 4))
        form.pack(fill="x")

        self._order_no = tk.StringVar()
        self._title = tk.StringVar()
        self._customer = tk.StringVar()
        self._status = tk.StringVar(value=STATUS_OPTIONS[0])
        self._deadline = tk.StringVar()
        self._value = tk.StringVar(value="0.00")
        self._priority = tk.StringVar(value=PRIORITY_OPTIONS[1])

        labels = [
            ("Order No", 0, 0),
            ("Title", 0, 2),
            ("Customer", 1, 0),
            ("Status", 1, 2),
            ("Deadline (DD/MM/YYYY)", 2, 0),
            ("Value", 2, 2),
            ("Priority", 3, 0),
        ]
        for text, row, col in labels:
            ttk.Label(form, text=text + ":", width=18, anchor="e").grid(
                row=row, column=col, sticky="e", padx=3, pady=2
            )

        ttk.Entry(form, textvariable=self._order_no, width=18, state="readonly").grid(
            row=0, column=1, sticky="w", padx=3, pady=2
        )
        ttk.Entry(form, textvariable=self._title, width=32).grid(
            row=0, column=3, sticky="w", padx=3, pady=2
        )
        self._customer_combo = ttk.Combobox(
            form, textvariable=self._customer, values=(), width=30, state="readonly"
        )
        self._customer_combo.grid(row=1, column=1, sticky="w", padx=3, pady=2)
        ttk.Combobox(
            form,
            textvariable=self._status,
            values=STATUS_OPTIONS,
            width=18,
            state="readonly",
        ).grid(row=1, column=3, sticky="w", padx=3, pady=2)
        self._deadline_entry = DateEntry(
            form,
            textvariable=self._deadline,
            width=18,
            date_pattern="dd/mm/yyyy",
        )
        self._deadline_entry.grid(row=2, column=1, sticky="w", padx=3, pady=2)
        ttk.Entry(form, textvariable=self._value, width=18).grid(
            row=2, column=3, sticky="w", padx=3, pady=2
        )
        ttk.Combobox(
            form,
            textvariable=self._priority,
            values=PRIORITY_OPTIONS,
            width=18,
            state="readonly",
        ).grid(row=3, column=1, sticky="w", padx=3, pady=2)

        desc_frame = ttk.LabelFrame(detail_frame, text="Description / Brief")
        desc_frame.pack(fill="both", padx=6, pady=(0, 6))
        self._description = tk.Text(desc_frame, height=5, wrap="word")
        self._description.pack(fill="both", expand=True, padx=6, pady=4)

        images_frame = ttk.LabelFrame(detail_frame, text="Reference Images")
        images_frame.pack(fill="both", padx=6, pady=(0, 6))
        images_body = ttk.Frame(images_frame, padding=4)
        images_body.pack(fill="x")
        self._images_list = tk.Listbox(images_body, height=4)
        self._images_list.pack(side="left", fill="x", expand=True)
        self._images_list.bind("<Double-Button-1>", self._view_image_event)

        actions = ttk.Frame(detail_frame, padding=(self._layout["section_padx"], 0))
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="New Order", command=self._new_order).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Save Order", command=self._save_order).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Delete Order", command=self._delete_order).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Export Form", command=self._export_form).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Add Image", command=self._add_images).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Remove Image", command=self._remove_image).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="View Image", command=self._view_image).pack(
            side="left", padx=(0, 6)
        )

    def _build_customers_tab(self, parent: ttk.Frame) -> None:
        list_frame = ttk.LabelFrame(parent, text="Customers")
        list_frame.pack(
            fill="both", expand=True, pady=(self._layout["section_padx"], 4)
        )

        columns = ("name", "contact_name", "email", "phone", "updated_at")
        self._customers_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=10
        )
        headings = {
            "name": "Name",
            "contact_name": "Contact",
            "email": "Email",
            "phone": "Phone",
            "updated_at": "Updated",
        }
        for col in columns:
            self._customers_tree.heading(col, text=headings[col])
            width = 160 if col in {"name", "contact_name"} else 140
            if col == "email":
                width = 200
            if col == "updated_at":
                width = 140
            self._customers_tree.column(col, width=width, anchor="w")
        self._customers_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self._customers_tree.bind("<<TreeviewSelect>>", self._on_select_customer)

        detail_frame = ttk.LabelFrame(parent, text="Customer Detail")
        detail_frame.pack(fill="x", pady=(4, 4))

        form = ttk.Frame(detail_frame, padding=(self._layout["section_padx"], 4))
        form.pack(fill="x")

        self._cust_name = tk.StringVar()
        self._cust_contact = tk.StringVar()
        self._cust_email = tk.StringVar()
        self._cust_phone = tk.StringVar()

        labels = [
            ("Name", 0, 0),
            ("Contact", 0, 2),
            ("Email", 1, 0),
            ("Phone", 1, 2),
        ]
        for text, row, col in labels:
            ttk.Label(form, text=text + ":", width=10, anchor="e").grid(
                row=row, column=col, sticky="e", padx=3, pady=2
            )

        ttk.Entry(form, textvariable=self._cust_name, width=32).grid(
            row=0, column=1, sticky="w", padx=3, pady=2
        )
        ttk.Entry(form, textvariable=self._cust_contact, width=32).grid(
            row=0, column=3, sticky="w", padx=3, pady=2
        )
        ttk.Entry(form, textvariable=self._cust_email, width=32).grid(
            row=1, column=1, sticky="w", padx=3, pady=2
        )
        ttk.Entry(form, textvariable=self._cust_phone, width=32).grid(
            row=1, column=3, sticky="w", padx=3, pady=2
        )

        notes_frame = ttk.LabelFrame(detail_frame, text="Notes")
        notes_frame.pack(fill="both", padx=6, pady=(0, 6))
        self._cust_notes = tk.Text(notes_frame, height=4, wrap="word")
        self._cust_notes.pack(fill="both", expand=True, padx=6, pady=4)

        actions = ttk.Frame(detail_frame, padding=(self._layout["section_padx"], 0))
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="New Customer", command=self._new_customer).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Save Customer", command=self._save_customer).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Delete Customer", command=self._delete_customer).pack(
            side="left", padx=(0, 6)
        )

    def _build_reports_tab(self, parent: ttk.Frame) -> None:
        status_frame = ttk.LabelFrame(parent, text="Status Summary")
        status_frame.pack(fill="x", padx=4, pady=4)
        self._status_tree = ttk.Treeview(
            status_frame,
            columns=("status", "order_count", "total_value"),
            show="headings",
        )
        self._status_tree.heading("status", text="Status")
        self._status_tree.heading("order_count", text="Orders")
        self._status_tree.heading("total_value", text="Total Value")
        self._status_tree.column("status", width=120, anchor="w")
        self._status_tree.column("order_count", width=120, anchor="e")
        self._status_tree.column("total_value", width=140, anchor="e")
        self._status_tree.pack(fill="x", padx=4, pady=4)

        overdue_frame = ttk.LabelFrame(parent, text="Overdue (Open/Feedback)")
        overdue_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self._overdue_tree = ttk.Treeview(
            overdue_frame,
            columns=("order_no", "title", "customer", "deadline", "value", "status"),
            show="headings",
            height=6,
        )
        for col, text, width in (
            ("order_no", "Order", 100),
            ("title", "Title", 200),
            ("customer", "Customer", 180),
            ("deadline", "Deadline", 120),
            ("value", "Value", 100),
            ("status", "Status", 100),
        ):
            self._overdue_tree.heading(col, text=text)
            self._overdue_tree.column(col, width=width, anchor="w")
        self._overdue_tree.column("value", anchor="e")
        self._overdue_tree.tag_configure("overdue", background="#ffe6e6")
        self._overdue_tree.pack(fill="both", expand=True, padx=4, pady=4)

        due_soon_frame = ttk.LabelFrame(parent, text="Due Soon (Next 7 Days)")
        due_soon_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self._due_soon_tree = ttk.Treeview(
            due_soon_frame,
            columns=("order_no", "title", "customer", "deadline", "value", "status"),
            show="headings",
            height=6,
        )
        for col, text, width in (
            ("order_no", "Order", 100),
            ("title", "Title", 200),
            ("customer", "Customer", 180),
            ("deadline", "Deadline", 120),
            ("value", "Value", 100),
            ("status", "Status", 100),
        ):
            self._due_soon_tree.heading(col, text=text)
            self._due_soon_tree.column(col, width=width, anchor="w")
        self._due_soon_tree.column("value", anchor="e")
        self._due_soon_tree.tag_configure("due_soon", background="#fff4cc")
        self._due_soon_tree.pack(fill="both", expand=True, padx=4, pady=4)

        actions = ttk.Frame(parent, padding=(self._layout["section_padx"], 0))
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="Refresh Reports", command=self._load_reports).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Export Reports", command=self._export_reports).pack(
            side="left", padx=(0, 6)
        )

    def _build_statusbar(self) -> None:
        status = ttk.Frame(
            self,
            relief="sunken",
            padding=(self._layout["panel_padx"], 2),
        )
        status.pack(fill="x", side="bottom")

        self._status_left = ttk.Label(status, text="Ready", anchor="w")
        self._status_left.pack(side="left", fill="x", expand=True)

    def _set_status(self, message: str) -> None:
        self._status_left.configure(text=message)

    def _clear_filters(self) -> None:
        self._filter_status.set("")
        self._filter_customer.set("")
        self._filter_search.set("")
        self._filter_deadline_from.set("")
        self._filter_deadline_to.set("")
        self._filter_show_closed.set(False)
        self._load_orders()

    def _load_customers(self) -> None:
        self._customers_cache = self._customer_service.list_customers()
        self._customers_by_name = {
            customer.get("name", ""): int(customer["id"])
            for customer in self._customers_cache
            if customer.get("name")
        }
        self._customers_by_id = {
            int(customer["id"]): customer for customer in self._customers_cache
        }
        names = [customer.get("name", "") for customer in self._customers_cache]
        self._customer_combo.configure(values=names)
        self._filter_customer_combo.configure(values=("",) + tuple(names))
        self._refresh_customers_tree()

    def _refresh_customers_tree(self) -> None:
        for item in self._customers_tree.get_children():
            self._customers_tree.delete(item)
        for row in self._customers_cache:
            updated = self._format_datetime(row.get("updated_at"))
            self._customers_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("name"),
                    row.get("contact_name"),
                    row.get("email"),
                    row.get("phone"),
                    updated,
                ),
            )

    def _load_orders(self) -> None:
        deadline_from_raw = self._filter_deadline_from.get().strip()
        deadline_to_raw = self._filter_deadline_to.get().strip()
        deadline_from = (
            self._parse_deadline(deadline_from_raw) if deadline_from_raw else None
        )
        deadline_to = self._parse_deadline(deadline_to_raw) if deadline_to_raw else None
        if deadline_from_raw and not deadline_from:
            messagebox.showwarning(
                "Invalid Filter",
                "Deadline From must be DD/MM/YYYY or YYYY-MM-DD.",
            )
            return
        if deadline_to_raw and not deadline_to:
            messagebox.showwarning(
                "Invalid Filter",
                "Deadline To must be DD/MM/YYYY or YYYY-MM-DD.",
            )
            return

        customer_id = None
        customer_name = self._filter_customer.get().strip()
        if customer_name:
            customer_id = self._customers_by_name.get(customer_name)

        status_filter = self._filter_status.get().strip() or None
        exclude_closed = not self._filter_show_closed.get()
        filters = OrderFilters(
            status=status_filter,
            exclude_status=None if status_filter or not exclude_closed else "Closed",
            customer_id=customer_id,
            customer=None,
            search=self._filter_search.get().strip() or None,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
        )
        self._orders_cache = self._order_service.list_orders(filters)
        self._apply_sort()
        self._refresh_orders_tree()
        self._set_status(f"Loaded {len(self._orders_cache)} orders")

    def _refresh_orders_tree(self) -> None:
        for item in self._orders_tree.get_children():
            self._orders_tree.delete(item)
        for row in self._orders_cache:
            value = float(row.get("value") or 0.0)
            deadline = self._format_date(row.get("deadline"))
            updated = self._format_datetime(row.get("updated_at"))
            item_id = self._orders_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("order_no"),
                    row.get("title"),
                    row.get("customer_display") or row.get("customer_name"),
                    row.get("status"),
                    deadline,
                    f"${value:,.2f}",
                    row.get("priority"),
                    updated,
                ),
            )
            status = self._date_status(row.get("deadline"))
            if status == "overdue":
                self._orders_tree.item(item_id, tags=("overdue",))
            elif status == "due_today":
                self._orders_tree.item(item_id, tags=("due_today",))
            elif status == "due_soon":
                self._orders_tree.item(item_id, tags=("due_soon",))

    def _load_reports(self) -> None:
        self._status_summary_cache = self._order_service.status_summary()
        self._overdue_cache = self._order_service.overdue_orders()
        self._due_soon_cache = self._order_service.due_soon_orders()
        self._refresh_status_tree()
        self._refresh_overdue_tree()
        self._refresh_due_soon_tree()
        self._set_status("Reports refreshed")

    def _refresh_status_tree(self) -> None:
        for item in self._status_tree.get_children():
            self._status_tree.delete(item)
        for row in self._status_summary_cache:
            total_value = float(row.get("total_value") or 0.0)
            self._status_tree.insert(
                "",
                "end",
                values=(
                    row.get("status"),
                    row.get("order_count"),
                    f"${total_value:,.2f}",
                ),
            )

    def _refresh_overdue_tree(self) -> None:
        for item in self._overdue_tree.get_children():
            self._overdue_tree.delete(item)
        for row in self._overdue_cache:
            value = float(row.get("value") or 0.0)
            item_id = self._overdue_tree.insert(
                "",
                "end",
                values=(
                    row.get("order_no"),
                    row.get("title"),
                    row.get("customer_display") or row.get("customer_name"),
                    self._format_date(row.get("deadline")),
                    f"${value:,.2f}",
                    row.get("status"),
                ),
            )
            self._overdue_tree.item(item_id, tags=("overdue",))

    def _refresh_due_soon_tree(self) -> None:
        for item in self._due_soon_tree.get_children():
            self._due_soon_tree.delete(item)
        for row in self._due_soon_cache:
            value = float(row.get("value") or 0.0)
            item_id = self._due_soon_tree.insert(
                "",
                "end",
                values=(
                    row.get("order_no"),
                    row.get("title"),
                    row.get("customer_display") or row.get("customer_name"),
                    self._format_date(row.get("deadline")),
                    f"${value:,.2f}",
                    row.get("status"),
                ),
            )
            self._due_soon_tree.item(item_id, tags=("due_soon",))

    def _apply_sort(self) -> None:
        key = self._sort_column

        def sort_key(row: dict[str, object]) -> object:
            value = row.get(key)
            if key == "value":
                try:
                    return float(value or 0.0)
                except (TypeError, ValueError):
                    return 0.0
            return value or ""

        self._orders_cache.sort(key=sort_key, reverse=self._sort_desc)

    def _sort_orders(self, column: str) -> None:
        if self._sort_column == column:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_column = column
            self._sort_desc = False
        self._apply_sort()
        self._refresh_orders_tree()

    def _date_status(self, value: object) -> str:
        if not value:
            return "none"
        try:
            parsed = datetime.strptime(str(value), DATE_STORAGE).date()
        except ValueError:
            return "none"
        today = datetime.today().date()
        if parsed < today:
            return "overdue"
        if parsed == today:
            return "due_today"
        if parsed <= today + timedelta(days=7):
            return "due_soon"
        return "ok"

    def _on_select_order(self, _event: tk.Event) -> None:
        selection = self._orders_tree.selection()
        if not selection:
            return
        order_id = int(selection[0])
        order = self._order_service.get_order(order_id)
        if not order:
            return
        self._current_order_id = order_id
        self._order_no.set(order.get("order_no", ""))
        self._title.set(order.get("title", ""))
        customer_display = (
            order.get("customer_display") or order.get("customer_name") or ""
        )
        self._customer.set(customer_display)
        self._status.set(order.get("status", STATUS_OPTIONS[0]))
        self._set_deadline_display(self._format_date(order.get("deadline")))
        self._value.set(f"{float(order.get('value') or 0.0):.2f}")
        self._priority.set(order.get("priority", PRIORITY_OPTIONS[1]))
        self._description.delete("1.0", "end")
        self._description.insert("1.0", order.get("description", ""))
        self._load_images(order_id)
        self._set_status(f"Loaded {order.get('order_no')}")

    def _load_images(self, order_id: int) -> None:
        self._images_cache = self._order_service.list_images(order_id)
        self._images_list.delete(0, "end")
        for image in self._images_cache:
            self._images_list.insert("end", image.get("file_name"))

    def _new_order(self) -> None:
        self._current_order_id = None
        self._order_no.set("(new)")
        self._title.set("")
        self._customer.set("")
        self._status.set(STATUS_OPTIONS[0])
        self._set_deadline_display("")
        self._value.set("0.00")
        self._priority.set(PRIORITY_OPTIONS[1])
        self._description.delete("1.0", "end")
        self._images_cache = []
        self._images_list.delete(0, "end")
        self._notebook.select(0)
        self._set_status("Creating new order")

    def _save_order(self) -> None:
        payload = self._collect_form_payload()
        if not payload:
            return
        if self._current_order_id is None:
            order_id = self._order_service.create_order(payload)
            self._current_order_id = order_id
            order = self._order_service.get_order(order_id)
            if order:
                self._order_no.set(order.get("order_no", ""))
            self._set_status("Order created")
        else:
            self._order_service.update_order(self._current_order_id, payload)
            self._set_status("Order updated")
        self._load_orders()
        if self._current_order_id is not None:
            item_id = str(self._current_order_id)
            if self._orders_tree.exists(item_id):
                self._orders_tree.selection_set(item_id)
                self._orders_tree.see(item_id)

    def _delete_order(self) -> None:
        selection = self._orders_tree.selection()
        if not selection:
            messagebox.showinfo("Delete Order", "Select an order to delete.")
            return
        order_id = int(selection[0])
        order = self._order_service.get_order(order_id)
        if not order:
            return
        proceed = messagebox.askyesno(
            "Delete Order",
            f"Delete order {order.get('order_no')}? This cannot be undone.",
        )
        if not proceed:
            return
        self._order_service.delete_order(order_id)
        self._current_order_id = None
        self._new_order()
        self._load_orders()
        self._load_reports()
        self._set_status("Order deleted")

    def _collect_form_payload(self) -> dict[str, object] | None:
        title = self._title.get().strip()
        customer_name = self._customer.get().strip()
        description = self._description.get("1.0", "end").strip()
        deadline_raw = self._deadline.get().strip()

        if not title:
            messagebox.showwarning("Missing Title", "Title is required.")
            return None
        if not customer_name:
            messagebox.showwarning("Missing Customer", "Customer is required.")
            return None
        if customer_name not in self._customers_by_name:
            messagebox.showwarning(
                "Unknown Customer",
                "Select a customer from the list or create a new customer first.",
            )
            return None
        if not description:
            messagebox.showwarning(
                "Missing Description", "Description/brief is required."
            )
            return None
        deadline = self._parse_deadline(deadline_raw)
        if not deadline:
            messagebox.showwarning(
                "Invalid Deadline",
                "Deadline is required. Use DD/MM/YYYY or YYYY-MM-DD.",
            )
            return None

        value_raw = self._value.get().strip() or "0"
        try:
            value = float(value_raw)
        except ValueError:
            messagebox.showwarning("Invalid Value", "Value must be a number.")
            return None

        customer_id = self._customers_by_name.get(customer_name)

        return {
            "title": title,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "status": self._status.get().strip() or STATUS_OPTIONS[0],
            "deadline": deadline,
            "value": value,
            "priority": self._priority.get().strip() or PRIORITY_OPTIONS[1],
            "description": description,
        }

    def _parse_deadline(self, value: str) -> str | None:
        if not value:
            return None
        for fmt in (DATE_DISPLAY, DATE_STORAGE):
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.strftime(DATE_STORAGE)
            except ValueError:
                continue
        return None

    def _set_deadline_display(self, value: str) -> None:
        if not value:
            self._deadline.set("")
            self._deadline_entry.delete(0, "end")
            return
        for fmt in (DATE_DISPLAY, DATE_STORAGE):
            try:
                parsed = datetime.strptime(value, fmt)
                self._deadline_entry.set_date(parsed)
                return
            except ValueError:
                continue
        self._deadline.set(value)

    def _format_date(self, value: object) -> str:
        if not value:
            return ""
        try:
            parsed = datetime.strptime(str(value), DATE_STORAGE)
            return parsed.strftime(DATE_DISPLAY)
        except ValueError:
            return str(value)

    def _format_datetime(self, value: object) -> str:
        if not value:
            return ""
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(str(value), fmt)
                return parsed.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                continue
        return str(value)

    def _add_images(self) -> None:
        if self._current_order_id is None:
            messagebox.showinfo("Save First", "Save the order before adding images.")
            return
        paths = filedialog.askopenfilenames(
            title="Add Reference Images",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All Files", "*.*"),
            ],
        )
        if not paths:
            return
        source_paths = [Path(path) for path in paths]
        self._order_service.add_images(self._current_order_id, source_paths)
        self._load_images(self._current_order_id)
        self._set_status(f"Added {len(paths)} image(s)")

    def _remove_image(self) -> None:
        selection = self._images_list.curselection()
        if not selection:
            messagebox.showinfo("Remove Image", "Select an image to remove.")
            return
        index = selection[0]
        image = self._images_cache[index]
        image_id = image.get("id")
        if image_id is None:
            return
        self._order_service.delete_image(int(image_id))
        if self._current_order_id is not None:
            self._load_images(self._current_order_id)
        self._set_status("Image removed")

    def _view_image_event(self, _event: tk.Event) -> None:
        self._view_image()

    def _view_image(self) -> None:
        selection = self._images_list.curselection()
        if not selection:
            messagebox.showinfo("View Image", "Select an image to view.")
            return
        index = selection[0]
        image = self._images_cache[index]
        file_path = Path(str(image.get("file_path", "")))
        if not file_path.exists():
            messagebox.showerror("View Image", "Image file not found on disk.")
            return
        try:
            webbrowser.open(file_path.resolve().as_uri())
        except OSError:
            messagebox.showerror("View Image", "Unable to open the image file.")

    def _export_form(self) -> None:
        if self._current_order_id is None:
            messagebox.showinfo("Export", "Select an order to export.")
            return
        try:
            output_path = self._order_service.export_order_form(self._current_order_id)
        except ValueError as exc:
            messagebox.showerror("Export Failed", str(exc))
            return
        self._open_export(output_path)
        if messagebox.askyesno(
            "Export Complete",
            f"Service order form saved to:\n{output_path}\n\nOpen the exports folder?",
        ):
            self._open_exports_folder()
        self._set_status("Exported service order form")

    def _export_reports(self) -> None:
        output_path = self._order_service.export_reports()
        self._open_export(output_path)
        if messagebox.askyesno(
            "Export Complete",
            f"Reports saved to:\n{output_path}\n\nOpen the exports folder?",
        ):
            self._open_exports_folder()
        self._set_status("Exported reports")

    def _open_export(self, output_path: Path) -> None:
        self._open_path(output_path)

    def _open_exports_folder(self) -> None:
        exports_dir = Path.home() / "Downloads" / "bp-order-management"
        if not exports_dir.exists():
            return
        self._open_path(exports_dir)

    def _open_path(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))
                return
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(path)], start_new_session=True)
                return
            opener = which("xdg-open")
            if opener:
                clean_env = os.environ.copy()
                # Avoid PyInstaller's bundled libs breaking system apps.
                clean_env.pop("LD_LIBRARY_PATH", None)
                clean_env.pop("LD_PRELOAD", None)
                subprocess.Popen(
                    [opener, str(path)],
                    start_new_session=True,
                    env=clean_env,
                )
                return
        except OSError:
            pass

    def _on_close(self) -> None:
        self.destroy()

    def _on_select_customer(self, _event: tk.Event) -> None:
        selection = self._customers_tree.selection()
        if not selection:
            return
        customer_id = int(selection[0])
        customer = self._customer_service.get_customer(customer_id)
        if not customer:
            return
        self._current_customer_id = customer_id
        self._cust_name.set(customer.get("name", ""))
        self._cust_contact.set(customer.get("contact_name", ""))
        self._cust_email.set(customer.get("email", ""))
        self._cust_phone.set(customer.get("phone", ""))
        self._cust_notes.delete("1.0", "end")
        self._cust_notes.insert("1.0", customer.get("notes", ""))
        self._notebook.select(1)
        self._set_status(f"Loaded customer {customer.get('name')}")

    def _new_customer(self) -> None:
        self._current_customer_id = None
        self._cust_name.set("")
        self._cust_contact.set("")
        self._cust_email.set("")
        self._cust_phone.set("")
        self._cust_notes.delete("1.0", "end")
        self._notebook.select(1)
        self._set_status("Creating new customer")

    def _save_customer(self) -> None:
        payload = self._collect_customer_payload()
        if not payload:
            return
        if self._current_customer_id is None:
            customer_id = self._customer_service.create_customer(payload)
            self._current_customer_id = customer_id
            self._set_status("Customer created")
        else:
            self._customer_service.update_customer(self._current_customer_id, payload)
            self._set_status("Customer updated")
        self._load_customers()
        if self._current_customer_id is not None:
            item_id = str(self._current_customer_id)
            if self._customers_tree.exists(item_id):
                self._customers_tree.selection_set(item_id)
                self._customers_tree.see(item_id)
        self._load_orders()

    def _delete_customer(self) -> None:
        selection = self._customers_tree.selection()
        if not selection:
            messagebox.showinfo("Delete Customer", "Select a customer to delete.")
            return
        customer_id = int(selection[0])
        customer = self._customer_service.get_customer(customer_id)
        if not customer:
            return
        linked = self._customer_service.count_linked_orders(customer_id)
        if linked > 0:
            proceed = messagebox.askyesno(
                "Delete Customer",
                f"{linked} order(s) are linked to this customer. Deleting will keep\n"
                "the order history but remove the customer from the list.\n\n"
                "Continue?",
            )
            if not proceed:
                return
        self._customer_service.delete_customer(customer_id)
        self._current_customer_id = None
        self._new_customer()
        self._load_customers()
        self._load_orders()
        self._set_status("Customer deleted")

    def _collect_customer_payload(self) -> dict[str, object] | None:
        name = self._cust_name.get().strip()
        contact = self._cust_contact.get().strip()
        email = self._cust_email.get().strip()
        phone = self._cust_phone.get().strip()
        notes = self._cust_notes.get("1.0", "end").strip()

        if not name:
            messagebox.showwarning("Missing Name", "Customer name is required.")
            return None

        return {
            "name": name,
            "contact_name": contact,
            "email": email,
            "phone": phone,
            "notes": notes,
        }

    def _seed_demo_data(self) -> None:
        result = self._seed_service.seed_demo_data()
        if result.customers_created == 0 and result.orders_created == 0:
            messagebox.showinfo(
                "Seed Demo Data",
                "Demo data already exists. Clear the database to reseed.",
            )
            return
        self._load_customers()
        self._load_orders()
        self._load_reports()
        messagebox.showinfo(
            "Seed Demo Data",
            f"Created {result.customers_created} customer(s) and "
            f"{result.orders_created} order(s).",
        )
