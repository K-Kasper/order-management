"""PDF rendering service for order forms and reports."""

from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF

from order_management.utils import format_date


class PdfService:
    """Service for rendering PDF documents."""

    def __init__(self, logo_path: Path | None = None) -> None:
        """Initialize the PDF service.

        Args:
            logo_path: Path to the logo image file.
        """
        if logo_path is None:
            logo_path = Path(__file__).resolve().parents[1] / "assets" / "bp-logo.png"
        self._logo_path = logo_path

    def render_order_form(
        self, order: dict[str, Any], images: list[dict[str, Any]]
    ) -> bytes:
        """Render a service order form as PDF.

        Args:
            order: Order data dictionary.
            images: List of image metadata dictionaries.

        Returns:
            PDF file contents as bytes.
        """
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        start_y = pdf.get_y()
        if self._logo_path.exists():
            logo_w = 30
            logo_h = 12
            logo_x = pdf.w - pdf.r_margin - logo_w
            pdf.image(
                str(self._logo_path),
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
        customer = order.get("customer_display") or order.get("customer_name") or ""
        pdf.cell(0, 6, f"Customer: {customer}", ln=1)
        pdf.ln(2)

        value = float(order.get("value") or 0.0)
        deadline = format_date(order.get("deadline"))
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
            self._render_image_pages(pdf, images)

        return self._output_pdf(pdf)

    def render_reports(
        self,
        summary: list[dict[str, Any]],
        overdue: list[dict[str, Any]],
        due_soon: list[dict[str, Any]],
        days: int,
    ) -> bytes:
        """Render operational reports as PDF.

        Args:
            summary: Status summary data.
            overdue: List of overdue orders.
            due_soon: List of orders due soon.
            days: Number of days for "due soon" window.

        Returns:
            PDF file contents as bytes.
        """
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)

        start_x = pdf.get_x()
        start_y = pdf.get_y()
        if self._logo_path.exists():
            pdf.image(str(self._logo_path), x=start_x, y=start_y, h=12)
            pdf.set_x(start_x + 16)
        pdf.cell(0, 10, "Operational Reports", ln=1)

        generated = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(85, 85, 85)
        pdf.cell(0, 6, f"Generated: {generated}", ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # Status Summary
        summary_rows = self._build_summary_rows(summary)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Status Summary", ln=1)
        self._render_table(
            pdf,
            ["Status", "Orders", "Total Value"],
            summary_rows,
            [70, 30, 40],
        )

        # Overdue
        overdue_rows = self._build_order_rows(overdue)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Overdue (Open/Feedback)", ln=1)
        self._render_table(
            pdf,
            ["Order", "Title", "Customer", "Deadline", "Value", "Status"],
            overdue_rows,
            [22, 50, 38, 22, 24, 24],
        )

        # Due Soon
        due_soon_rows = self._build_order_rows(due_soon)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, f"Due Soon (Next {days} Days)", ln=1)
        self._render_table(
            pdf,
            ["Order", "Title", "Customer", "Deadline", "Value", "Status"],
            due_soon_rows,
            [22, 50, 38, 22, 24, 24],
        )

        return self._output_pdf(pdf)

    def _render_image_pages(
        self, pdf: FPDF, images: list[dict[str, Any]]
    ) -> None:
        """Render image gallery pages."""
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

    def _build_summary_rows(
        self, summary: list[dict[str, Any]]
    ) -> list[list[str]]:
        """Build summary table rows."""
        rows: list[list[str]] = []
        for row in summary:
            total_value = float(row.get("total_value") or 0.0)
            rows.append([
                str(row.get("status", "")),
                str(row.get("order_count", 0)),
                f"${total_value:,.2f}",
            ])
        return rows or [["No data", "", ""]]

    def _build_order_rows(
        self, orders: list[dict[str, Any]]
    ) -> list[list[str]]:
        """Build order table rows."""
        rows: list[list[str]] = []
        for row in orders:
            value = float(row.get("value") or 0.0)
            deadline = format_date(row.get("deadline"))
            customer = row.get("customer_display") or row.get("customer_name") or ""
            rows.append([
                str(row.get("order_no", "")),
                str(row.get("title", "")),
                str(customer),
                str(deadline),
                f"${value:,.2f}",
                str(row.get("status", "")),
            ])
        return rows or [["None", "", "", "", "", ""]]

    def _render_table(
        self,
        pdf: FPDF,
        headers: list[str],
        rows: list[list[str]],
        col_widths: list[float],
    ) -> None:
        """Render a table with headers and rows."""
        line_height = 5
        header_height = 6
        pdf.set_fill_color(239, 239, 239)
        pdf.set_font("Helvetica", "B", 9)
        for header, width in zip(headers, col_widths, strict=True):
            pdf.cell(width, header_height, header, border=1, align="L", fill=True)
        pdf.ln(header_height)
        pdf.set_font("Helvetica", "", 9)

        for row in rows:
            cells = [str(cell) for cell in row]
            cell_lines = [
                self._split_lines(pdf, width, text)
                for width, text in zip(col_widths, cells)
            ]
            max_lines = max(len(lines) for lines in cell_lines)
            row_height = line_height * max_lines
            self._ensure_page_space(
                pdf, row_height, headers, col_widths, header_height
            )
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

    def _split_lines(self, pdf: FPDF, width: float, text: str) -> list[str]:
        """Split text into lines that fit within width."""
        if not text:
            return [""]
        lines = pdf.multi_cell(width, 5, text, split_only=True)
        return lines or [""]

    def _ensure_page_space(
        self,
        pdf: FPDF,
        height: float,
        headers: list[str],
        col_widths: list[float],
        header_height: float,
    ) -> None:
        """Ensure there's enough space on the page, adding a new page if needed."""
        if pdf.get_y() + height > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_fill_color(239, 239, 239)
            pdf.set_font("Helvetica", "B", 9)
            for header, width in zip(headers, col_widths, strict=True):
                pdf.cell(width, header_height, header, border=1, align="L", fill=True)
            pdf.ln(header_height)
            pdf.set_font("Helvetica", "", 9)

    def _output_pdf(self, pdf: FPDF) -> bytes:
        """Output PDF as bytes."""
        pdf_bytes = pdf.output(dest="S")
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin-1")
        return pdf_bytes
