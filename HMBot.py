import asyncio
import json
import random
from playwright.async_api import async_playwright
from db import init_db, upsert_product, get_tracked_products_for_scraping

# Losowe opóźnienie między kolejnymi produktami (sekundy)
DELAY_MIN = 8
DELAY_MAX = 20

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['pl-PL', 'pl', 'en-US', 'en'] });
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
"""


async def scrape_product(page, url: str) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

    schema_json = await page.evaluate("""() => {
        const el = document.querySelector('script#product-group-schema[type="application/ld+json"]');
        return el ? el.textContent : null;
    }""")

    if not schema_json:
        raise ValueError(f"No product-group-schema found at: {url}")

    return json.loads(schema_json)


def extract_product_data(data: dict, product_variant_id: str) -> dict:
    variants = data.get("hasVariant", [])
    matched = [v for v in variants if v.get("sku", "").startswith(product_variant_id)]
    first = matched[0] if matched else (variants[0] if variants else {})

    offer = first.get("offers", {})
    return {
        "productGroupID": data.get("productGroupID"),
        "productVariantID": product_variant_id,
        "name": data.get("name"),
        "description": data.get("description"),
        "brand": data.get("brand", {}).get("name"),
        "material": data.get("material"),
        "pattern": data.get("pattern"),
        "color": first.get("color"),
        "audience": data.get("audience", {}).get("suggestedGender"),
        "price": offer.get("price"),
        "priceCurrency": offer.get("priceCurrency"),
        "url": offer.get("url"),
        "image": first.get("image"),
    }


async def main():
    init_db()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pl-PL",
            timezone_id="Europe/Warsaw",
            extra_http_headers={
                "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
        )

        await context.add_init_script(STEALTH_INIT_SCRIPT)
        page = await context.new_page()

        products = get_tracked_products_for_scraping()
        if not products:
            print("Brak produktów do zescrapowania.")
            await browser.close()
            return

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
