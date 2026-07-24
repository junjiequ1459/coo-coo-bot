import time
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from config import BOT_OWNER_IDS, DB_PATH
from database import (
    add_user_gems, add_user_dust, add_user_drop_tickets, add_user_grab_tickets,
    add_user_premium, save_card_to_inventory, generate_card_code, get_next_mint
)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_owner(self, user_id: int) -> bool:
        return user_id in BOT_OWNER_IDS

    async def resolve_target_and_value(self, ctx, args: tuple):
        """Intelligently resolves target user and value from flexible command input arguments."""
        target = ctx.author
        val_parts = []

        for arg in args:
            clean_arg = str(arg).strip("<@!>")
            if clean_arg.isdigit() and len(clean_arg) >= 17:
                try:
                    fetched = self.bot.get_user(int(clean_arg)) or await self.bot.fetch_user(int(clean_arg))
                    if fetched:
                        target = fetched
                        continue
                except Exception:
                    pass
            val_parts.append(str(arg))

        val_str = " ".join(val_parts).strip()
        return target, val_str

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

    # --- UNIFIED PREFIX COMMAND GROUP ---
    @commands.group(name="give", invoke_without_command=True)
    async def give_group(self, ctx, *args):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return

        if not args:
            embed = discord.Embed(
                title="👑 Admin Grant Controls",
                description=(
                    "**Usage Examples (Targeting @user or yourself):**\n"
                    "• `!give gems 5000` or `!give gems @user 5000` — Grant Gems 💎\n"
                    "• `!give dust 1000` or `!give dust @user 1000` — Grant Dust 🧪\n"
                    "• `!give drop 5` or `!give drop @user 5` — Grant Drop Tickets 🎟️\n"
                    "• `!give grab 5` or `!give grab @user 5` — Grant Grab Tickets 🖐️\n"
                    "• `!give premium 30` or `!give premium @user 30` — Grant Premium Pass 👑\n"
                    "• `!give card Gojo` or `!give card @user Gojo` — Spawn Card 🎴"
                ),
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)

    @give_group.command(name="gems")
    async def give_gems_sub(self, ctx, *args):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        target, val_str = await self.resolve_target_and_value(ctx, args)
        amount = int(val_str) if val_str and val_str.isdigit() else 1000
        await self.grant_gems(ctx, target, amount)

    @give_group.command(name="dust")
    async def give_dust_sub(self, ctx, *args):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        target, val_str = await self.resolve_target_and_value(ctx, args)
        amount = int(val_str) if val_str and val_str.isdigit() else 500
        await self.grant_dust(ctx, target, amount)

    @give_group.command(name="drop")
    async def give_drop_sub(self, ctx, *args):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        target, val_str = await self.resolve_target_and_value(ctx, args)
        amount = int(val_str) if val_str and val_str.isdigit() else 1
        await self.grant_drop_tickets(ctx, target, amount)

    @give_group.command(name="grab")
    async def give_grab_sub(self, ctx, *args):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        target, val_str = await self.resolve_target_and_value(ctx, args)
        amount = int(val_str) if val_str and val_str.isdigit() else 1
        await self.grant_grab_tickets(ctx, target, amount)

    @give_group.command(name="premium")
    async def give_premium_sub(self, ctx, *args):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        target, val_str = await self.resolve_target_and_value(ctx, args)
        days = int(val_str) if val_str and val_str.isdigit() else 30
        await self.grant_premium(ctx, target, days)

    @give_group.command(name="card")
    async def give_card_sub(self, ctx, *args):
        if not self.is_owner(ctx.author.id):
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        target, char_query = await self.resolve_target_and_value(ctx, args)
        if not char_query:
            await ctx.send("Coo coo! ⚠️ Please specify a character name! e.g. `!give card Gojo`")
            return
        await self.grant_card(ctx, target, char_query)

    # --- UNIFIED SLASH COMMAND ---
    @app_commands.command(name="give", description="[Owner Only] Grant Gems, Dust, Tickets, Premium, or Cards to any user")
    @app_commands.choices(item=[
        app_commands.Choice(name="💎 Gems", value="gems"),
        app_commands.Choice(name="🧪 Dust", value="dust"),
        app_commands.Choice(name="🎟️ Drop Ticket", value="drop"),
        app_commands.Choice(name="🖐️ Grab Ticket", value="grab"),
        app_commands.Choice(name="👑 Premium Pass (30 Days)", value="premium"),
        app_commands.Choice(name="🎴 Card Spawner", value="card")
    ])
    async def give_slash(self, interaction: discord.Interaction, item: app_commands.Choice[str], value: str, target: discord.User = None):
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("Coo coo! ⚠️ This command is restricted to the Bot Owner!", ephemeral=True)
            return

        try:
            await interaction.response.defer()
        except Exception:
            pass

        dest = target or interaction.user
        choice = item.value
        if choice == "gems":
            amount = int(value) if value.isdigit() else 1000
            await self.grant_gems(interaction, dest, amount)
        elif choice == "dust":
            amount = int(value) if value.isdigit() else 500
            await self.grant_dust(interaction, dest, amount)
        elif choice == "drop":
            amount = int(value) if value.isdigit() else 1
            await self.grant_drop_tickets(interaction, dest, amount)
        elif choice == "grab":
            amount = int(value) if value.isdigit() else 1
            await self.grant_grab_tickets(interaction, dest, amount)
        elif choice == "premium":
            days = int(value) if value.isdigit() else 30
            await self.grant_premium(interaction, dest, days)
        elif choice == "card":
            await self.grant_card(interaction, dest, value)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
