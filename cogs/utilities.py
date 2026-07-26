import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from config import BOT_OWNER_IDS, COLOR_ROLES, LEGACY_COLOR_ROLES, PIGEON_MESSAGES, DROP_PRIORITY_SEC
from db import get_connection, release_connection
from utils.color_preview import generate_color_preview

COLOR_BUTTON_COOLDOWNS = {}  # {user_id: last_click_timestamp}
COOLDOWN_DURATION_SEC = 5  # 5-second rate limit per user

class ColorButton(discord.ui.Button):
    def __init__(self, color_info):
        btn_label = color_info.get("label", color_info["name"])
        super().__init__(
            label=btn_label,
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

        now = time.time()
        last_press = COLOR_BUTTON_COOLDOWNS.get(member.id, 0)
        remaining = COOLDOWN_DURATION_SEC - (now - last_press)

        if remaining > 0:
            await interaction.followup.send(
                f"Coo coo! ⏳ Rate limit active! Please wait **{int(remaining) + 1}s** before changing your color again!",
                ephemeral=True
            )
            return

        COLOR_BUTTON_COOLDOWNS[member.id] = now

        target_role_name = self.color_info["name"]
        target_role = discord.utils.get(guild.roles, name=target_role_name)

        if not target_role:
            try:
                target_role = await guild.create_role(
                    name=target_role_name,
                    color=discord.Color(self.color_info["hex"]),
                    hoist=True,
                    reason="Coo Coo Color Role Auto-Creation"
                )
            except discord.Forbidden:
                await interaction.followup.send("Coo coo! ⚠️ I don't have 'Manage Roles' permission!", ephemeral=True)
                return
        else:
            try:
                await target_role.edit(color=discord.Color(self.color_info["hex"]), hoist=True)
            except Exception:
                pass

        color_role_names = [c["name"] for c in COLOR_ROLES] + LEGACY_COLOR_ROLES
        roles_to_remove = [r for r in member.roles if r.name in color_role_names and r.name != target_role_name]
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove)
            except discord.Forbidden:
                pass

        if target_role not in member.roles:
            try:
                await member.add_roles(target_role)
                color_desc = self.color_info.get("color_desc", "")
                desc_str = f" ({color_desc})" if color_desc else ""
                await interaction.followup.send(
                    f"Coo coo! 🐦 Your name color is now **{target_role_name}**{desc_str}!",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "Coo coo! ⚠️ I cannot assign this role. Please ensure my **Coo Coo Bot** role is dragged **ABOVE** the color roles in Server Settings -> Roles!",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"Coo coo! ⚠️ Could not assign role: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"Coo coo! 🐦 You already have **{target_role_name}**!", ephemeral=True)

class ColorPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for color in COLOR_ROLES:
            self.add_item(ColorButton(color))

class UtilitiesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin_or_owner(self, user: discord.User | discord.Member) -> bool:
        if user.id in BOT_OWNER_IDS:
            return True
        if isinstance(user, discord.Member) and hasattr(user, "guild_permissions"):
            perms = user.guild_permissions
            if perms.administrator or perms.manage_guild or perms.manage_roles:
                return True
        return False

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcome_channels = [
            channel
            for channel in member.guild.text_channels
            if "welcome" in channel.name.casefold()
        ]
        channel = next(
            (
                candidate
                for candidate in welcome_channels
                if candidate.category is not None
                and "information" in candidate.category.name.casefold()
            ),
            welcome_channels[0] if welcome_channels else None,
        )

        if channel is None:
            print(
                f"⚠️ Could not welcome {member}: no channel containing "
                f"'welcome' was found in {member.guild.name}."
            )
            return

        embed = discord.Embed(
            title=f"Welcome, {member.display_name}!",
            color=discord.Color.from_rgb(247, 193, 64),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        member_number = member.guild.member_count or len(member.guild.members)
        embed.set_footer(
            text=f"Member #{member_number:,} • Coo Coo is happy you're here 🐦"
        )

        try:
            await channel.send(
                content=f"Welcome to Yukisfriends {member.mention}",
                embed=embed,
            )
        except discord.Forbidden:
            print(
                f"⚠️ Could not welcome {member}: missing View Channel or "
                f"Send Messages/Embed Links permission in #{channel.name}."
            )
        except discord.HTTPException as error:
            print(f"⚠️ Could not welcome {member} in #{channel.name}: {error}")

    async def send_help_menu(self, ctx_or_interaction):
        embed = discord.Embed(
            title="🐦 Coo Coo Bot — Official Command & Rule Guide",
            description="Welcome to Coo Coo! Below is a complete list of commands, shortcuts, and card mechanics.",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="⏱️ Command Cooldowns",
            value=(
                "• **`!cd`** or **`/cd`** — Check your Drop (15m), Grab (5m), and Daily (24h) timers!\n"
                "• **`🎴 Drop Cooldown`** — 15 minutes per user (7.5m with Premium!).\n"
                "• **`🖐️ Grab Cooldown`** — 5 minutes per user (2.5m with Premium!).\n"
                f"• **`🔒 Priority Window`** — Dropper has {int(DROP_PRIORITY_SEC)} seconds of exclusive grab priority."
            ),
            inline=False
        )

        embed.add_field(
            name="🎴 Card Drops & Collecting",
            value=(
                "• **`!d`** or **`!drop`** or **`/drop`** — Drops 3 random anime cards (15m CD).\n"
                f"• **`1️⃣ 2️⃣ 3️⃣ Buttons`** — Grab cards ({int(DROP_PRIORITY_SEC)}s dropper priority!).\n"
                "• **`!v`** or **`!v <id>`** or **`/view`** — View high-res card artwork.\n"
                "• **`!c`** or **`!collection`** or **`/collection`** — Open your Anime Cards binder collection.\n"
                "• **`!i`** or **`!inv`** or **`/inventory`** — Check your items, tickets, gems & bag."
            ),
            inline=False
        )

        embed.add_field(
            name="💖 Wishlist",
            value=(
                "• **`!wish <name>`** or **`/wish`** — Add a character to your wishlist (10 max).\n"
                "• **`!unwish <name>`** or **`/unwish`** — Remove a character from your wishlist.\n"
                "• **`!wl`** or **`!wishlist`** or **`/wishlist`** — View your wishlist.\n"
                "• 🔔 You'll be **pinged** when a wishlisted character drops!"
            ),
            inline=False
        )

        embed.add_field(
            name="⭐ Favorites & Profile",
            value=(
                "• **`!fav <code>`** or **`/fav`** — Add a card to your favorites (5 max, defaults to latest).\n"
                "• **`!unfav <code>`** or **`/unfav`** — Remove a card from favorites.\n"
                "• **`!favs`** or **`/favorites`** — View your favorites showcase.\n"
                "• **`!profile @user`** or **`/profile`** — View someone's favorites!"
            ),
            inline=False
        )

        embed.add_field(
            name="💎 Gems & 🛒 Shop Economy",
            value=(
                "• **`!shop`** or **`/shop`** — Open Shop to buy **👑 30-Day Premium Pass**, **🎟️ Drop Tickets**, & items!\n"
                "• **`!bal`** or **`/bal`** — Check your personal Gem balance (Private!).\n"
                "• **`!dust`** or **`/dust`** — Check your Dust flask balance.\n"
                "• **`!daily`** or **`/daily`** — Claim 500 free Gems every 24 hours!\n"
                "• **`!pay @user <amt>`** or **`/pay`** — Transfer Gems to a friend."
            ),
            inline=False
        )

        embed.add_field(
            name="🛠️ Repair, 🔥 Burning & 🏷️ Tagging",
            value=(
                "• **`!repair <id>`** or **`/repair`** — Repair & upgrade card condition using Dust 🧪!\n"
                "• **`!burn <id>`** or **`/burn`** — Burn an unwanted card for Dust (Prompts for Epic, Legendary & Mythic!).\n"
                "• **`!t <name>`** or **`!tag <id> <name>`** — Assign a folder tag to a card (Defaults to latest!).\n"
                "• **`!ut`** or **`!untag <id>`** — Remove a tag from a card (Defaults to latest!).\n"
                "• **`!vt <tag>`** or **`!viewtag <tag>`** — View all cards in a tag folder!"
            ),
            inline=False
        )

        embed.add_field(
            name="🔍 Character & Series Lookup",
            value=(
                "• **`!lu <name>`** or **`/lu`** — Lookup character details & circulation stats.\n"
                "• **`!lu <name> <#>`** — View a specific print of a character.\n"
                "• **`!slu <series>`** or **`/slu`** — Lookup all characters in an anime series."
            ),
            inline=False
        )

        embed.add_field(
            name="🤝 Card & Gems Trading",
            value=(
                "• **`!trade @user`** or **`/trade`** — Start a trade.\n"
                "• **`!ta <id>`** or **`!ta 250g`** — Add a card or Gems to trade offer.\n"
                "• **`!tr <id>`** or **`!tr gems`** — Remove a card or reset Gems.\n"
                "• **Buttons (`➕` `➖` `✅` `❌`)** — Manage trade & confirm."
            ),
            inline=False
        )

        embed.add_field(
            name="👑 Card Rarities & Burn Yields",
            value=(
                "• **`🌈 Mythic` (Rainbow Frame)** — **0.1% Drop Rate** | Burns to **+500 🧪 Dust**\n"
                "• **`✨ Legendary` (Gold Frame)** — **0.5% Drop Rate** | Burns to **+200 🧪 Dust**\n"
                "• **`🟣 Epic` (Purple Frame)** — **5% Drop Rate** | Burns to **+100 🧪 Dust**\n"
                "• **`🔷 Rare` (Cyan Frame)** — **10% Drop Rate** | Burns to **+50 🧪 Dust**\n"
                "• **`⚪ Common` (Silver Frame)** — **84.4% Drop Rate** | Burns to **+20 🧪 Dust**"
            ),
            inline=False
        )

        embed.add_field(
            name="🎨 Server Utilities & Pigeon Wisdom",
            value=(
                "• **`!setup-colors`** or **`/setup-colors`** — Custom name color menu.\n"
                "• **`!coo`** or **`/coo`** — Pigeon wisdom from NYC sidewalk!"
            ),
            inline=False
        )

        embed.set_footer(text="Coo Coo Bot • Anime Card, Tagging & Dusting Engine")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="help", description="Displays Coo Coo's official command and rules guide")
    async def help_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.send_help_menu(interaction)

    @commands.command(name="help")
    async def help_prefix(self, ctx):
        await self.send_help_menu(ctx)

    @commands.command(name="h")
    async def help_prefix_h(self, ctx):
        await self.send_help_menu(ctx)

    @commands.command(name="setup-colors")
    async def setup_colors_prefix(self, ctx):
        if not self.is_admin_or_owner(ctx.author):
            await ctx.send("Coo coo! ⚠️ Only Server Administrators can spawn the color setup menu!")
            return
        if not os.path.exists("color_preview.png"):
            generate_color_preview("color_preview.png")
        file = discord.File("color_preview.png", filename="color_preview.png")
        embed = discord.Embed(
            title="🐦 Coo Coo's Color Nest",
            description="Pick a character color below to customize your username color in the server!",
            color=discord.Color.from_rgb(138, 158, 167)
        )
        embed.set_image(url="attachment://color_preview.png")
        embed.set_footer(text="Coo Coo • Select your favorite vibe!")
        await ctx.send(embed=embed, file=file, view=ColorPickerView())

    @app_commands.command(name="setup-colors", description="Spawns the Coo Coo Color Selection Buttons (Admin Only)")
    @app_commands.default_permissions(administrator=True)
    async def setup_colors_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        if not self.is_admin_or_owner(interaction.user):
            await interaction.followup.send("Coo coo! ⚠️ Only Server Administrators can spawn the color setup menu!", ephemeral=True)
            return
        if not os.path.exists("color_preview.png"):
            generate_color_preview("color_preview.png")
        file = discord.File("color_preview.png", filename="color_preview.png")
        embed = discord.Embed(
            title="🐦 Coo Coo's Color Nest",
            description="Pick a character color below to customize your username color in the server!",
            color=discord.Color.from_rgb(138, 158, 167)
        )
        embed.set_image(url="attachment://color_preview.png")
        embed.set_footer(text="Coo Coo • Select your favorite vibe!")
        await interaction.followup.send(embed=embed, file=file, view=ColorPickerView())

    @commands.command(name="coo")
    async def coo_prefix(self, ctx):
        msg = random.choice(PIGEON_MESSAGES)
        await ctx.send(f"🐦 **Coo Coo**: {msg}")

    @app_commands.command(name="coo", description="Coo Coo shares motivational pigeon wisdom!")
    async def coo_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        msg = random.choice(PIGEON_MESSAGES)
        await interaction.followup.send(f"🐦 **Coo Coo**: {msg}")

    @app_commands.command(name="users", description="[Owner Only] View all registered users and their balances in the database")
    @app_commands.default_permissions(administrator=True)
    async def users_slash(self, interaction: discord.Interaction):
        from config import BOT_OWNER_IDS
        if interaction.user.id not in BOT_OWNER_IDS:
            await interaction.response.send_message("Coo coo! ⚠️ This command is restricted to the Bot Owner!", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        import time
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT u.user_id, u.gems, u.dust, u.premium_until, (SELECT COUNT(*) FROM inventory i WHERE i.user_id = u.user_id) FROM users u")
        rows = cursor.fetchall()
        release_connection(conn)

        if not rows:
            await interaction.followup.send("Coo coo! 📭 No users found in the database yet!", ephemeral=True)
            return

        embed = discord.Embed(
            title="👥 Database Users Overview",
            description=f"Total Registered Users: **{len(rows)}**",
            color=discord.Color.blue()
        )

        for row in rows[:15]:
            uid, gems, dust, prem_until, card_count = row
            user_obj = self.bot.get_user(uid)
            uname = user_obj.display_name if user_obj else f"User ID: {uid}"
            is_prem = "👑 Premium" if int(time.time()) < (prem_until or 0) else "⚪ Standard"
            embed.add_field(
                name=f"👤 {uname}",
                value=f"💎 **{gems:,} Gems** | 🧪 **{dust:,} Dust** | 🎴 **{card_count} Cards** | {is_prem}",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.command(name="users")
    async def users_prefix(self, ctx):
        from config import BOT_OWNER_IDS
        if ctx.author.id not in BOT_OWNER_IDS:
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return

        import time
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT u.user_id, u.gems, u.dust, u.premium_until, (SELECT COUNT(*) FROM inventory i WHERE i.user_id = u.user_id) FROM users u")
        rows = cursor.fetchall()
        release_connection(conn)

        if not rows:
            await ctx.send("Coo coo! 📭 No users found in the database yet!")
            return

        embed = discord.Embed(
            title="👥 Database Users Overview",
            description=f"Total Registered Users: **{len(rows)}**",
            color=discord.Color.blue()
        )

        for row in rows[:15]:
            uid, gems, dust, prem_until, card_count = row
            user_obj = self.bot.get_user(uid)
            uname = user_obj.display_name if user_obj else f"User ID: {uid}"
            is_prem = "👑 Premium" if int(time.time()) < (prem_until or 0) else "⚪ Standard"
            embed.add_field(
                name=f"👤 {uname}",
                value=f"💎 **{gems:,} Gems** | 🧪 **{dust:,} Dust** | 🎴 **{card_count} Cards** | {is_prem}",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilitiesCog(bot))
