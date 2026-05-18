"""Main application window orchestrating tab controllers."""

import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import messagebox, ttk

from order_management.data.customer_repository import CustomerRepository
from order_management.services.order_service import OrderService
from order_management.services.seed_service import SeedService
from order_management.ui.constants import (
    BG_MAIN,
    DEFAULT_LAYOUT,
    HEADER_FOREGROUND,
    PRIMARY_BLUE,
)
from order_management.ui.tabs import (
    CustomersTabController,
    OrdersTabController,
    ReportsTabController,
)
from order_management.version import get_version


class MainWindow(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self._layout = DEFAULT_LAYOUT.copy()
        self._configure_fonts()
        self.title("BP Order Management")
        self.minsize(1120, 480)
        self.configure(bg=BG_MAIN)

        self._order_service = OrderService()
        self._customer_repository = CustomerRepository()
        self._seed_service = SeedService()

        self._configure_style()
        self._load_assets()
        self.iconphoto(True, self._logo_image)

        self._build_menu()
        self._build_statusbar()
        self._build_main_content()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._load_data()

    def _configure_fonts(self) -> None:
        """Configure default font sizes."""
        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkFixedFont",
            "TkMenuFont",
            "TkHeadingFont",
        ):
            tkfont.nametofont(name).configure(size=8)

    def _configure_style(self) -> None:
        """Configure ttk styles."""
        style = ttk.Style(self)
        style.configure("Toolbar.TFrame", padding=(self._layout["panel_padx"], 4))
        style.configure("Header.TFrame", background=PRIMARY_BLUE)
        style.configure("Header.TLabel", background=PRIMARY_BLUE, foreground=HEADER_FOREGROUND)
        style.configure("Filter.TLabel", padding=(0, 0, 6, 0))
        style.configure("Action.TButton", padding=(8, 2))

    def _load_assets(self) -> None:
        """Load application assets."""
        assets_dir = Path(__file__).resolve().parents[1] / "assets"
        logo_path = assets_dir / "bp-logo.png"
        self._logo_image = tk.PhotoImage(file=str(logo_path))

    def _build_menu(self) -> None:
        """Build the application menu bar."""
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
        customer_menu.add_command(label="Delete Customer", command=self._delete_customer)

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label="Seed Demo Data", command=self._seed_demo_data)
        tools_menu.add_command(label="Refresh Reports", command=self._refresh_reports)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Help Topics", state="disabled")
        help_menu.add_command(label="About", state="disabled")

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Customers", menu=customer_menu)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _build_main_content(self) -> None:
        """Build the main content area with tabs."""
        body = ttk.Frame(self, padding=self._layout["body_padding"])
        body.pack(fill="both", expand=True)

        self._build_header(body)

        self._notebook = ttk.Notebook(body)
        self._notebook.pack(fill="both", expand=True, pady=(6, 0))

        orders_tab = ttk.Frame(self._notebook)
        customers_tab = ttk.Frame(self._notebook)
        reports_tab = ttk.Frame(self._notebook)
        self._notebook.add(orders_tab, text="Orders")
        self._notebook.add(customers_tab, text="Customers")
        self._notebook.add(reports_tab, text="Reports")

        self._orders_controller = OrdersTabController(
            orders_tab,
            self._order_service,
            self._layout,
            self._set_status,
            self._on_orders_changed,
        )
        self._customers_controller = CustomersTabController(
            customers_tab,
            self._customer_repository,
            self._layout,
            self._set_status,
            self._on_customers_changed,
        )
        self._reports_controller = ReportsTabController(
            reports_tab,
            self._order_service,
            self._layout,
            self._set_status,
        )

    def _build_header(self, parent: ttk.Frame) -> None:
        """Build the header section."""
        header = ttk.Frame(parent, style="Header.TFrame")
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

    def _build_statusbar(self) -> None:
        """Build the status bar."""
        status = ttk.Frame(
            self,
            relief="sunken",
            padding=(self._layout["panel_padx"], 2),
        )
        status.pack(fill="x", side="bottom")

        self._status_left = ttk.Label(status, text="Ready", anchor="w")
        self._status_left.pack(side="left", fill="x", expand=True)

        app_version = get_version()
        if app_version:
            version_text = f"v{app_version}"
            self._status_right = ttk.Label(
                status,
                text=version_text,
                anchor="e",
            )
            self._status_right.pack(side="right", padx=(12, 0))

    def _set_status(self, message: str) -> None:
        """Set the status bar message."""
        self._status_left.configure(text=message)

    def _load_data(self) -> None:
        """Load initial data into all tabs."""
        self._customers_controller.load_customers()
        self._sync_customer_data()
        self._orders_controller.load_orders()
        self._reports_controller.load_reports()

    def _sync_customer_data(self) -> None:
        """Sync customer data to orders controller."""
        names = self._customers_controller.get_customer_names()
        customers_by_name = self._customers_controller.customers_by_name
        self._orders_controller.update_customer_lists(names, customers_by_name)

    def _on_customers_changed(self) -> None:
        """Handle customer data changes."""
        self._sync_customer_data()
        self._orders_controller.load_orders()

    def _on_orders_changed(self) -> None:
        """Handle order data changes."""
        self._reports_controller.load_reports()

    # Menu command handlers delegating to tab controllers
    def _new_order(self) -> None:
        self._notebook.select(0)
        self._orders_controller.new_order()

    def _save_order(self) -> None:
        self._orders_controller.save_order()

    def _delete_order(self) -> None:
        self._orders_controller.delete_order()

    def _export_form(self) -> None:
        self._orders_controller._export_form()

    def _new_customer(self) -> None:
        self._notebook.select(1)
        self._customers_controller.new_customer()

    def _save_customer(self) -> None:
        self._customers_controller.save_customer()

    def _delete_customer(self) -> None:
        self._customers_controller.delete_customer()

    def _refresh_reports(self) -> None:
        self._reports_controller.load_reports()

    def _seed_demo_data(self) -> None:
        """Seed demo data."""
        result = self._seed_service.seed_demo_data()
        if result.customers_created == 0 and result.orders_created == 0:
            messagebox.showinfo(
                "Seed Demo Data",
                "Demo data already exists. Clear the database to reseed.",
            )
            return
        self._load_data()
        messagebox.showinfo(
            "Seed Demo Data",
            f"Created {result.customers_created} customer(s) and {result.orders_created} order(s).",
        )

    def _on_close(self) -> None:
        """Handle window close."""
        self.destroy()
