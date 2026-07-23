import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import random
import asyncio
import aiohttp
import sqlite3
import time
import traceback
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

# ==========================================
# 🗄️ SQLITE DATABASE INITIALIZATION
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        character_name TEXT NOT NULL,
        series_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        rarity TEXT NOT NULL,
        mint_number INTEGER NOT NULL,
        grabbed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mints (
        character_name TEXT PRIMARY KEY,
        current_mint INTEGER NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cooldowns (
        user_id INTEGER PRIMARY KEY,
        last_drop REAL NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

def get_next_mint(character_name: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT current_mint FROM mints WHERE character_name = ?", (character_name,))
    row = cursor.fetchone()
    if row:
        next_mint = row[0] + 1
        cursor.execute("UPDATE mints SET current_mint = ? WHERE character_name = ?", (next_mint, character_name))
    else:
        next_mint = 1
        cursor.execute("INSERT INTO mints (character_name, current_mint) VALUES (?, ?)", (character_name, next_mint))
    conn.commit()
    conn.close()
    return next_mint

def save_card_to_inventory(user_id: int, character_name: str, series_name: str, image_url: str, rarity: str, mint_number: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO inventory (user_id, character_name, series_name, image_url, rarity, mint_number)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, character_name, series_name, image_url, rarity, mint_number))
    conn.commit()
    conn.close()

def get_user_inventory(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, character_name, series_name, rarity, mint_number, image_url FROM inventory WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_user_cooldown(user_id: int) -> float:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_drop FROM cooldowns WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

def set_user_cooldown(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO cooldowns (user_id, last_drop) VALUES (?, ?)", (user_id, time.time()))
    conn.commit()
    conn.close()

# ==========================================
# 🌐 ANILIST PUBLIC API INTEGRATION
# ==========================================
ANILIST_URL = "https://graphql.anilist.co"

ANILIST_QUERY = """query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    characters(sort: FAVOURITES_DESC) {
      id
      name {
        full
      }
      image {
        large
      }
      favourites
      media(perPage: 1) {
        nodes {
          title {
            english
            romaji
          }
        }
      }
    }
  }
}"""

async def fetch_random_anilist_cards(count: int = 3):
    """Fetches random popular anime characters from AniList API."""
    random_page = random.randint(1, 35)
    variables = {"page": random_page, "perPage": 25}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": variables}, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    char_list = data["data"]["Page"]["characters"]
                    selected = random.sample(char_list, min(count, len(char_list)))
                    
                    cards = []
                    for char in selected:
                        char_name = char["name"]["full"]
                        img_url = char["image"]["large"]
                        favs = char.get("favourites", 0)
                        
                        media_nodes = char.get("media", {}).get("nodes", [])
                        if media_nodes and media_nodes[0].get("title"):
                            series = media_nodes[0]["title"].get("english") or media_nodes[0]["title"].get("romaji") or "Anime Series"
                        else:
                            series = "Anime Series"
                            
                        if favs > 10000:
                            rarity = "✨ Legendary"
                        elif favs > 3000:
                            rarity = "🟣 Epic"
                        elif favs > 800:
                            rarity = "🔷 Rare"
                        else:
                            rarity = "⚪ Common"
                            
                        cards.append({
                            "name": char_name,
                            "series": series,
                            "image": img_url,
                            "rarity": rarity
                        })
                    return cards
                else:
                    print(f"AniList API Status Error: {resp.status}")
                    return None
        except Exception as e:
            print(f"AniList Fetch Exception: {e}")
            return None

# ==========================================
# 🎨 COLOR ROLES CONFIGURATION
# ==========================================
COLOR_ROLES = [
    {"name": "Cherry Pink", "emoji": "🩷", "hex": 0xFFB6C1},
    {"name": "Lavender", "emoji": "💜", "hex": 0x9370DB},
    {"name": "Sunset Red", "emoji": "🔴", "hex": 0xE60023},
    {"name": "Mint Green", "emoji": "💚", "hex": 0x98FF98},
    {"name": "Sky Blue", "emoji": "🩵", "hex": 0x87CEEB},
    {"name": "Lemon Yellow", "emoji": "💛", "hex": 0xFFFACD},
    {"name": "Peach Coral", "emoji": "🧡", "hex": 0xFF7F50},
    {"name": "Royal Blue", "emoji": "💙", "hex": 0x007AFF},
    {"name": "Pure White", "emoji": "🤍", "hex": 0xFFFFFF},
    {"name": "Midnight", "emoji": "🖤", "hex": 0x36393F},
]

PIGEON_MESSAGES = [
    "Coo coo! 🍞 Don't let a bad sketch ruin your day. Even a dropped bagel on 5th Ave gets a second chance!",
    "Coo coo! 🎨 You don't need perfection, you just need to start. Look at me — I can't read the room, but I still show up!",
    "Coo coo! 🍟 If someone tells you your goals are too big, tell them you're just aerodynamically blessed like me!",
    "Coo coo! 🗽 Life is tough, but so is NYC sidewalk pizza. Keep chewing and keep creating!",
    "Coo coo! 🌾 Take a break, stretch your wrist, and drink water. You can't draw masterpieces on an empty stomach!",
    "Coo coo! 👔 Wear your bowtie with confidence, even when you're just hunting for breadcrumbs!",
    "Coo coo! ✨ Art block is temporary, but your talent is forever. Go make something cool!",
    "Coo coo! 🥯 They said I couldn't fly over the park bench because I was too fat. I waddled instead. Adapt and conquer!",
    "Coo coo! 💅 Never be afraid to third-wheel your own success!",
    "Coo coo! 🎨 Yuki told me every artist starts with a rough draft. Mine was a pretzel stain on the sidewalk!",
    "Coo coo! 🌟 Ratan told me to reach for the stars. I reached for a French fry instead, but the energy is the same!",
    "Coo coo! 🍕 Keep pushing forward! Every line you draw brings you closer to your dream!"
]

# ==========================================
# 🎴 CARD DROP BUTTON UI
# ==========================================
class CardGrabButton(discord.ui.Button):
    def __init__(self, index: int, card_info: dict):
        super().__init__(
            label=f"Grab Card {index + 1}",
            emoji=["1️⃣", "2️⃣", "3️⃣"][index],
            style=discord.ButtonStyle.primary,
            custom_id=f"coocoo_grab_{index}_{random.randint(10000, 99999)}"
        )
        self.index = index
        self.card_info = card_info
        self.grabbed = False

    async def callback(self, interaction: discord.Interaction):
        if self.grabbed:
            await interaction.response.send_message("Coo coo! ⚠️ This card has already been grabbed!", ephemeral=True)
            return

        self.grabbed = True
        self.disabled = True
        self.label = f"Claimed by {interaction.user.display_name}"
        self.style = discord.ButtonStyle.success

        mint_num = get_next_mint(self.card_info["name"])
        save_card_to_inventory(
            user_id=interaction.user.id,
            character_name=self.card_info["name"],
            series_name=self.card_info["series"],
            image_url=self.card_info["image"],
            rarity=self.card_info["rarity"],
            mint_number=mint_num
        )

        await interaction.response.edit_message(view=self.view)
        await interaction.followup.send(
            f"🎉 {interaction.user.mention} grabbed **{self.card_info['name']}** (Mint **#{mint_num}**) from *{self.card_info['series']}*! {self.card_info['rarity']}"
        )

class CardDropView(discord.ui.View):
    def __init__(self, cards: list):
        super().__init__(timeout=180)
        for idx, card in enumerate(cards):
            self.add_item(CardGrabButton(idx, card))

class ColorButton(discord.ui.Button):
    def __init__(self, color_info):
        super().__init__(
            label=f"{color_info['emoji']} {color_info['name']}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"coocoo_color_{color_info['name'].lower().replace(' ', '_')}"
        )
        self.color_info = color_info

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        target_role_name = self.color_info["name"]
        target_role = discord.utils.get(guild.roles, name=target_role_name)

        if not target_role:
            try:
                target_role = await guild.create_role(
                    name=target_role_name,
                    color=discord.Color(self.color_info["hex"]),
                    reason="Coo Coo Color Role Auto-Creation"
                )
            except discord.Forbidden:
                await interaction.followup.send("Coo coo! ⚠️ I don't have 'Manage Roles' permission!", ephemeral=True)
                return
        else:
            try:
                await target_role.edit(color=discord.Color(self.color_info["hex"]))
            except Exception:
                pass

        color_role_names = [c["name"] for c in COLOR_ROLES]
        roles_to_remove = [r for r in member.roles if r.name in color_role_names and r.name != target_role_name]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        if target_role not in member.roles:
            await member.add_roles(target_role)
            await interaction.followup.send(
                f"Coo coo! 🐦 {self.color_info['emoji']} Your name color is now **{target_role_name}**!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"Coo coo! 🐦 You already have **{target_role_name}**!", ephemeral=True)

class ColorPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for color in COLOR_ROLES:
            self.add_item(ColorButton(color))

# ==========================================
# 🤖 BOT DISCORD CLIENT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🐦 Coo Coo is ONLINE as {bot.user.name} ({bot.user.id})!")
    # Instant Guild Slash Command Sync for immediate appearance in Discord menus!
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} Slash Commands to guild '{guild.name}' ({guild.id})!")
        except Exception as e:
            print(f"Guild sync error for {guild.name}: {e}")

    bot.add_view(ColorPickerView())

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general") or discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        embed = discord.Embed(
            title=f"🐦 Coo Coo Welcomes {member.display_name}!",
            description=(
                f"Coo coo! 🍞 Welcome to the nest, {member.mention}!\n\n"
                f"I'm Coo Coo — New York's fattest pigeon and Yuki's friend! "
                f"Head over to `#get-roles` to pick a name color!\n\n"
                f"Here, take a fresh pretzel crust 🥨!"
            ),
            color=discord.Color.from_rgb(255, 182, 193)
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        await channel.send(embed=embed)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"❌ Slash command error: {error}")

# ==========================================
# 🎴 ANILIST CARD DROP & INVENTORY COMMANDS
# ==========================================

async def execute_card_drop(ctx_or_interaction, user):
    """Core logic to fetch cards and display drop embed."""
    user_id = user.id
    last_drop = get_user_cooldown(user_id)
    cooldown_seconds = 1800 # 30 minutes
    elapsed = time.time() - last_drop

    if elapsed < cooldown_seconds:
        remaining_mins = int((cooldown_seconds - elapsed) // 60)
        msg = f"Coo coo! ⏳ {user.mention}, you're on drop cooldown! Please wait **{remaining_mins} more minutes** before dropping cards again."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Fetch 3 random AniList cards
    cards = await fetch_random_anilist_cards(3)
    if not cards:
        msg = "Coo coo! ⚠️ Couldn't reach AniList. Please try again in a moment!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Update Cooldown
    set_user_cooldown(user_id)

    embed = discord.Embed(
        title="🎴 Coo Coo's Anime Card Drop!",
        description=f"**{user.display_name}** dropped 3 cards from AniList! Click a button below to grab one!",
        color=discord.Color.gold()
    )

    for idx, card in enumerate(cards):
        embed.add_field(
            name=f"Card {idx + 1}: {card['name']}",
            value=f"📺 **Series:** {card['series']}\n✨ **Rarity:** {card['rarity']}",
            inline=True
        )

    embed.set_thumbnail(url=cards[0]["image"])
    embed.set_footer(text="Coo Coo Card Engine • Cards expire in 3 minutes!")

    view = CardDropView(cards)

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="drop", description="Drops 3 random Anime Cards from AniList!")
async def drop_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await execute_card_drop(interaction, interaction.user)

@bot.command(name="drop")
async def drop_prefix(ctx):
    await execute_card_drop(ctx, ctx.author)

@bot.tree.command(name="inventory", description="View your collected Anime Cards")
async def inventory_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    rows = get_user_inventory(interaction.user.id)
    if not rows:
        await interaction.followup.send("Coo coo! 🎴 You haven't grabbed any cards yet! Type `/drop` to start collecting!")
        return

    embed = discord.Embed(
        title=f"🎴 {interaction.user.display_name}'s Card Collection",
        description=f"Total Cards Collected: **{len(rows)}**",
        color=discord.Color.purple()
    )

    for row in rows[:10]:
        card_id, char_name, series, rarity, mint_num, img_url = row
        embed.add_field(
            name=f"#{card_id} • {char_name} (Mint #{mint_num})",
            value=f"📺 *{series}* | {rarity}",
            inline=False
        )

    if len(rows) > 10:
        embed.set_footer(text=f"Showing 10 of {len(rows)} cards. Type /view-card <id> to see full artwork!")
    else:
        embed.set_footer(text="Type /view-card <id> to see full artwork!")

    await interaction.followup.send(embed=embed)

@bot.command(name="inventory")
async def inventory_prefix(ctx):
    rows = get_user_inventory(ctx.author.id)
    if not rows:
        await ctx.send("Coo coo! 🎴 You haven't grabbed any cards yet! Type `!drop` to start collecting!")
        return

    embed = discord.Embed(
        title=f"🎴 {ctx.author.display_name}'s Card Collection",
        description=f"Total Cards Collected: **{len(rows)}**",
        color=discord.Color.purple()
    )

    for row in rows[:10]:
        card_id, char_name, series, rarity, mint_num, img_url = row
        embed.add_field(
            name=f"#{card_id} • {char_name} (Mint #{mint_num})",
            value=f"📺 *{series}* | {rarity}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.tree.command(name="view-card", description="View full details and artwork of a card from your inventory")
async def view_card_slash(interaction: discord.Interaction, card_id: int):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, character_name, series_name, rarity, mint_number, image_url, grabbed_at FROM inventory WHERE id = ?", (card_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await interaction.followup.send("Coo coo! ⚠️ Card ID not found in database!")
        return

    cid, uid, char_name, series, rarity, mint_num, img_url, grabbed_at = row
    owner = bot.get_user(uid)
    owner_name = owner.display_name if owner else f"User {uid}"

    embed = discord.Embed(
        title=f"{char_name} (Mint #{mint_num})",
        description=f"📺 **Series:** {series}\n✨ **Rarity:** {rarity}\n👤 **Owner:** {owner_name}\n📅 **Grabbed:** {grabbed_at}",
        color=discord.Color.magenta()
    )
    embed.set_image(url=img_url)
    embed.set_footer(text=f"Coo Coo Card Vault • Card #{cid}")

    await interaction.followup.send(embed=embed)

# ==========================================
# 🎨 OTHER COMMANDS
# ==========================================

@bot.command(name="setup-colors")
async def setup_colors_prefix(ctx):
    embed = discord.Embed(
        title="🐦 Coo Coo's Color Nest",
        description="Pick a color below to customize your username color in the server!",
        color=discord.Color.from_rgb(138, 158, 167)
    )
    embed.set_footer(text="Coo Coo • Select your favorite vibe!")
    await ctx.send(embed=embed, view=ColorPickerView())

@bot.tree.command(name="setup-colors", description="Spawns the Coo Coo Color Selection Buttons")
async def setup_colors_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    embed = discord.Embed(
        title="🐦 Coo Coo's Color Nest",
        description="Pick a color below to customize your username color in the server!",
        color=discord.Color.from_rgb(138, 158, 167)
    )
    embed.set_footer(text="Coo Coo • Select your favorite vibe!")
    await interaction.followup.send(embed=embed, view=ColorPickerView())

@bot.command(name="coo")
async def coo_prefix(ctx):
    msg = random.choice(PIGEON_MESSAGES)
    await ctx.send(f"🐦 **Coo Coo**: {msg}")

@bot.tree.command(name="coo", description="Coo Coo shares motivational pigeon wisdom!")
async def coo_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    msg = random.choice(PIGEON_MESSAGES)
    await interaction.followup.send(f"🐦 **Coo Coo**: {msg}")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Error: Please put your Discord Bot Token in the .env file!")
    else:
        bot.run(TOKEN)
