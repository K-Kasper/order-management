"""Order management service handling CRUD operations and exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from order_management.data.db import APP_DIR
from order_management.data.order_repository import OrderRepository
from order_management.services.pdf_service import PdfService

STATUS_OPTIONS = ("Open", "Feedback", "Closed")
PRIORITY_OPTIONS = ("Low", "Normal", "High")


@dataclass
class OrderFilters:
    """Filter criteria for listing orders."""

    status: str | None = None
    exclude_status: str | None = None
    customer_id: int | None = None
    customer: str | None = None
    search: str | None = None
    deadline_from: str | None = None
    deadline_to: str | None = None


class OrderService:
    """Service for order CRUD operations and exports."""

    def __init__(self) -> None:
        self._repo = OrderRepository()
        self._pdf_service = PdfService()

    def list_orders(self, filters: OrderFilters | None = None) -> list[dict[str, Any]]:
        """List orders with optional filters."""
        payload: dict[str, Any] = {}
        if filters:
            payload = {
                "status": filters.status or None,
                "exclude_status": filters.exclude_status or None,
                "customer_id": filters.customer_id or None,
                "customer": filters.customer or None,
                "search": filters.search or None,
                "deadline_from": filters.deadline_from or None,
                "deadline_to": filters.deadline_to or None,
            }
        return self._repo.list_orders(payload)

    def get_order(self, order_id: int) -> dict[str, Any] | None:
        """Get a single order by ID."""
        return self._repo.get_order(order_id)

    def create_order(self, payload: dict[str, Any]) -> int:
        """Create a new order and return its ID."""
        payload = payload.copy()
        payload["order_no"] = self._next_order_no()
        return self._repo.create_order(payload)

    def update_order(self, order_id: int, payload: dict[str, Any]) -> None:
        """Update an existing order."""
        self._repo.update_order(order_id, payload)

    def delete_order(self, order_id: int) -> None:
        """Delete an order and its associated images."""
        images = self._repo.list_images(order_id)
        for image in images:
            file_path = Path(str(image.get("file_path", "")))
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError:
                pass
        self._repo.delete_order(order_id)

    def list_images(self, order_id: int) -> list[dict[str, Any]]:
        """List images for an order."""
        return self._repo.list_images(order_id)

    def add_images(self, order_id: int, source_paths: list[Path]) -> list[dict[str, Any]]:
        """Add images to an order by copying them to the uploads directory."""
        uploads_dir = APP_DIR / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        created: list[dict[str, Any]] = []
        for path in source_paths:
            if not path.exists():
                continue
            stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            target_name = f"{order_id}_{stamp}_{path.name}"
            target_path = uploads_dir / target_name
            target_path.write_bytes(path.read_bytes())
            self._repo.add_image(order_id, path.name, str(target_path))
            created.append({"file_name": path.name, "file_path": str(target_path)})
        return created

    def delete_image(self, image_id: int) -> None:
        """Delete an image by ID."""
        image = self._repo.get_image(image_id)
        self._repo.delete_image(image_id)
        if not image:
            return
        file_path = Path(str(image.get("file_path", "")))
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            pass

    def export_order_form(self, order_id: int, output_path: Path) -> Path:
        """Export an order as a PDF service order form."""
        order = self._repo.get_order(order_id)
        if not order:
            raise ValueError("Order not found")
        images = self._repo.list_images(order_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = self._pdf_service.render_order_form(order, images)
        output_path.write_bytes(pdf_bytes)
        return output_path

    def status_summary(self) -> list[dict[str, Any]]:
        """Get status summary for reports."""
        return self._repo.status_summary()

    def overdue_orders(self) -> list[dict[str, Any]]:
        """Get orders that are overdue."""
        today = date.today().strftime("%Y-%m-%d")
        return self._repo.list_overdue(today)

    def due_soon_orders(self, days: int = 7) -> list[dict[str, Any]]:
        """Get orders due within the specified number of days."""
        today = date.today()
        through = today + timedelta(days=days)
        return self._repo.list_due_soon(today.strftime("%Y-%m-%d"), through.strftime("%Y-%m-%d"))

    def export_reports(self, output_path: Path, days: int = 7) -> Path:
        """Export operational reports as PDF."""
        summary = self.status_summary()
        overdue = self.overdue_orders()
        due_soon = self.due_soon_orders(days=days)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = self._pdf_service.render_reports(summary, overdue, due_soon, days)
        output_path.write_bytes(pdf_bytes)
        return output_path

    def suggested_order_filename(self, order_id: int) -> str:
        """Return a suggested filename for an order export."""
        order = self._repo.get_order(order_id)
        if not order:
            raise ValueError("Order not found")
        return f"{order['order_no']}_service_order.pdf"

    def _next_order_no(self) -> str:
        """Generate the next order number."""
        max_id = self._repo.get_max_order_id()
        return f"ORD-{max_id + 1:06d}"
