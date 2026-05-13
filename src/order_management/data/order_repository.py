from __future__ import annotations

from datetime import datetime
from typing import Any

from order_management.data.db import get_connection


class OrderRepository:
    def list_orders(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []

        status = filters.get("status")
        if status:
            clauses.append("status = ?")
            params.append(status)

        exclude_status = filters.get("exclude_status")
        if exclude_status:
            clauses.append("status != ?")
            params.append(exclude_status)

        customer_id = filters.get("customer_id")
        if customer_id:
            clauses.append("orders.customer_id = ?")
            params.append(customer_id)

        customer = filters.get("customer")
        if customer:
            clauses.append("customers.name LIKE ?")
            params.append(f"%{customer}%")

        search = filters.get("search")
        if search:
            clauses.append(
                "(orders.title LIKE ? OR orders.description LIKE ? OR orders.order_no LIKE ?)"
            )
            params.extend([f"%{search}%"] * 3)

        deadline_from = filters.get("deadline_from")
        if deadline_from:
            clauses.append("deadline >= ?")
            params.append(deadline_from)

        deadline_to = filters.get("deadline_to")
        if deadline_to:
            clauses.append("deadline <= ?")
            params.append(deadline_to)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"""
            SELECT
                orders.*,
                COALESCE(customers.name, orders.customer_name) AS customer_display
            FROM orders
            LEFT JOIN customers ON customers.id = orders.customer_id
            {where}
            ORDER BY deadline IS NULL, deadline ASC, updated_at DESC
        """
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_order(self, order_id: int) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    orders.*,
                    COALESCE(customers.name, orders.customer_name) AS customer_display
                FROM orders
                LEFT JOIN customers ON customers.id = orders.customer_id
                WHERE orders.id = ?
                """,
                (order_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_order(self, payload: dict[str, Any]) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds")
        payload = payload.copy()
        payload["created_at"] = now
        payload["updated_at"] = now
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO orders (
                    order_no, title, customer_id, customer_name, status, deadline,
                    value, priority, description, created_at, updated_at
                )
                VALUES (
                    :order_no, :title, :customer_id, :customer_name, :status, :deadline,
                    :value, :priority, :description, :created_at, :updated_at
                )
                """,
                payload,
            )
            order_id = cursor.lastrowid
        return int(order_id)

    def update_order(self, order_id: int, payload: dict[str, Any]) -> None:
        payload = payload.copy()
        payload["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
        payload["id"] = order_id
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE orders
                SET title = :title,
                    customer_id = :customer_id,
                    customer_name = :customer_name,
                    status = :status,
                    deadline = :deadline,
                    value = :value,
                    priority = :priority,
                    description = :description,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                payload,
            )

    def list_images(self, order_id: int) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM order_images WHERE order_id = ? ORDER BY created_at",
                (order_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_image(self, image_id: int) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM order_images WHERE id = ?",
                (image_id,),
            ).fetchone()
        return dict(row) if row else None

    def add_image(self, order_id: int, file_name: str, file_path: str) -> None:
        now = datetime.utcnow().isoformat(timespec="seconds")
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO order_images (order_id, file_name, file_path, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, file_name, file_path, now),
            )

    def delete_image(self, image_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM order_images WHERE id = ?", (image_id,))

    def delete_order(self, order_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))

    def status_summary(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS order_count, SUM(value) AS total_value
                FROM orders
                GROUP BY status
                ORDER BY status
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_overdue(self, today: str) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    orders.*,
                    COALESCE(customers.name, orders.customer_name) AS customer_display
                FROM orders
                LEFT JOIN customers ON customers.id = orders.customer_id
                WHERE status != 'Closed' AND deadline < ?
                ORDER BY deadline ASC
                """,
                (today,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_due_soon(self, today: str, through: str) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    orders.*,
                    COALESCE(customers.name, orders.customer_name) AS customer_display
                FROM orders
                LEFT JOIN customers ON customers.id = orders.customer_id
                WHERE status != 'Closed' AND deadline >= ? AND deadline <= ?
                ORDER BY deadline ASC
                """,
                (today, through),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_max_order_id(self) -> int:
        with get_connection() as conn:
            row = conn.execute("SELECT MAX(id) FROM orders").fetchone()
        return row[0] or 0 if row else 0
