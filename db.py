import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "prices.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS TRACKED_PRODUCTS (
                id               TEXT    NOT NULL,
                store            TEXT    NOT NULL,
                name             TEXT    NOT NULL,
                minPrice         REAL,
                maxPrice         REAL,
                lastPrice        REAL,
                currentPrice     REAL    NOT NULL,
                url              TEXT    NOT NULL,
                sendNotification INTEGER NOT NULL DEFAULT 0,
                createdOn        TEXT    NOT NULL DEFAULT (datetime('now')),
                lastUpdatedOn    TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (id, store)
            )
        """)


def get_tracked_products_for_scraping() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, store, url FROM TRACKED_PRODUCTS"
        ).fetchall()
    return [dict(row) for row in rows]


def add_tracked_product(product_id: str, url: str, store: str):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO TRACKED_PRODUCTS (id, store, name, currentPrice, url)
            VALUES (?, ?, 'Ładowanie...', 0, ?)
        """,
            (product_id, store, url),
        )


def remove_tracked_product(product_id: str, store: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM TRACKED_PRODUCTS WHERE id = ? AND store = ?",
            (product_id, store),
        )
        return cursor.rowcount > 0


def get_all_products(store: str = None) -> list[dict]:
    with get_connection() as conn:
        if store:
            rows = conn.execute(
                "SELECT * FROM TRACKED_PRODUCTS WHERE store = ? ORDER BY createdOn DESC",
                (store,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM TRACKED_PRODUCTS ORDER BY store, createdOn DESC"
            ).fetchall()
    return [dict(row) for row in rows]


def upsert_product(product: dict):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO TRACKED_PRODUCTS (id, store, name, minPrice, maxPrice, lastPrice, currentPrice, url)
            VALUES (:id, :store, :name, :price, :price, NULL, :price, :url)
            ON CONFLICT(id, store) DO UPDATE SET
                name             = excluded.name,
                lastPrice        = CASE WHEN currentPrice = 0 THEN NULL ELSE currentPrice END,
                currentPrice     = excluded.currentPrice,
                minPrice         = MIN(COALESCE(minPrice, excluded.currentPrice), excluded.currentPrice),
                maxPrice         = MAX(COALESCE(maxPrice, excluded.currentPrice), excluded.currentPrice),
                sendNotification = CASE WHEN excluded.currentPrice < currentPrice THEN 1 ELSE sendNotification END,
                lastUpdatedOn    = CASE WHEN excluded.currentPrice != currentPrice THEN datetime('now', 'localtime') ELSE lastUpdatedOn END
        """,
            {
                "id": product["id"],
                "store": product["store"],
                "name": product["name"],
                "price": product["price"],
                "url": product["url"],
            },
        )
