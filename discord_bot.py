import re
import json
from pathlib import Path
import discord
from discord import app_commands
from db import init_db, add_tracked_product, remove_tracked_product, get_all_products

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
GUILD_ID = 0  # wklej ID swojego serwera Discord (liczba całkowita)

STORES_PATH = Path(__file__).parent / "stores.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=GUILD_ID)


def load_stores():
    return json.loads(STORES_PATH.read_text())


def detect_store_and_id(url: str):
    stores = load_stores()
    for store_key, cfg in stores.items():
        if cfg["hostPattern"] in url:
            pattern = re.compile(cfg["urlIdRegex"], re.IGNORECASE)
            match = pattern.search(url)
            if match:
                return store_key, match.group(1).upper(), cfg["name"]
    return None, None, None


@tree.command(name="dodaj", description="Dodaj produkt do śledzenia ceny", guild=guild)
@app_commands.describe(url="Link do produktu (H&M, Reserved, ...)")
async def dodaj(interaction: discord.Interaction, url: str):
    store_key, product_id, store_name = detect_store_and_id(url)
    if not store_key:
        await interaction.response.send_message(
            "❌ Nie rozpoznano linku. Obsługiwane sklepy: H&M, Reserved.",
            ephemeral=True,
        )
        return

    add_tracked_product(product_id, url, store_key)
    await interaction.response.send_message(
        f"✅ Produkt `{product_id}` ({store_name}) dodany do śledzenia!\nDane o cenie pojawią się po najbliższym uruchomieniu scrapera.",
        ephemeral=True,
    )


@tree.command(name="usun", description="Usuń produkt ze śledzenia ceny", guild=guild)
@app_commands.describe(product_id="ID produktu widoczne na liście")
async def usun(interaction: discord.Interaction, product_id: str):
    products = get_all_products()
    matched = [p for p in products if p["id"] == product_id.upper()]
    if not matched:
        await interaction.response.send_message(
            f"❌ Nie znaleziono produktu o ID `{product_id}`. Sprawdź listę przez `/lista`.",
            ephemeral=True,
        )
        return

    for p in matched:
        remove_tracked_product(p["id"], p["store"])
    await interaction.response.send_message(
        f"✅ Produkt `{product_id}` usunięty ze śledzenia.", ephemeral=True
    )


@tree.command(name="lista", description="Wyświetl wszystkie śledzone produkty", guild=guild)
async def lista(interaction: discord.Interaction):
    stores = load_stores()
    products = get_all_products()
    if not products:
        await interaction.response.send_message(
            "Brak śledzonych produktów. Dodaj pierwszy przez `/dodaj`.", ephemeral=True
        )
        return

    by_store = {}
    for p in products:
        by_store.setdefault(p["store"], []).append(p)

    embeds = []
    for store_key, store_products in by_store.items():
        cfg = stores.get(store_key, {})
        embed = discord.Embed(
            title=f"🏷️ Śledzone produkty — {cfg.get('name', store_key)}",
            color=cfg.get("color", 0),
        )
        for p in store_products:
            pending = p["currentPrice"] == 0
            current = "Ładowanie..." if pending else f"{p['currentPrice']:.2f} PLN"
            last = f"{p['lastPrice']:.2f} PLN" if p["lastPrice"] else "—"
            min_p = f"{p['minPrice']:.2f} PLN" if p["minPrice"] else "—"
            max_p = f"{p['maxPrice']:.2f} PLN" if p["maxPrice"] else "—"

            embed.add_field(
                name=f"`{p['id']}` — {p['name']}",
                value=(
                    f"Aktualna: **{current}** | Poprzednia: {last}\n"
                    f"Min: {min_p} | Max: {max_p}\n"
                    f"Dodano: {p['createdOn']}"
                ),
                inline=False,
            )
        embeds.append(embed)

    await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)


@client.event
async def on_ready():
    init_db()
    await tree.sync(guild=guild)
    print(f"Bot gotowy jako {client.user}")


client.run(BOT_TOKEN)
