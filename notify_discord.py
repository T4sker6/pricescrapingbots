import json
import requests
from pathlib import Path
from db import get_connection

STORES_PATH = Path(__file__).parent / "stores.json"


def load_stores():
    return json.loads(STORES_PATH.read_text())


def get_pending_products() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM TRACKED_PRODUCTS WHERE sendNotification = 1"
        ).fetchall()
    return [dict(row) for row in rows]


def mark_sent(product_id: str, store: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE TRACKED_PRODUCTS SET sendNotification = 0 WHERE id = ? AND store = ?",
            (product_id, store),
        )


def _fmt_price(val) -> str:
    return f"{val:.2f} PLN" if val is not None else "—"


def _fmt_drop(old, new) -> str:
    return f"-{(old - new) / old * 100:.1f}%" if old else "—"


def build_embed(p: dict, store_cfg: dict) -> dict:
    current = p["currentPrice"]
    return {
        "title": f"🏷️ PROMOCJA — {store_cfg['name']}",
        "url": p["url"],
        "color": store_cfg["color"],
        "fields": [
            {
                "name": f"`{p['id']}` — {p['name']}",
                "value": (
                    f"Cena zmieniła się **{p['lastUpdatedOn']}**\n"
                    f"**{_fmt_price(p['lastPrice'])}** → **{_fmt_price(current)}**\n"
                    f"Najwyższa: {_fmt_price(p['maxPrice'])} | Najniższa: {_fmt_price(p['minPrice'])}\n"
                    f"Względna zmiana: **{_fmt_drop(p['lastPrice'], current)}** | Od max: **{_fmt_drop(p['maxPrice'], current)}**"
                ),
            }
        ],
    }


def main():
    stores = load_stores()
    products = get_pending_products()
    if not products:
        print("Brak produktów do powiadomienia.")
        return

    for product in products:
        store_key = product["store"]
        store_cfg = stores.get(store_key)
        if not store_cfg:
            print(f"  Nieznany sklep '{store_key}' dla {product['id']}, pomijam.")
            continue

        webhook = store_cfg.get("discordWebhook", "")
        if not webhook or webhook == "PASTE_WEBHOOK_URL_HERE":
            print(f"  Brak webhooka dla sklepu '{store_key}', pomijam.")
            continue

        try:
            embed = build_embed(product, store_cfg)
            response = requests.post(webhook, json={"embeds": [embed]})
            response.raise_for_status()
            mark_sent(product["id"], product["store"])
            print(f"  Wysłano: {product['id']} ({store_key}) - {product['name']}")
        except Exception as e:
            print(f"  ERROR dla {product['id']}: {e}")


if __name__ == "__main__":
    main()
