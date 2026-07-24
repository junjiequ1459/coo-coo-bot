import random
import discord
from discord.ext import commands
from discord import app_commands
from config import COLOR_ROLES, PIGEON_MESSAGES

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

class UtilitiesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = discord.utils.get(member.guild.text_channels, name="general") or discord.utils.get(member.guild.text_channels, name="welcome")
        if channel:
            embed = discord.Embed(
                title=f"🐦 Coo Coo Welcomes {member.display_name}!",
                description=(
                    f"Coo coo! 🍞 Welcome to the nest, {member.mention}!\n\n"
                    f"I'm Coo Coo — New York's fattest pigeon and Yuki's friend! "
                    f"Head over to `#get-roles` to pick a name color!\n\n"
                    f"Here, take a fresh pretzel crust 🥨 and type `!daily` to claim your first **500 Gems 💎**!"
                ),
                color=discord.Color.from_rgb(255, 182, 193)
            )
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            await channel.send(embed=embed)

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
                "• **`🔒 Priority Window`** — Dropper has 30 seconds of exclusive grab priority."
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
            name="🔥 Burning & 🏷️ Tagging",
            value=(
                "• **`!burn <id>`** or **`/burn`** — Burn an unwanted card for Dust (Prompts for Epic+!).\n"
                "• **`!tag <name>`** or **`!tag <id> <name>`** — Assign a folder tag to a card (Defaults to latest!).\n"
                "• **`!untag`** or **`!untag <id>`** — Remove a tag from a card (Defaults to latest!).\n"
                "• **`!viewtag <tag>`** or **`!vt <tag>`** or **`!inv <tag>`** — View all cards in a tag folder!"
            ),
            inline=False
        )

        embed.add_field(
            name="🎴 Card Drops & Collecting",
            value=(
                "• **`!d`** or **`!drop`** or **`/drop`** — Drops 3 random anime cards (15m CD).\n"
                "• **`1️⃣ 2️⃣ 3️⃣ Buttons`** — Grab cards (30s dropper priority!).\n"
                "• **`!v`** or **`!v <id>`** or **`/card`** — View high-res card artwork.\n"
                "• **`!c`** or **`!collection`** or **`/collection`** — Open your Anime Cards binder collection.\n"
                "• **`!i`** or **`!inventory`** or **`/inventory`** — Check your items, tickets, gems & bag."
            ),
            inline=False
        )

        embed.add_field(
            name="🤝 Card & Gems Trading",
            value=(
                "• **`!t @user`** or **`!trade @user`** or **`/trade`** — Start a trade.\n"
                "• **`!ta <id>`** or **`!ta 250g`** — Add a card or Gems to trade offer.\n"
                "• **`!tr <id>`** or **`!tr gems`** — Remove a card or reset Gems.\n"
                "• **Buttons (`➕` `➖` `✅` `❌`)** — Manage trade & confirm."
            ),
            inline=False
        )

        embed.add_field(
            name="👑 Card Rarities & Burn Yields",
            value=(
                "• **`✨ Legendary` (Gold Frame)** — **1% Drop Rate** | Burns to **+200 🧪 Dust**\n"
                "• **`🟣 Epic` (Purple Frame)** — **8% Drop Rate** | Burns to **+100 🧪 Dust**\n"
                "• **`🔷 Rare` (Cyan Frame)** — **15% Drop Rate** | Burns to **+50 🧪 Dust**\n"
                "• **`⚪ Common` (Silver Frame)** — **76% Drop Rate** | Burns to **+20 🧪 Dust**"
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
        embed = discord.Embed(
            title="🐦 Coo Coo's Color Nest",
            description="Pick a color below to customize your username color in the server!",
            color=discord.Color.from_rgb(138, 158, 167)
        )
        embed.set_footer(text="Coo Coo • Select your favorite vibe!")
        await ctx.send(embed=embed, view=ColorPickerView())

    @app_commands.command(name="setup-colors", description="Spawns the Coo Coo Color Selection Buttons")
    async def setup_colors_slash(self, interaction: discord.Interaction):
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
    async def users_slash(self, interaction: discord.Interaction):
        from config import BOT_OWNER_IDS, DB_PATH
        if interaction.user.id not in BOT_OWNER_IDS:
            await interaction.response.send_message("Coo coo! ⚠️ This command is restricted to the Bot Owner!", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        import sqlite3, time
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        cursor.execute("SELECT u.user_id, u.gems, u.dust, u.premium_until, (SELECT COUNT(*) FROM inventory i WHERE i.user_id = u.user_id) FROM users u")
        rows = cursor.fetchall()
        conn.close()

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
        from config import BOT_OWNER_IDS, DB_PATH
        if ctx.author.id not in BOT_OWNER_IDS:
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return

        import sqlite3, time
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        cursor.execute("SELECT u.user_id, u.gems, u.dust, u.premium_until, (SELECT COUNT(*) FROM inventory i WHERE i.user_id = u.user_id) FROM users u")
        rows = cursor.fetchall()
        conn.close()

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
