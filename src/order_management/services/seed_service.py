from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from order_management.data.customer_repository import CustomerRepository
from order_management.services.order_service import (
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    OrderService,
)


@dataclass
class SeedResult:
    customers_created: int
    orders_created: int


class SeedService:
    def __init__(self) -> None:
        self._customers = CustomerRepository()
        self._orders = OrderService()

    def seed_demo_data(self) -> SeedResult:
        customers_existing = self._customers.list_customers()
        orders_existing = self._orders.list_orders()
        if customers_existing or orders_existing:
            return SeedResult(0, 0)

        customer_payloads = [
            {
                "name": "Atelier North",
                "contact_name": "Elina Sorensen",
                "email": "elina@ateliernorth.example",
                "phone": "+46 70 555 1122",
                "notes": "Prefers matte finishes.",
            },
            {
                "name": "Studio Meridian",
                "contact_name": "Jonas Berg",
                "email": "jonas@studiomeridian.example",
                "phone": "+46 70 555 2201",
                "notes": "Rush orders possible with 48h notice.",
            },
            {
                "name": "Lumen Gallery",
                "contact_name": "Ava Lind",
                "email": "ava@lumengallery.example",
                "phone": "+46 70 555 3310",
                "notes": "Requires proof before final delivery.",
            },
        ]

        customer_ids: list[int] = []
        for payload in customer_payloads:
            customer_ids.append(self._customers.create_customer(payload))

        today = date.today()
        orders = [
            {
                "title": "Portrait commission - charcoal",
                "customer_id": customer_ids[0],
                "customer_name": customer_payloads[0]["name"],
                "status": STATUS_OPTIONS[0],
                "deadline": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
                "value": 1200.0,
                "priority": PRIORITY_OPTIONS[2],
                "description": "A3 portrait, charcoal on paper. Include soft background.",
            },
            {
                "title": "Gallery signage - acrylic",
                "customer_id": customer_ids[2],
                "customer_name": customer_payloads[2]["name"],
                "status": STATUS_OPTIONS[1],
                "deadline": (today + timedelta(days=12)).strftime("%Y-%m-%d"),
                "value": 850.0,
                "priority": PRIORITY_OPTIONS[1],
                "description": "Set of 4 acrylic signs. Provide proof layout.",
            },
            {
                "title": "Large format print - abstract",
                "customer_id": customer_ids[1],
                "customer_name": customer_payloads[1]["name"],
                "status": STATUS_OPTIONS[0],
                "deadline": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                "value": 560.0,
                "priority": PRIORITY_OPTIONS[1],
                "description": "120x90cm print. Use high-gloss stock.",
            },
            {
                "title": "Restoration consultation",
                "customer_id": customer_ids[0],
                "customer_name": customer_payloads[0]["name"],
                "status": STATUS_OPTIONS[2],
                "deadline": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
                "value": 0.0,
                "priority": PRIORITY_OPTIONS[0],
                "description": "Consultation completed; archive notes attached.",
            },
            {
                "title": "Mixed media poster series",
                "customer_id": customer_ids[2],
                "customer_name": customer_payloads[2]["name"],
                "status": STATUS_OPTIONS[0],
                "deadline": (today + timedelta(days=20)).strftime("%Y-%m-%d"),
                "value": 2200.0,
                "priority": PRIORITY_OPTIONS[2],
                "description": "Series of 3 posters, 50x70cm, mixed media.",
            },
        ]

        orders_created = 0
        for payload in orders:
            self._orders.create_order(payload)
            orders_created += 1

        return SeedResult(len(customer_ids), orders_created)
