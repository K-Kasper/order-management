"""Reports tab controller."""

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from order_management.data.settings import get_setting, set_setting
from order_management.services.order_service import OrderService
from order_management.ui.constants import PDF_FILE_TYPES, TAG_COLORS
from order_management.ui.file_utils import open_folder, open_path
from order_management.ui.widgets import ButtonBar, clear_treeview, configure_treeview_tags
from order_management.utils import format_date


class ReportsTabController:
    """Controller for the Reports tab."""

    def __init__(
        self,
        parent: ttk.Frame,
        order_service: OrderService,
        layout: dict[str, int],
        set_status: Callable[[str], None],
    ) -> None:
        """Initialize the reports tab.

        Args:
            parent: Parent frame for the tab.
            order_service: Order service instance.
            layout: Layout configuration dictionary.
            set_status: Callback to set status bar message.
        """
        self._order_service = order_service
        self._layout = layout
        self._set_status = set_status

        self._status_summary_cache: list[dict[str, Any]] = []
        self._overdue_cache: list[dict[str, Any]] = []
        self._due_soon_cache: list[dict[str, Any]] = []

        self._build_ui(parent)

    def _build_ui(self, parent: ttk.Frame) -> None:
        """Build the reports tab UI."""
        # Status Summary
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

        # Overdue
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
        self._overdue_tree.tag_configure("overdue", background=TAG_COLORS["overdue"])
        self._overdue_tree.pack(fill="both", expand=True, padx=4, pady=4)

        # Due Soon
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
        self._due_soon_tree.tag_configure(
            "due_soon", background=TAG_COLORS["due_soon"]
        )
        self._due_soon_tree.pack(fill="both", expand=True, padx=4, pady=4)

        # Actions
        actions = ButtonBar(
            parent,
            [
                ("Refresh Reports", self.load_reports),
                ("Export Reports", self._export_reports),
            ],
            padding=(self._layout["section_padx"], 0),
        )
        actions.pack(fill="x", pady=(0, 6))

    def load_reports(self) -> None:
        """Load all report data."""
        self._status_summary_cache = self._order_service.status_summary()
        self._overdue_cache = self._order_service.overdue_orders()
        self._due_soon_cache = self._order_service.due_soon_orders()
        self._refresh_status_tree()
        self._refresh_overdue_tree()
        self._refresh_due_soon_tree()
        self._set_status("Reports refreshed")

    def _refresh_status_tree(self) -> None:
        """Refresh the status summary treeview."""
        clear_treeview(self._status_tree)
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
        """Refresh the overdue orders treeview."""
        clear_treeview(self._overdue_tree)
        for row in self._overdue_cache:
            value = float(row.get("value") or 0.0)
            item_id = self._overdue_tree.insert(
                "",
                "end",
                values=(
                    row.get("order_no"),
                    row.get("title"),
                    row.get("customer_display") or row.get("customer_name"),
                    format_date(row.get("deadline")),
                    f"${value:,.2f}",
                    row.get("status"),
                ),
            )
            self._overdue_tree.item(item_id, tags=("overdue",))

    def _refresh_due_soon_tree(self) -> None:
        """Refresh the due soon orders treeview."""
        clear_treeview(self._due_soon_tree)
        for row in self._due_soon_cache:
            value = float(row.get("value") or 0.0)
            item_id = self._due_soon_tree.insert(
                "",
                "end",
                values=(
                    row.get("order_no"),
                    row.get("title"),
                    row.get("customer_display") or row.get("customer_name"),
                    format_date(row.get("deadline")),
                    f"${value:,.2f}",
                    row.get("status"),
                ),
            )
            self._due_soon_tree.item(item_id, tags=("due_soon",))

    def _default_export_dir(self) -> str:
        """Return the best default directory for exports."""
        saved = get_setting("last_export_dir")
        if saved and Path(saved).is_dir():
            return saved
        downloads = Path.home() / "Downloads"
        if downloads.is_dir():
            return str(downloads)
        return str(Path.home())

    def _export_reports(self) -> None:
        """Export reports as PDF."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports_{timestamp}.pdf"
        chosen = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=PDF_FILE_TYPES,
            initialdir=self._default_export_dir(),
            initialfile=filename,
        )
        if not chosen:
            return
        output_path = Path(chosen)
        try:
            self._order_service.export_reports(output_path)
        except OSError as exc:
            messagebox.showerror("Export Failed", str(exc))
            return
        set_setting("last_export_dir", str(output_path.parent))
        open_path(output_path)
        if messagebox.askyesno(
            "Export Complete",
            f"Reports saved to:\n{output_path}\n\nOpen the folder?",
        ):
            open_folder(output_path.parent)
        self._set_status("Exported reports")
