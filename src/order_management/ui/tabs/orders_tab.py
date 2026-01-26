"""Orders tab controller."""

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from tkcalendar import DateEntry

from order_management.services.order_service import (
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    OrderFilters,
    OrderService,
)
from order_management.ui.constants import IMAGE_FILE_TYPES
from order_management.ui.file_utils import open_exports_folder, open_path
from order_management.ui.widgets import ButtonBar, clear_treeview, configure_treeview_tags
from order_management.utils import date_status, format_date, format_datetime, parse_date


class OrdersTabController:
    """Controller for the Orders tab."""

    def __init__(
        self,
        parent: ttk.Frame,
        order_service: OrderService,
        layout: dict[str, int],
        set_status: Callable[[str], None],
        on_data_changed: Callable[[], None],
    ) -> None:
        """Initialize the orders tab.

        Args:
            parent: Parent frame for the tab.
            order_service: Order service instance.
            layout: Layout configuration dictionary.
            set_status: Callback to set status bar message.
            on_data_changed: Callback when orders are modified.
        """
        self._order_service = order_service
        self._layout = layout
        self._set_status = set_status
        self._on_data_changed = on_data_changed

        self._current_order_id: int | None = None
        self._orders_cache: list[dict[str, Any]] = []
        self._images_cache: list[dict[str, Any]] = []
        self._customers_by_name: dict[str, int] = {}
        self._sort_column = "deadline"
        self._sort_desc = False

        self._build_ui(parent)

    def _build_ui(self, parent: ttk.Frame) -> None:
        """Build the orders tab UI."""
        self._build_filters(parent)
        self._build_orders_list(parent)
        self._build_detail_form(parent)

    def _build_filters(self, parent: ttk.Frame) -> None:
        """Build the filters section."""
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
            command=self.load_orders,
        ).grid(row=1, column=5, sticky="w", padx=(0, 10))

        ttk.Button(
            filter_body, text="Apply", style="Action.TButton", command=self.load_orders
        ).grid(row=1, column=6, padx=(6, 4))
        ttk.Button(
            filter_body,
            text="Clear",
            style="Action.TButton",
            command=self._clear_filters,
        ).grid(row=1, column=7, padx=(0, 6))

    def _build_orders_list(self, parent: ttk.Frame) -> None:
        """Build the orders list section."""
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
        configure_treeview_tags(self._orders_tree)
        self._orders_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self._orders_tree.bind("<<TreeviewSelect>>", self._on_select_order)

    def _build_detail_form(self, parent: ttk.Frame) -> None:
        """Build the order detail form section."""
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

        actions = ButtonBar(
            detail_frame,
            [
                ("New Order", self.new_order),
                ("Save Order", self.save_order),
                ("Delete Order", self.delete_order),
                ("Export Form", self._export_form),
                ("Add Image", self._add_images),
                ("Remove Image", self._remove_image),
                ("View Image", self._view_image),
            ],
            padding=(self._layout["section_padx"], 0),
        )
        actions.pack(fill="x", pady=(0, 6))

    def update_customer_lists(
        self, names: list[str], customers_by_name: dict[str, int]
    ) -> None:
        """Update the customer dropdown lists.

        Args:
            names: List of customer names.
            customers_by_name: Mapping of names to customer IDs.
        """
        self._customers_by_name = customers_by_name
        self._customer_combo.configure(values=names)
        self._filter_customer_combo.configure(values=("",) + tuple(names))

    def load_orders(self) -> None:
        """Load orders with current filters."""
        deadline_from_raw = self._filter_deadline_from.get().strip()
        deadline_to_raw = self._filter_deadline_to.get().strip()
        deadline_from = parse_date(deadline_from_raw) if deadline_from_raw else None
        deadline_to = parse_date(deadline_to_raw) if deadline_to_raw else None
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
        """Refresh the orders treeview."""
        clear_treeview(self._orders_tree)
        for row in self._orders_cache:
            value = float(row.get("value") or 0.0)
            deadline = format_date(row.get("deadline"))
            updated = format_datetime(row.get("updated_at"))
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
            status = date_status(row.get("deadline"))
            if status in ("overdue", "due_today", "due_soon"):
                self._orders_tree.item(item_id, tags=(status,))

    def _clear_filters(self) -> None:
        """Clear all filters."""
        self._filter_status.set("")
        self._filter_customer.set("")
        self._filter_search.set("")
        self._filter_deadline_from.set("")
        self._filter_deadline_to.set("")
        self._filter_show_closed.set(False)
        self.load_orders()

    def _apply_sort(self) -> None:
        """Apply current sort to orders cache."""
        key = self._sort_column

        def sort_key(row: dict[str, Any]) -> Any:
            value = row.get(key)
            if key == "value":
                try:
                    return float(value or 0.0)
                except (TypeError, ValueError):
                    return 0.0
            return value or ""

        self._orders_cache.sort(key=sort_key, reverse=self._sort_desc)

    def _sort_orders(self, column: str) -> None:
        """Sort orders by column."""
        if self._sort_column == column:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_column = column
            self._sort_desc = False
        self._apply_sort()
        self._refresh_orders_tree()

    def _on_select_order(self, _event: tk.Event) -> None:
        """Handle order selection."""
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
        self._set_deadline_display(format_date(order.get("deadline")))
        self._value.set(f"{float(order.get('value') or 0.0):.2f}")
        self._priority.set(order.get("priority", PRIORITY_OPTIONS[1]))
        self._description.delete("1.0", "end")
        self._description.insert("1.0", order.get("description", ""))
        self._load_images(order_id)
        self._set_status(f"Loaded {order.get('order_no')}")

    def _load_images(self, order_id: int) -> None:
        """Load images for an order."""
        self._images_cache = self._order_service.list_images(order_id)
        self._images_list.delete(0, "end")
        for image in self._images_cache:
            self._images_list.insert("end", image.get("file_name"))

    def _set_deadline_display(self, value: str) -> None:
        """Set the deadline entry display value."""
        if not value:
            self._deadline.set("")
            self._deadline_entry.delete(0, "end")
            return
        from datetime import datetime
        from order_management.utils import DATE_DISPLAY, DATE_STORAGE
        for fmt in (DATE_DISPLAY, DATE_STORAGE):
            try:
                parsed = datetime.strptime(value, fmt)
                self._deadline_entry.set_date(parsed)
                return
            except ValueError:
                continue
        self._deadline.set(value)

    def new_order(self) -> None:
        """Clear form for a new order."""
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
        self._set_status("Creating new order")

    def save_order(self) -> None:
        """Save the current order."""
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
        self.load_orders()
        self._on_data_changed()
        if self._current_order_id is not None:
            item_id = str(self._current_order_id)
            if self._orders_tree.exists(item_id):
                self._orders_tree.selection_set(item_id)
                self._orders_tree.see(item_id)

    def delete_order(self) -> None:
        """Delete the selected order."""
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
        self.new_order()
        self.load_orders()
        self._on_data_changed()
        self._set_status("Order deleted")

    def _collect_form_payload(self) -> dict[str, Any] | None:
        """Collect and validate form data."""
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
        deadline = parse_date(deadline_raw)
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

    def _add_images(self) -> None:
        """Add images to the current order."""
        if self._current_order_id is None:
            messagebox.showinfo("Save First", "Save the order before adding images.")
            return
        paths = filedialog.askopenfilenames(
            title="Add Reference Images",
            filetypes=IMAGE_FILE_TYPES,
        )
        if not paths:
            return
        source_paths = [Path(path) for path in paths]
        self._order_service.add_images(self._current_order_id, source_paths)
        self._load_images(self._current_order_id)
        self._set_status(f"Added {len(paths)} image(s)")

    def _remove_image(self) -> None:
        """Remove the selected image."""
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
        """Handle double-click to view image."""
        self._view_image()

    def _view_image(self) -> None:
        """View the selected image."""
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
        """Export the current order as PDF."""
        if self._current_order_id is None:
            messagebox.showinfo("Export", "Select an order to export.")
            return
        try:
            output_path = self._order_service.export_order_form(self._current_order_id)
        except ValueError as exc:
            messagebox.showerror("Export Failed", str(exc))
            return
        open_path(output_path)
        if messagebox.askyesno(
            "Export Complete",
            f"Service order form saved to:\n{output_path}\n\nOpen the exports folder?",
        ):
            open_exports_folder()
        self._set_status("Exported service order form")

    @property
    def current_order_id(self) -> int | None:
        """Get the currently selected order ID."""
        return self._current_order_id
