"""Customers tab controller."""

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk
from typing import Any

from order_management.services.customer_service import CustomerService
from order_management.ui.widgets import ButtonBar, clear_treeview
from order_management.utils import format_datetime


class CustomersTabController:
    """Controller for the Customers tab."""

    def __init__(
        self,
        parent: ttk.Frame,
        customer_service: CustomerService,
        layout: dict[str, int],
        set_status: Callable[[str], None],
        on_data_changed: Callable[[], None],
    ) -> None:
        """Initialize the customers tab.

        Args:
            parent: Parent frame for the tab.
            customer_service: Customer service instance.
            layout: Layout configuration dictionary.
            set_status: Callback to set status bar message.
            on_data_changed: Callback when customers are modified.
        """
        self._customer_service = customer_service
        self._layout = layout
        self._set_status = set_status
        self._on_data_changed = on_data_changed

        self._current_customer_id: int | None = None
        self._customers_cache: list[dict[str, Any]] = []
        self._customers_by_name: dict[str, int] = {}
        self._customers_by_id: dict[int, dict[str, Any]] = {}

        self._build_ui(parent)

    def _build_ui(self, parent: ttk.Frame) -> None:
        """Build the customers tab UI."""
        self._build_customers_list(parent)
        self._build_detail_form(parent)

    def _build_customers_list(self, parent: ttk.Frame) -> None:
        """Build the customers list section."""
        list_frame = ttk.LabelFrame(parent, text="Customers")
        list_frame.pack(fill="both", expand=True, pady=(self._layout["section_padx"], 4))

        columns = ("name", "contact_name", "email", "phone", "updated_at")
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self._customers_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
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
        customers_scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._customers_tree.yview
        )
        self._customers_tree.configure(yscrollcommand=customers_scrollbar.set)
        self._customers_tree.pack(side="left", fill="both", expand=True)
        customers_scrollbar.pack(side="right", fill="y")
        self._customers_tree.bind("<<TreeviewSelect>>", self._on_select_customer)

    def _build_detail_form(self, parent: ttk.Frame) -> None:
        """Build the customer detail form section."""
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

        actions = ButtonBar(
            detail_frame,
            [
                ("New Customer", self.new_customer),
                ("Save Customer", self.save_customer),
                ("Delete Customer", self.delete_customer),
            ],
            padding=(self._layout["section_padx"], 0),
        )
        actions.pack(fill="x", pady=(0, 6))

    def load_customers(self) -> None:
        """Load customers from the service."""
        self._customers_cache = self._customer_service.list_customers()
        self._customers_by_name = {
            customer.get("name", ""): int(customer["id"])
            for customer in self._customers_cache
            if customer.get("name")
        }
        self._customers_by_id = {
            int(customer["id"]): customer for customer in self._customers_cache
        }
        self._refresh_customers_tree()

    def _refresh_customers_tree(self) -> None:
        """Refresh the customers treeview."""
        clear_treeview(self._customers_tree)
        for row in self._customers_cache:
            updated = format_datetime(row.get("updated_at"))
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

    def _on_select_customer(self, _event: tk.Event) -> None:
        """Handle customer selection."""
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
        self._set_status(f"Loaded customer {customer.get('name')}")

    def new_customer(self) -> None:
        """Clear form for a new customer."""
        self._current_customer_id = None
        self._cust_name.set("")
        self._cust_contact.set("")
        self._cust_email.set("")
        self._cust_phone.set("")
        self._cust_notes.delete("1.0", "end")
        self._set_status("Creating new customer")

    def save_customer(self) -> None:
        """Save the current customer."""
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
        self.load_customers()
        self._on_data_changed()
        if self._current_customer_id is not None:
            item_id = str(self._current_customer_id)
            if self._customers_tree.exists(item_id):
                self._customers_tree.selection_set(item_id)
                self._customers_tree.see(item_id)

    def delete_customer(self) -> None:
        """Delete the selected customer."""
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
        self.new_customer()
        self.load_customers()
        self._on_data_changed()
        self._set_status("Customer deleted")

    def _collect_customer_payload(self) -> dict[str, Any] | None:
        """Collect and validate customer form data."""
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

    def get_customer_names(self) -> list[str]:
        """Get list of customer names."""
        return [customer.get("name", "") for customer in self._customers_cache]

    @property
    def customers_by_name(self) -> dict[str, int]:
        """Get mapping of customer names to IDs."""
        return self._customers_by_name

    @property
    def customers_by_id(self) -> dict[int, dict[str, Any]]:
        """Get mapping of customer IDs to customer data."""
        return self._customers_by_id

    @property
    def current_customer_id(self) -> int | None:
        """Get the currently selected customer ID."""
        return self._current_customer_id
