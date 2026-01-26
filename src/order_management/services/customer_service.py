from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from order_management.data.customer_repository import CustomerRepository
from order_management.data.db import init_db


@dataclass
class CustomerPayload:
    name: str
    contact_name: str
    email: str
    phone: str
    notes: str


class CustomerService:
    def __init__(self) -> None:
        init_db()
        self._repo = CustomerRepository()

    def list_customers(self) -> list[dict[str, Any]]:
        return self._repo.list_customers()

    def get_customer(self, customer_id: int) -> dict[str, Any] | None:
        return self._repo.get_customer(customer_id)

    def create_customer(self, payload: dict[str, Any]) -> int:
        return self._repo.create_customer(payload)

    def update_customer(self, customer_id: int, payload: dict[str, Any]) -> None:
        self._repo.update_customer(customer_id, payload)

    def delete_customer(self, customer_id: int) -> None:
        self._repo.delete_customer(customer_id)

    def count_linked_orders(self, customer_id: int) -> int:
        return self._repo.count_linked_orders(customer_id)
