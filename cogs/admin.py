import time
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from config import BOT_OWNER_IDS, DB_PATH
from database import (
    add_user_gems, add_user_dust, add_user_drop_tickets, add_user_grab_tickets,
    add_user_premium, save_card_to_inventory, generate_card_code, get_next_mint,
    get_user_gems, get_user_dust, get_user_drop_tickets, get_user_grab_tickets,
    get_user_premium_until
)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_owner(self, user_id: int) -> bool:
        return user_id in BOT_OWNER_IDS

    # --- ADMIN GRANT HELPERS ---
    async def grant_gems(self, ctx_or_interaction, target: discord.User, amount: int):
        new_val = add_user_gems(target.id, amount)
        embed = discord.Embed(
            title="👑 Admin Grant: Gems",
            description=f"Granted **+{amount:,} 💎 Gems** to {target.mention}!\n\n💎 **New Balance:** **{new_val:,} Gems**",
            color=discord.Color.gold()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def grant_dust(self, ctx_or_interaction, target: discord.User, amount: int):
        new_val = add_user_dust(target.id, amount)
        embed = discord.Embed(
            title="👑 Admin Grant: Dust",
            description=f"Granted **+{amount:,} 🧪 Dust** to {target.mention}!\n\n🧪 **New Balance:** **{new_val:,} Dust**",
            color=discord.Color.purple()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def grant_drop_tickets(self, ctx_or_interaction, target: discord.User, amount: int):
        new_val = add_user_drop_tickets(target.id, amount)
        embed = discord.Embed(
            title="👑 Admin Grant: Extra Drop Tickets",
            description=f"Granted **+{amount} 🎟️ Drop Ticket(s)** to {target.mention}!\n\n🎟️ **Total Drop Tickets:** **{new_val}**",
            color=discord.Color.blue()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def grant_grab_tickets(self, ctx_or_interaction, target: discord.User, amount: int):
        new_val = add_user_grab_tickets(target.id, amount)
        embed = discord.Embed(
            title="👑 Admin Grant: Extra Grab Tickets",
            description=f"Granted **+{amount} 🖐️ Grab Ticket(s)** to {target.mention}!\n\n🖐️ **Total Grab Tickets:** **{new_val}**",
            color=discord.Color.blue()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def grant_premium(self, ctx_or_interaction, target: discord.User, days: int = 30):
        new_until = add_user_premium(target.id, days)
        rem_days = max(1, (new_until - int(time.time())) // 86400)
        embed = discord.Embed(
            title="👑 Admin Grant: Premium Pass",
            description=f"Granted **{days} Days** of 👑 **Premium Pass** to {target.mention}!\n\n👑 **Active Until:** **{rem_days} Days Remaining**",
            color=discord.Color.gold()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def grant_card(self, ctx_or_interaction, target: discord.User, character_query: str):
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        query_str = f"%{character_query.strip().lower()}%"
        cursor.execute("SELECT character_name, series_name, image_url, rarity FROM cards_pool WHERE LOWER(character_name) LIKE ? ORDER BY favourites DESC LIMIT 1", (query_str,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            msg = f"Coo coo! ⚠️ Character matching `{character_query}` not found in master database pool!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        char_name, series, img_url, rarity = row
        mint_num = get_next_mint(char_name)
        code = generate_card_code()

        save_card_to_inventory(
            user_id=target.id,
            code=code,
            character_name=char_name,
            series_name=series,
            image_url=img_url,
            rarity=rarity,
            mint_number=mint_num,
            edition=1
        )

        embed = discord.Embed(
            title=f"👑 Admin Grant: Card Spawner",
            description=(
                f"Spawned & granted card to {target.mention}!\n\n"
                f"🎴 **{char_name}** ({rarity})\n"
                f"📺 **Series:** {series}\n"
                f"🆔 **Card ID:** `{code}` | **Print:** #{mint_num}"
            ),
            color=discord.Color.green()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    # --- PREFIX COMMANDS ---
    @commands.group(name="give", invoke_without_command=True)
    async def give_group(self, ctx):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        embed = discord.Embed(
            title="👑 Admin Grant Controls",
            description=(
                "**Usage:**\n"
                "• `!give gems @user <amount>` — Grant Gems 💎\n"
                "• `!give dust @user <amount>` — Grant Dust 🧪\n"
                "• `!give drop @user <amount>` — Grant Extra Drop Tickets 🎟️\n"
                "• `!give grab @user <amount>` — Grant Extra Grab Tickets 🖐️\n"
                "• `!give premium @user <days>` — Grant Premium Pass 👑\n"
                "• `!give card @user <character_name>` — Spawn specific Card 🎴"
            ),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @give_group.command(name="gems")
    async def give_gems_sub(self, ctx, target: discord.User, amount: int):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_gems(ctx, target, amount)

    @give_group.command(name="dust")
    async def give_dust_sub(self, ctx, target: discord.User, amount: int):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_dust(ctx, target, amount)

    @give_group.command(name="drop")
    async def give_drop_sub(self, ctx, target: discord.User, amount: int):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_drop_tickets(ctx, target, amount)

    @give_group.command(name="grab")
    async def give_grab_sub(self, ctx, target: discord.User, amount: int):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_grab_tickets(ctx, target, amount)

    @give_group.command(name="premium")
    async def give_premium_sub(self, ctx, target: discord.User, days: int = 30):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_premium(ctx, target, days)

    @give_group.command(name="card")
    async def give_card_sub(self, ctx, target: discord.User, *, character_name: str):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_card(ctx, target, character_name)

    # --- DIRECT SHORTCUT COMMANDS ---
    @commands.command(name="givedust")
    async def givedust_prefix(self, ctx, target: discord.User, amount: int):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_dust(ctx, target, amount)

    @commands.command(name="givedrop")
    async def givedrop_prefix(self, ctx, target: discord.User, amount: int):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_drop_tickets(ctx, target, amount)

    @commands.command(name="givegrab")
    async def givegrab_prefix(self, ctx, target: discord.User, amount: int):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_grab_tickets(ctx, target, amount)

    @commands.command(name="givepremium")
    async def givepremium_prefix(self, ctx, target: discord.User, days: int = 30):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_premium(ctx, target, days)

    @commands.command(name="givecard")
    async def givecard_prefix(self, ctx, target: discord.User, *, character_name: str):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.grant_card(ctx, target, character_name)

    # --- SLASH COMMAND ---
    @app_commands.command(name="give", description="[Owner Only] Grant Gems, Dust, Tickets, Premium, or Cards to any user")
    @app_commands.choices(item=[
        app_commands.Choice(name="💎 Gems", value="gems"),
        app_commands.Choice(name="🧪 Dust", value="dust"),
        app_commands.Choice(name="🎟️ Drop Ticket", value="drop"),
        app_commands.Choice(name="🖐️ Grab Ticket", value="grab"),
        app_commands.Choice(name="👑 Premium Pass (30 Days)", value="premium"),
        app_commands.Choice(name="🎴 Card Spawner", value="card")
    ])
    async def give_slash(self, interaction: discord.Interaction, item: app_commands.Choice[str], target: discord.User, value: str):
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("Coo coo! ⚠️ This command is restricted to the Bot Owner!", ephemeral=True)
            return

        try:
            await interaction.response.defer()
        except Exception:
            pass

        choice = item.value
        if choice == "gems":
            amount = int(value) if value.isdigit() else 100
            await self.grant_gems(interaction, target, amount)
        elif choice == "dust":
            amount = int(value) if value.isdigit() else 100
            await self.grant_dust(interaction, target, amount)
        elif choice == "drop":
            amount = int(value) if value.isdigit() else 1
            await self.grant_drop_tickets(interaction, target, amount)
        elif choice == "grab":
            amount = int(value) if value.isdigit() else 1
            await self.grant_grab_tickets(interaction, target, amount)
        elif choice == "premium":
            days = int(value) if value.isdigit() else 30
            await self.grant_premium(interaction, target, days)
        elif choice == "card":
            await self.grant_card(interaction, target, value)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
