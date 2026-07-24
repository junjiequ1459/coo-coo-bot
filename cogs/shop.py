import time
import discord
from discord.ext import commands
from discord import app_commands
from database import (
    get_user_gems, get_user_dust, add_user_gems, add_user_dust,
    is_user_premium, get_user_premium_until, add_user_premium,
    get_user_drop_tickets, add_user_drop_tickets,
    get_user_grab_tickets, add_user_grab_tickets
)

class ShopView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="Buy Premium Pass (2,500 💎)", style=discord.ButtonStyle.success, emoji="👑")
    async def buy_premium_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Coo coo! ⚠️ Open your own shop with `/shop` or `!shop`!", ephemeral=True)
            return

        price = 2500
        curr_gems = get_user_gems(self.user_id)
        if curr_gems < price:
            await interaction.response.send_message(
                f"Coo coo! ⚠️ You need **{price:,} 💎 Gems** for a 👑 Premium Pass! You currently have **{curr_gems:,} 💎 Gems**.",
                ephemeral=True
            )
            return

        add_user_gems(self.user_id, -price)
        new_until = add_user_premium(self.user_id, 30)
        rem_days = max(1, (new_until - int(time.time())) // 86400)

        embed = discord.Embed(
            title="👑 Premium Pass Activated!",
            description=(
                f"🎉 Congratulations {interaction.user.mention}!\n\n"
                f"⚡ **Drop Cooldown:** Halved to **7.5 Minutes**!\n"
                f"⚡ **Grab Cooldown:** Halved to **2.5 Minutes**!\n"
                f"👑 **Status:** Active for **{rem_days} Days**!\n\n"
                f"💎 **Remaining Balance:** **{curr_gems - price:,} Gems 💎**"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Buy Drop Ticket (100 💎)", style=discord.ButtonStyle.secondary, emoji="🎟️")
    async def buy_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Coo coo! ⚠️ Open your own shop with `/shop` or `!shop`!", ephemeral=True)
            return

        price = 100
        curr_gems = get_user_gems(self.user_id)
        if curr_gems < price:
            await interaction.response.send_message(
                f"Coo coo! ⚠️ You need **{price:,} 💎 Gems** for an 🎟️ Extra Drop Ticket! You currently have **{curr_gems:,} 💎 Gems**.",
                ephemeral=True
            )
            return

        add_user_gems(self.user_id, -price)
        new_tickets = add_user_drop_tickets(self.user_id, 1)

        embed = discord.Embed(
            title="🎟️ Extra Drop Ticket Purchased!",
            description=(
                f"🎉 {interaction.user.mention} bought an Extra Drop Ticket for **100 💎 Gems**!\n\n"
                f"🎟️ **Total Drop Tickets:** **{new_tickets} Tickets 🎟️**\n"
                f"💎 **Remaining Gems:** **{curr_gems - price:,} Gems 💎**\n\n"
                f"💡 *Use `/drop` or `!d` anytime to bypass drop cooldowns!*"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Buy Grab Ticket (100 💎)", style=discord.ButtonStyle.secondary, emoji="🖐️")
    async def buy_grab_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Coo coo! ⚠️ Open your own shop with `/shop` or `!shop`!", ephemeral=True)
            return

        price = 100
        curr_gems = get_user_gems(self.user_id)
        if curr_gems < price:
            await interaction.response.send_message(
                f"Coo coo! ⚠️ You need **{price:,} 💎 Gems** for an 🖐️ Extra Grab Ticket! You currently have **{curr_gems:,} 💎 Gems**.",
                ephemeral=True
            )
            return

        add_user_gems(self.user_id, -price)
        new_tickets = add_user_grab_tickets(self.user_id, 1)

        embed = discord.Embed(
            title="🖐️ Extra Grab Ticket Purchased!",
            description=(
                f"🎉 {interaction.user.mention} bought an Extra Grab Ticket for **100 💎 Gems**!\n\n"
                f"🖐️ **Total Grab Tickets:** **{new_tickets} Tickets 🖐️**\n"
                f"💎 **Remaining Gems:** **{curr_gems - price:,} Gems 💎**\n\n"
                f"💡 *Click any card grab button anytime to bypass grab cooldowns!*"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Buy Dust Pouch (+250 🧪)", style=discord.ButtonStyle.primary, emoji="🧪")
    async def buy_dust_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Coo coo! ⚠️ Open your own shop with `/shop` or `!shop`!", ephemeral=True)
            return

        price = 1000
        curr_gems = get_user_gems(self.user_id)
        if curr_gems < price:
            await interaction.response.send_message(
                f"Coo coo! ⚠️ You need **{price:,} 💎 Gems** for a 🧪 Dust Pouch! You currently have **{curr_gems:,} 💎 Gems**.",
                ephemeral=True
            )
            return

        add_user_gems(self.user_id, -price)
        new_dust = add_user_dust(self.user_id, 250)

        embed = discord.Embed(
            title="🧪 Dust Pouch Purchased!",
            description=(
                f"🎉 {interaction.user.mention} bought a Dust Pouch for **1,000 💎 Gems**!\n\n"
                f"🧪 **Gained:** **+250 🧪 Dust**\n"
                f"🧪 **New Dust Balance:** **{new_dust:,} Dust 🧪**\n"
                f"💎 **Remaining Gems:** **{curr_gems - price:,} Gems 💎**"
            ),
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)

class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def process_shop(self, ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        gems = get_user_gems(user.id)
        dust = get_user_dust(user.id)
        drop_t = get_user_drop_tickets(user.id)
        grab_t = get_user_grab_tickets(user.id)
        now_ts = int(time.time())

        prem_text = "⚪ Standard Member (15m Drop / 5m Grab CD)"
        if is_user_premium(user.id):
            prem_until = get_user_premium_until(user.id)
            rem_days = max(1, (prem_until - now_ts) // 86400)
            prem_text = f"👑 **PREMIUM ACTIVE** ({rem_days} days left — 7.5m Drop / 2.5m Grab CD!)"

        embed = discord.Embed(
            title="🛒 Coo Coo's Gem & Utility Shop",
            description=(
                f"Welcome to the shop, {user.mention}!\n"
                f"💎 **Your Gems Balance:** **{gems:,} Gems 💎**\n"
                f"🎟️ **Your Drop Tickets:** **{drop_t} Tickets 🎟️**\n"
                f"🖐️ **Your Grab Tickets:** **{grab_t} Tickets 🖐️**\n"
                f"🧪 **Your Dust Balance:** **{dust:,} Dust 🧪**\n"
                f"👤 **Membership:** {prem_text}\n\n"
                f"Click a button below to purchase items with your Gems!"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="👑 30-Day Premium Pass (2,500 Gems 💎)",
            value=(
                "• **Halves Drop Cooldown**: Drop cards every **7.5 minutes** (instead of 15m)!\n"
                "• **Halves Grab Cooldown**: Grab cards every **2.5 minutes** (instead of 5m)!\n"
                "• **👑 Premium Badge**: Displays on your profile, inventory, & cooldowns."
            ),
            inline=False
        )

        embed.add_field(
            name="🎟️ Extra Drop Ticket (100 Gems 💎)",
            value="• Instantly bypasses your drop cooldown for **1 instant bonus drop**!",
            inline=False
        )

        embed.add_field(
            name="🖐️ Extra Grab Ticket (100 Gems 💎)",
            value="• Instantly bypasses your grab cooldown for **1 instant bonus grab**!",
            inline=False
        )

        embed.add_field(
            name="🧪 Dust Pouch +250 (1,000 Gems 💎)",
            value="• Convert **1,000 Gems** directly into **+250 🧪 Dust** for your flask!",
            inline=False
        )

        embed.set_footer(text="Type /daily or !daily to earn 500 free Gems every day!")

        view = ShopView(user.id)

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

    @app_commands.command(name="shop", description="Open Coo Coo's Shop to buy Premium Pass and utilities with Gems")
    async def shop_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_shop(interaction)

    @commands.command(name="shop")
    async def shop_prefix(self, ctx):
        await self.process_shop(ctx)

    @commands.command(name="store")
    async def shop_prefix_store(self, ctx):
        await self.process_shop(ctx)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))
