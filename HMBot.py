import asyncio
import json
import random
import re
from playwright.async_api import async_playwright
from db import init_db, upsert_product, get_tracked_products_for_scraping

DELAY_MIN = 8
DELAY_MAX = 20

SCHEMA_RE = re.compile(
    r'<script[^>]+id="product-group-schema"[^>]*>(.*?)</script>',
    re.DOTALL,
)


async def scrape_product(page, url: str) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_load_state("networkidle", timeout=30_000)

    content = await page.content()
    match = SCHEMA_RE.search(content)
    if not match:
        print(f"  Response snippet: {content[:500]}")
        raise ValueError(f"No product-group-schema found at: {url}")

    return json.loads(match.group(1))


def extract_product_data(data: dict, product_variant_id: str) -> dict:
    variants = data.get("hasVariant", [])
    matched = [v for v in variants if v.get("sku", "").startswith(product_variant_id)]
    first = matched[0] if matched else (variants[0] if variants else {})

    offer = first.get("offers", {})
    return {
        "productVariantID": product_variant_id,
        "name": data.get("name"),
        "price": offer.get("price"),
        "url": offer.get("url"),
    }


async def main():
    init_db()

    products = get_tracked_products_for_scraping()
    if not products:
        print("Brak produktów do zescrapowania.")
        return

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="pl-PL",
            timezone_id="Europe/Warsaw",
        )
        page = await context.new_page()

        for i, product in enumerate(products):
            if i > 0:
                delay = random.uniform(DELAY_MIN, DELAY_MAX)
                print(f"Waiting {delay:.1f}s before next product...")
                await asyncio.sleep(delay)

            print(f"[{i + 1}/{len(products)}] Scraping: {product['url']}")

            try:
                data = await scrape_product(page, product["url"])
                result = extract_product_data(data, product["id"])
                upsert_product(result)
                print(f"  Saved to DB: {product['id']}")
            except Exception as e:
                print(f"  ERROR for {product['id']}: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
