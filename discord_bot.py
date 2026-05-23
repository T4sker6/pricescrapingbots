import re
import discord
from discord import app_commands
from db import init_db, add_tracked_product, remove_tracked_product, get_all_products

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
GUILD_ID = 0  # wklej ID swojego serwera Discord (liczba całkowita)

PRODUCT_ID_RE = re.compile(r"productpage\.(\d+)\.html")
HM_RED = 0xE50010

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=GUILD_ID)


@tree.command(name="dodaj", description="Dodaj produkt H&M do śledzenia ceny", guild=guild)
@app_commands.describe(url="Link do produktu na hm.com")
async def dodaj(interaction: discord.Interaction, url: str):
    match = PRODUCT_ID_RE.search(url)
    if not match:
        await interaction.response.send_message(
            "❌ Nie rozpoznano linku H&M. Wklej link do konkretnego produktu, np. `https://www2.hm.com/pl_pl/productpage.1338759001.html`",
            ephemeral=True,
        )
        return

    product_id = match.group(1)
    add_tracked_product(product_id, url)
    await interaction.response.send_message(
        f"✅ Produkt `{product_id}` dodany do śledzenia!\nDane o cenie pojawią się po najbliższym uruchomieniu scrapera.",
        ephemeral=True,
    )


@tree.command(name="usun", description="Usuń produkt H&M ze śledzenia ceny", guild=guild)
@app_commands.describe(product_id="ID produktu widoczne na liście (np. 1338759001)")
async def usun(interaction: discord.Interaction, product_id: str):
    removed = remove_tracked_product(product_id)
    if removed:
        await interaction.response.send_message(
            f"✅ Produkt `{product_id}` usunięty ze śledzenia.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Nie znaleziono produktu o ID `{product_id}`. Sprawdź listę przez `/lista`.",
            ephemeral=True,
        )


@tree.command(name="lista", description="Wyświetl wszystkie śledzone produkty H&M", guild=guild)
async def lista(interaction: discord.Interaction):
    products = get_all_products()
    if not products:
        await interaction.response.send_message(
            "Brak śledzonych produktów. Dodaj pierwszy przez `/dodaj`.", ephemeral=True
        )
        return

    embed = discord.Embed(title="🏷️ Śledzone produkty H&M", color=HM_RED)
    for p in products:
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

    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.event
async def on_ready():
    init_db()
    await tree.sync(guild=guild)
    print(f"Bot gotowy jako {client.user}")


client.run(BOT_TOKEN)
