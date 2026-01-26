from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def _app_data_dir() -> Path:
    app_name = "bp-order-management"
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "BP Order Management"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "BP Order Management"
    return Path.home() / ".local" / "share" / app_name


APP_DIR = _app_data_dir()
DB_PATH = APP_DIR / "order_management.sqlite3"


def get_connection() -> sqlite3.Connection:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                customer_id INTEGER,
                customer_name TEXT NOT NULL,
                status TEXT NOT NULL,
                deadline TEXT NOT NULL,
                value REAL NOT NULL DEFAULT 0.0,
                priority TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
            """
        )

        _ensure_column(conn, "orders", "customer_id", "INTEGER")
        _ensure_column(conn, "orders", "customer_name", "TEXT NOT NULL DEFAULT ''")

        _migrate_customers(conn)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _migrate_customers(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT COUNT(*) FROM customers").fetchone()
    if rows and rows[0] > 0:
        return
    distinct = conn.execute(
        "SELECT DISTINCT customer_name FROM orders WHERE customer_name != ''"
    ).fetchall()
    if not distinct:
        return
    now = datetime.utcnow().isoformat(timespec="seconds")
    for row in distinct:
        name = row[0]
        try:
            conn.execute(
                """
                INSERT INTO customers (name, contact_name, email, phone, notes, created_at, updated_at)
                VALUES (?, '', '', '', '', ?, ?)
                """,
                (name, now, now),
            )
        except sqlite3.IntegrityError:
            continue
    conn.execute(
        """
        UPDATE orders
        SET customer_id = (
            SELECT id FROM customers WHERE customers.name = orders.customer_name
        )
        WHERE customer_id IS NULL AND customer_name != ''
        """
    )
