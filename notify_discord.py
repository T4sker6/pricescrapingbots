import requests
from db import get_connection

WEBHOOK_URL = "PASTE_YOUR_DISCORD_WEBHOOK_URL_HERE"

HM_RED = 0xE50010


def get_pending_products() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM TRACKED_PRODUCTS_HM WHERE sendNotification = 1"
        ).fetchall()
    return [dict(row) for row in rows]


def mark_sent(product_id: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE TRACKED_PRODUCTS_HM SET sendNotification = 0 WHERE id = ?",
            (product_id,),
        )


def _fmt_price(val) -> str:
    return f"{val:.2f} PLN" if val is not None else "—"


def _fmt_drop(old, new) -> str:
    return f"-{(old - new) / old * 100:.1f}%" if old else "—"


def build_embed(p: dict) -> dict:
    current = p["currentPrice"]
    return {
        "title": "🏷️ PROMOCJA",
        "url": p["url"],
        "color": HM_RED,
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
    products = get_pending_products()
    if not products:
        print("Brak produktów do powiadomienia.")
        return

    for product in products:
        try:
            embed = build_embed(product)
            response = requests.post(WEBHOOK_URL, json={"embeds": [embed]})
            response.raise_for_status()
            mark_sent(product["id"])
            print(f"  Wysłano: {product['id']} - {product['name']}")
        except Exception as e:
            print(f"  ERROR dla {product['id']}: {e}")


if __name__ == "__main__":
    main()
