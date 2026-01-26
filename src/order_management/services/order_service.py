from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fpdf import FPDF
from order_management.data.db import APP_DIR, init_db
from order_management.data.order_repository import OrderRepository

STATUS_OPTIONS = ("Open", "Feedback", "Closed")
PRIORITY_OPTIONS = ("Low", "Normal", "High")


@dataclass
class OrderFilters:
    status: str | None = None
    exclude_status: str | None = None
    customer_id: int | None = None
    customer: str | None = None
    search: str | None = None
    deadline_from: str | None = None
    deadline_to: str | None = None


class OrderService:
    def __init__(self) -> None:
        init_db()
        self._repo = OrderRepository()

    def list_orders(self, filters: OrderFilters | None = None) -> list[dict[str, Any]]:
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
        return self._repo.get_order(order_id)

    def create_order(self, payload: dict[str, Any]) -> int:
        payload = payload.copy()
        payload["order_no"] = self._next_order_no()
        return self._repo.create_order(payload)

    def update_order(self, order_id: int, payload: dict[str, Any]) -> None:
        self._repo.update_order(order_id, payload)

    def list_images(self, order_id: int) -> list[dict[str, Any]]:
        return self._repo.list_images(order_id)

    def add_images(
        self, order_id: int, source_paths: list[Path]
    ) -> list[dict[str, Any]]:
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

    def delete_order(self, order_id: int) -> None:
        images = self._repo.list_images(order_id)
        for image in images:
            file_path = Path(str(image.get("file_path", "")))
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError:
                pass
        self._repo.delete_order(order_id)

    def export_order_form(self, order_id: int) -> Path:
        order = self._repo.get_order(order_id)
        if not order:
            raise ValueError("Order not found")
        images = self._repo.list_images(order_id)
        export_dir = self._export_dir()
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{order['order_no']}_service_order.pdf"
        output_path = export_dir / filename
        pdf_bytes = self._render_order_form_pdf(order, images)
        output_path.write_bytes(pdf_bytes)
        return output_path

    def status_summary(self) -> list[dict[str, Any]]:
        return self._repo.status_summary()

    def overdue_orders(self) -> list[dict[str, Any]]:
        today = date.today().strftime("%Y-%m-%d")
        return self._repo.list_overdue(today)

    def due_soon_orders(self, days: int = 7) -> list[dict[str, Any]]:
        today = date.today()
        through = today + timedelta(days=days)
        return self._repo.list_due_soon(
            today.strftime("%Y-%m-%d"), through.strftime("%Y-%m-%d")
        )

    def export_reports(self, days: int = 7) -> Path:
        summary = self.status_summary()
        overdue = self.overdue_orders()
        due_soon = self.due_soon_orders(days=days)
        export_dir = self._export_dir()
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = export_dir / f"reports_{timestamp}.pdf"
        pdf_bytes = self._render_reports_pdf(summary, overdue, due_soon, days)
        output_path.write_bytes(pdf_bytes)
        return output_path

    def _logo_data_uri(self) -> str:
        logo_path = self._logo_path()
        if not logo_path.exists():
            return ""
        encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _logo_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "assets" / "bp-logo.png"

    def _export_dir(self) -> Path:
        return Path.home() / "Downloads" / "bp-order-management"

    def _next_order_no(self) -> str:
        max_id = self._repo.get_max_order_id()
        return f"ORD-{max_id + 1:06d}"

    def _format_date(self, value: object) -> str:
        if not value:
            return ""
        try:
            parsed = datetime.strptime(str(value), "%Y-%m-%d")
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            return str(value)

    def _render_order_form(
        self, order: dict[str, Any], images: list[dict[str, Any]]
    ) -> str:
        image_list = (
            "".join(f"<li>{img['file_name']}</li>" for img in images) or "<li>None</li>"
        )
        image_gallery = self._render_image_gallery(images)
        value = float(order.get("value") or 0.0)
        customer_name = (
            order.get("customer_display") or order.get("customer_name") or ""
        )
        deadline = self._format_date(order.get("deadline"))
        logo_uri = self._logo_data_uri()
        logo_html = (
            f'<img src="{logo_uri}" alt="Logo" style="height:48px;" />'
            if logo_uri
            else ""
        )
        return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Service Order Form - {order["order_no"]}</title>
  <style>
    body {{
      font-family: "Segoe UI", Tahoma, sans-serif;
      margin: 32px;
      color: #111;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #222;
      padding-bottom: 12px;
      margin-bottom: 20px;
    }}
    .title {{
      font-size: 22px;
      font-weight: 700;
    }}
    .section {{
      margin-bottom: 18px;
    }}
    .label {{
      font-weight: 600;
      width: 160px;
      display: inline-block;
    }}
    .box {{
      border: 1px solid #444;
      padding: 12px;
      min-height: 72px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    td {{
      padding: 6px 8px;
      border: 1px solid #999;
    }}
    .signature {{
      margin-top: 30px;
    }}
  </style>
</head>
<body>
  <div class="header" style="align-items:center;">
    <div style="display:flex; align-items:center; gap:16px;">
      {logo_html}
      <div>
        <div class="title">Service Order Form</div>
        <div>Order: {order["order_no"]}</div>
        <div>Status: {order["status"]}</div>
      </div>
    </div>
    <div>
      <div><strong>Customer</strong></div>
      <div>{customer_name}</div>
    </div>
  </div>

  <div class="section">
    <table>
      <tr>
        <td><span class="label">Title</span>{order["title"]}</td>
        <td><span class="label">Deadline</span>{deadline}</td>
      </tr>
      <tr>
        <td><span class="label">Priority</span>{order["priority"]}</td>
        <td><span class="label">Value</span>${value:,.2f}</td>
      </tr>
    </table>
  </div>

  <div class="section">
    <div class="label">Description / Brief</div>
    <div class="box">{order["description"]}</div>
  </div>

  <div class="section">
    <div class="label">Reference Images</div>
    {image_gallery}
    <ul>{image_list}</ul>
  </div>

  <div class="signature">
    <div><span class="label">Approved By</span> ____________________________</div>
    <div style="margin-top: 12px;"><span class="label">Date</span> ____________________________</div>
  </div>
</body>
</html>
"""

    def _render_order_form_pdf(
        self, order: dict[str, Any], images: list[dict[str, Any]]
    ) -> bytes:
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        logo_path = self._logo_path()
        start_y = pdf.get_y()
        if logo_path.exists():
            logo_w = 30
            logo_h = 12
            logo_x = pdf.w - pdf.r_margin - logo_w
            pdf.image(
                str(logo_path),
                x=logo_x,
                y=start_y,
                w=logo_w,
                h=logo_h,
                keep_aspect_ratio=True,
            )

        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Service Order Form", ln=1)

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Order: {order.get('order_no', '')}", ln=1)
        pdf.cell(0, 6, f"Status: {order.get('status', '')}", ln=1)
        pdf.cell(0, 6, f"Customer: {order.get('customer_display') or order.get('customer_name') or ''}", ln=1)
        pdf.ln(2)

        value = float(order.get("value") or 0.0)
        deadline = self._format_date(order.get("deadline"))
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Order Details", ln=1)
        pdf.set_font("Helvetica", "", 9)
        col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 2
        row_h = 6
        pdf.cell(col_w, row_h, f"Title: {order.get('title', '')}", border=1)
        pdf.cell(col_w, row_h, f"Deadline: {deadline}", border=1, ln=1)
        pdf.cell(col_w, row_h, f"Priority: {order.get('priority', '')}", border=1)
        pdf.cell(col_w, row_h, f"Value: ${value:,.2f}", border=1, ln=1)
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Description / Brief", ln=1)
        pdf.set_font("Helvetica", "", 9)
        description = str(order.get("description", "") or "")
        pdf.multi_cell(0, 5, description or " ", border=1)
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Reference Images", ln=1)
        pdf.set_font("Helvetica", "", 9)
        if not images:
            pdf.cell(0, 6, "None", ln=1)
        else:
            for image in images:
                pdf.cell(0, 5, str(image.get("file_name", "")), ln=1)

        pdf.ln(4)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "Approved By: ____________________________", ln=1)
        pdf.cell(0, 6, "Date: ____________________________", ln=1)

        if images:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Reference Images", ln=1)
            pdf.set_font("Helvetica", "", 9)
            max_h = 80
            for image in images:
                file_path = Path(str(image.get("file_path", "")))
                caption = str(image.get("file_name", ""))
                if not file_path.exists():
                    pdf.cell(0, 5, f"Missing: {caption}", ln=1)
                    continue
                if pdf.get_y() + max_h + 12 > pdf.page_break_trigger:
                    pdf.add_page()
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 5, caption, ln=1)
                try:
                    pdf.image(
                        str(file_path),
                        w=pdf.epw,
                        h=max_h,
                        keep_aspect_ratio=True,
                    )
                except RuntimeError:
                    pdf.multi_cell(0, 5, "Unsupported image", border=1)
                pdf.ln(3)

        pdf_bytes = pdf.output(dest="S")
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin-1")
        return pdf_bytes

    def _render_image_gallery(self, images: list[dict[str, Any]]) -> str:
        if not images:
            return '<div class="box">None</div>'
        cards: list[str] = []
        for image in images:
            file_path = Path(str(image.get("file_path", "")))
            if not file_path.exists():
                continue
            mime, _ = mimetypes.guess_type(str(file_path))
            if not mime:
                mime = "image/png"
            encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
            data_uri = f"data:{mime};base64,{encoded}"
            cards.append(
                f'<div style="border:1px solid #bbb; padding:6px; margin:6px; display:inline-block;">'
                f'<div style="font-size:12px; margin-bottom:4px;">{image.get("file_name", "")}</div>'
                f'<img src="{data_uri}" alt="{image.get("file_name", "")}" style="max-height:180px; max-width:240px;" />'
                f"</div>"
            )
        if not cards:
            return '<div class="box">None</div>'
        return "<div>" + "".join(cards) + "</div>"

    def _render_reports(
        self,
        summary: list[dict[str, Any]],
        overdue: list[dict[str, Any]],
        due_soon: list[dict[str, Any]],
        days: int,
    ) -> str:
        def row_cells(items: list[str]) -> str:
            return "".join(f"<td>{item}</td>" for item in items)

        summary_rows = ""
        for row in summary:
            total_value = float(row.get("total_value") or 0.0)
            summary_rows += (
                "<tr>"
                + row_cells(
                    [
                        row.get("status", ""),
                        str(row.get("order_count", 0)),
                        f"${total_value:,.2f}",
                    ]
                )
                + "</tr>"
            )
        summary_rows = summary_rows or '<tr><td colspan="3">No data</td></tr>'

        def order_row(row: dict[str, Any]) -> str:
            value = float(row.get("value") or 0.0)
            deadline = self._format_date(row.get("deadline"))
            customer = row.get("customer_display") or row.get("customer_name") or ""
            cells = [
                row.get("order_no", ""),
                row.get("title", ""),
                customer,
                deadline,
                f"${value:,.2f}",
                row.get("status", ""),
            ]
            return f"<tr>{row_cells(cells)}</tr>"

        overdue_rows = (
            "".join(order_row(row) for row in overdue)
            or '<tr><td colspan="6">None</td></tr>'
        )
        due_soon_rows = (
            "".join(order_row(row) for row in due_soon)
            or '<tr><td colspan="6">None</td></tr>'
        )
        generated = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        logo_uri = self._logo_data_uri()
        logo_html = (
            f'<img src="{logo_uri}" alt="Logo" style="height:48px;" />'
            if logo_uri
            else ""
        )

        return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Operational Reports</title>
  <style>
    body {{
      font-family: "Segoe UI", Tahoma, sans-serif;
      margin: 32px;
      color: #111;
    }}
    h1 {{
      font-size: 22px;
      margin-bottom: 4px;
    }}
    .meta {{
      color: #555;
      margin-bottom: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 18px;
    }}
    th, td {{
      border: 1px solid #999;
      padding: 6px 8px;
      text-align: left;
    }}
    th {{
      background: #efefef;
    }}
  </style>
</head>
<body>
  <div style="display:flex; align-items:center; gap:16px;">
    {logo_html}
    <h1>Operational Reports</h1>
  </div>
  <div class="meta">Generated: {generated}</div>

  <h2>Status Summary</h2>
  <table>
    <tr><th>Status</th><th>Orders</th><th>Total Value</th></tr>
    {summary_rows}
  </table>

  <h2>Overdue (Open/Feedback)</h2>
  <table>
    <tr><th>Order</th><th>Title</th><th>Customer</th><th>Deadline</th><th>Value</th><th>Status</th></tr>
    {overdue_rows}
  </table>

  <h2>Due Soon (Next {days} Days)</h2>
  <table>
    <tr><th>Order</th><th>Title</th><th>Customer</th><th>Deadline</th><th>Value</th><th>Status</th></tr>
    {due_soon_rows}
  </table>
</body>
</html>
"""

    def _render_reports_pdf(
        self,
        summary: list[dict[str, Any]],
        overdue: list[dict[str, Any]],
        due_soon: list[dict[str, Any]],
        days: int,
    ) -> bytes:
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)

        logo_path = self._logo_path()
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        if logo_path.exists():
            pdf.image(str(logo_path), x=start_x, y=start_y, h=12)
            pdf.set_x(start_x + 16)
        pdf.cell(0, 10, "Operational Reports", ln=1)

        generated = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(85, 85, 85)
        pdf.cell(0, 6, f"Generated: {generated}", ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        def split_lines(width: float, text: str) -> list[str]:
            if not text:
                return [""]
            lines = pdf.multi_cell(width, 5, text, split_only=True)
            return lines or [""]

        def table(
            headers: list[str], rows: list[list[str]], col_widths: list[float]
        ) -> None:
            line_height = 5
            header_height = 6
            pdf.set_fill_color(239, 239, 239)
            pdf.set_font("Helvetica", "B", 9)
            for header, width in zip(headers, col_widths, strict=True):
                pdf.cell(width, header_height, header, border=1, align="L", fill=True)
            pdf.ln(header_height)
            pdf.set_font("Helvetica", "", 9)

            def ensure_page_space(height: float) -> None:
                if pdf.get_y() + height > pdf.page_break_trigger:
                    pdf.add_page()
                    pdf.set_fill_color(239, 239, 239)
                    pdf.set_font("Helvetica", "B", 9)
                    for header, width in zip(headers, col_widths, strict=True):
                        pdf.cell(
                            width,
                            header_height,
                            header,
                            border=1,
                            align="L",
                            fill=True,
                        )
                    pdf.ln(header_height)
                    pdf.set_font("Helvetica", "", 9)

            for row in rows:
                cells = [str(cell) for cell in row]
                cell_lines = [
                    split_lines(width, text) for width, text in zip(col_widths, cells)
                ]
                max_lines = max(len(lines) for lines in cell_lines)
                row_height = line_height * max_lines
                ensure_page_space(row_height)
                x = pdf.get_x()
                y = pdf.get_y()
                for width, lines in zip(col_widths, cell_lines):
                    text = "\n".join(lines)
                    pdf.multi_cell(
                        width,
                        line_height,
                        text,
                        border=1,
                        align="L",
                        max_line_height=line_height,
                    )
                    pdf.set_xy(x + width, y)
                    x += width
                pdf.set_xy(pdf.l_margin, y + row_height)

        summary_rows: list[list[str]] = []
        for row in summary:
            total_value = float(row.get("total_value") or 0.0)
            summary_rows.append(
                [
                    str(row.get("status", "")),
                    str(row.get("order_count", 0)),
                    f"${total_value:,.2f}",
                ]
            )
        if not summary_rows:
            summary_rows = [["No data", "", ""]]

        def order_row(row: dict[str, Any]) -> list[str]:
            value = float(row.get("value") or 0.0)
            deadline = self._format_date(row.get("deadline"))
            customer = row.get("customer_display") or row.get("customer_name") or ""
            return [
                str(row.get("order_no", "")),
                str(row.get("title", "")),
                str(customer),
                str(deadline),
                f"${value:,.2f}",
                str(row.get("status", "")),
            ]

        overdue_rows = [order_row(row) for row in overdue]
        if not overdue_rows:
            overdue_rows = [["None", "", "", "", "", ""]]

        due_soon_rows = [order_row(row) for row in due_soon]
        if not due_soon_rows:
            due_soon_rows = [["None", "", "", "", "", ""]]

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Status Summary", ln=1)
        table(
            ["Status", "Orders", "Total Value"],
            summary_rows,
            [70, 30, 40],
        )

        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Overdue (Open/Feedback)", ln=1)
        table(
            ["Order", "Title", "Customer", "Deadline", "Value", "Status"],
            overdue_rows,
            [22, 50, 38, 22, 24, 24],
        )

        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, f"Due Soon (Next {days} Days)", ln=1)
        table(
            ["Order", "Title", "Customer", "Deadline", "Value", "Status"],
            due_soon_rows,
            [22, 50, 38, 22, 24, 24],
        )

        pdf_bytes = pdf.output(dest="S")
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin-1")
        return pdf_bytes
