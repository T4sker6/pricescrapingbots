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


def build_embed(p: dict) -> dict:
    relative_drop = ((p["lastPrice"] - p["currentPrice"]) / p["lastPrice"]) * 100
    drop_from_max = ((p["maxPrice"] - p["currentPrice"]) / p["maxPrice"]) * 100
    return {
        "title": "🏷️ PROMOCJA",
        "color": HM_RED,
        "fields": [
            {
                "name": f"`{p['id']}` — {p['name']}",
                "value": (
                    f"Cena zmieniła się **{p['lastUpdatedOn']}**\n"
                    f"**{p['lastPrice']:.2f} PLN** → **{p['currentPrice']:.2f} PLN**\n"
                    f"Najwyższa: {p['maxPrice']:.2f} PLN | Najniższa: {p['minPrice']:.2f} PLN\n"
                    f"Względna zmiana: **-{relative_drop:.1f}%** | Od max: **-{drop_from_max:.1f}%**"
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
