from __future__ import annotations

from datetime import datetime
from typing import Any

from order_management.data.db import get_connection


class CustomerRepository:
    def list_customers(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM customers ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(row) for row in rows]

    def get_customer(self, customer_id: int) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE id = ?",
                (customer_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_customer(self, payload: dict[str, Any]) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds")
        payload = payload.copy()
        payload["created_at"] = now
        payload["updated_at"] = now
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO customers (
                    name, contact_name, email, phone, notes, created_at, updated_at
                )
                VALUES (
                    :name, :contact_name, :email, :phone, :notes, :created_at, :updated_at
                )
                """,
                payload,
            )
            customer_id = cursor.lastrowid
        return int(customer_id)

    def update_customer(self, customer_id: int, payload: dict[str, Any]) -> None:
        payload = payload.copy()
        payload["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
        payload["id"] = customer_id
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE customers
                SET name = :name,
                    contact_name = :contact_name,
                    email = :email,
                    phone = :phone,
                    notes = :notes,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                payload,
            )

    def delete_customer(self, customer_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE orders SET customer_id = NULL WHERE customer_id = ?",
                (customer_id,),
            )
            conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))

    def count_linked_orders(self, customer_id: int) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()
        return int(row[0]) if row else 0
