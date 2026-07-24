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

class BuyConfirmView(discord.ui.View):
    def __init__(self, user_id: int, item_key: str, item_disp: str, quantity: int, unit_price: int, total_price: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_key = item_key
        self.item_disp = item_disp
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = total_price

    @discord.ui.button(label="Confirm Purchase", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot confirm this purchase!", ephemeral=True)
            return

        curr_gems = get_user_gems(self.user_id)
        if curr_gems < self.total_price:
            await interaction.response.send_message(
                f"Coo coo! ⚠️ You no longer have enough Gems! Needed: **{self.total_price:,} 💎**, Current: **{curr_gems:,} 💎**.",
                ephemeral=True
            )
            return

        add_user_gems(self.user_id, -self.total_price)

        if self.item_key == "premium":
            new_until = add_user_premium(self.user_id, 30 * self.quantity)
            rem_days = max(1, (new_until - int(time.time())) // 86400)
            desc = (
                f"🎉 **{interaction.user.mention}** confirmed and purchased **{self.quantity}x 👑 Premium Pass** for **{self.total_price:,} 💎 Gems**!\n\n"
                f"⚡ **Drop Cooldown:** Halved to **7.5 Minutes**!\n"
                f"⚡ **Grab Cooldown:** Halved to **2.5 Minutes**!\n"
                f"👑 **Status:** Active for **{rem_days} Days**!\n\n"
                f"💎 **Remaining Balance:** **{curr_gems - self.total_price:,} Gems 💎**"
            )
            color = discord.Color.gold()
        elif self.item_key == "drop":
            new_t = add_user_drop_tickets(self.user_id, self.quantity)
            desc = (
                f"🎉 **{interaction.user.mention}** confirmed and purchased **{self.quantity}x Extra Drop Ticket(s)** for **{self.total_price:,} 💎 Gems**!\n\n"
                f"🎟️ **Total Drop Tickets:** **{new_t} Tickets 🎟️**\n"
                f"💎 **Remaining Balance:** **{curr_gems - self.total_price:,} Gems 💎**"
            )
            color = discord.Color.blue()
        elif self.item_key == "grab":
            new_t = add_user_grab_tickets(self.user_id, self.quantity)
            desc = (
                f"🎉 **{interaction.user.mention}** confirmed and purchased **{self.quantity}x Extra Grab Ticket(s)** for **{self.total_price:,} 💎 Gems**!\n\n"
                f"🖐️ **Total Grab Tickets:** **{new_t} Tickets 🖐️**\n"
                f"💎 **Remaining Balance:** **{curr_gems - self.total_price:,} Gems 💎**"
            )
            color = discord.Color.blue()
        elif self.item_key == "dust":
            gained = 250 * self.quantity
            new_d = add_user_dust(self.user_id, gained)
            desc = (
                f"🎉 **{interaction.user.mention}** confirmed and purchased **{self.quantity}x Dust Pouch(es)** for **{self.total_price:,} 💎 Gems**!\n\n"
                f"🧪 **Gained Dust:** **+{gained:,} 🧪 Dust**\n"
                f"🧪 **New Dust Balance:** **{new_d:,} Dust 🧪**\n"
                f"💎 **Remaining Balance:** **{curr_gems - self.total_price:,} Gems 💎**"
            )
            color = discord.Color.purple()

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title=f"🛍️ Purchase Confirmed: {self.item_disp}",
            description=desc,
            color=color
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot cancel this purchase!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="❌ Purchase Cancelled",
            description=f"Transaction cancelled. No Gems were deducted from your balance.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

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

        embed.set_footer(text="Type !buy <item> <quantity> or click a button below to purchase!")

        view = ShopView(user.id)

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

    async def process_buy_item(self, ctx_or_interaction, item_name: str, quantity: int = 1):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        if quantity < 1:
            quantity = 1

        item_clean = item_name.lower().strip()
        curr_gems = get_user_gems(user.id)

        if item_clean in ["premium", "pass", "p", "prem"]:
            item_key = "premium"
            item_disp = "👑 30-Day Premium Pass"
            unit_price = 2500
        elif item_clean in ["drop", "dropticket", "d", "droptickets", "drops"]:
            item_key = "drop"
            item_disp = "🎟️ Extra Drop Ticket"
            unit_price = 100
        elif item_clean in ["grab", "grabticket", "g", "grabtickets", "grabs"]:
            item_key = "grab"
            item_disp = "🖐️ Extra Grab Ticket"
            unit_price = 100
        elif item_clean in ["dust", "dustpouch", "dp", "pouches"]:
            item_key = "dust"
            item_disp = "🧪 Dust Pouch (+250 Dust)"
            unit_price = 1000
        else:
            msg = (
                f"Coo coo! ⚠️ Unknown item `{item_name}`!\n"
                f"**Available Shop Items:**\n"
                f"• `!buy premium` (2,500 💎)\n"
                f"• `!buy drop <qty>` (100 💎 each)\n"
                f"• `!buy grab <qty>` (100 💎 each)\n"
                f"• `!buy dust <qty>` (1,000 💎 each)"
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        total_price = unit_price * quantity
        if curr_gems < total_price:
            msg = f"Coo coo! ⚠️ You need **{total_price:,} 💎 Gems** to buy **{quantity}x {item_disp}**! You currently have **{curr_gems:,} 💎 Gems**."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        view = BuyConfirmView(user.id, item_key, item_disp, quantity, unit_price, total_price)
        embed = discord.Embed(
            title=f"🛒 Confirm Purchase: {item_disp}",
            description=(
                f"Are you sure you want to buy **{quantity}x {item_disp}** for **{total_price:,} 💎 Gems**?\n\n"
                f"💎 **Current Balance:** **{curr_gems:,} Gems**\n"
                f"💎 **Balance After Purchase:** **{curr_gems - total_price:,} Gems**\n\n"
                f"Click **Confirm Purchase** below to complete your transaction!"
            ),
            color=discord.Color.gold()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

    @app_commands.command(name="buy", description="Purchase items from Coo Coo's Shop with Gems")
    @app_commands.choices(item=[
        app_commands.Choice(name="👑 30-Day Premium Pass (2,500 💎)", value="premium"),
        app_commands.Choice(name="🎟️ Extra Drop Ticket (100 💎)", value="drop"),
        app_commands.Choice(name="🖐️ Extra Grab Ticket (100 💎)", value="grab"),
        app_commands.Choice(name="🧪 Dust Pouch +250 (1,000 💎)", value="dust")
    ])
    async def buy_slash(self, interaction: discord.Interaction, item: app_commands.Choice[str], quantity: int = 1):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_buy_item(interaction, item.value, quantity)

    @commands.command(name="buy")
    async def buy_prefix(self, ctx, item: str = None, quantity: int = 1):
        if not item:
            await self.process_shop(ctx)
            return
        await self.process_buy_item(ctx, item, quantity)

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
