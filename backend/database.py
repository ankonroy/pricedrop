"""SQLite storage layer for price-monitor.

Two tables:
  - products: one row per product ever added (key = url)
  - price_history: append-only, one row per scrape

Public functions:
    init_db()                              — create tables if missing
    upsert_product(url, name) -> int       — insert or update, returns product id
    add_price(product_id, price, currency, in_stock) -> int
    get_last_price(product_id) -> dict|None
    list_products() -> list[dict]
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from worker.utils.logger import get_logger

log = get_logger("database")

DB_PATH = Path(__file__).parent.parent / "data" / "prices.db"


@contextmanager
def get_db():
    """Yield a SQLite connection.

    Commits on success, rolls back on exception, always closes.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row        # rows accessible by column name
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and indexes if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id),
                price      REAL NOT NULL,
                currency   TEXT NOT NULL,
                in_stock   BOOLEAN NOT NULL,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_price_history_product_id
                ON price_history(product_id, scraped_at DESC);
        """)
    log.info("db_initialized", extra={"extra": {"path": str(DB_PATH)}})


def upsert_product(url: str, name: str) -> int:
    """Insert a product or update its name. Returns the product id."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM products WHERE url = ?", (url,)
        ).fetchone()
        if row:
            conn.execute("UPDATE products SET name = ? WHERE id = ?", (name, row["id"]))
            return row["id"]
        cur = conn.execute(
            "INSERT INTO products (url, name) VALUES (?, ?)", (url, name)
        )
        log.info("product_added", extra={"extra": {"url": url, "id": cur.lastrowid}})
        return cur.lastrowid


def add_price(product_id: int, price: float, currency: str, in_stock: bool) -> int:
    """Append a price record. Returns the price_history row id."""
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO price_history (product_id, price, currency, in_stock) "
            "VALUES (?, ?, ?, ?)",
            (product_id, price, currency, 1 if in_stock else 0),
        )
        return cur.lastrowid


def get_last_price(product_id: int) -> Optional[dict]:
    """Return the most recent price record for a product, or None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT price, currency, in_stock, scraped_at "
            "FROM price_history WHERE product_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (product_id,),
        ).fetchone()
        return dict(row) if row else None


def list_products() -> list[dict]:
    """Return every product in the DB, oldest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, url, name, created_at FROM products ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]