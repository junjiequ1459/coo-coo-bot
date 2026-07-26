import time

import discord

from database import (
    add_user_drop_tickets, add_user_dust, add_user_gems,
    add_user_grab_tickets, add_user_premium, get_user_gems,
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

    @discord.ui.button(label="Buy Dust Pouch (+2,000 🧪)", style=discord.ButtonStyle.primary, emoji="🧪")
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
        new_dust = add_user_dust(self.user_id, 2000)

        embed = discord.Embed(
            title="🧪 Dust Pouch Purchased!",
            description=(
                f"🎉 {interaction.user.mention} bought a Dust Pouch for **1,000 💎 Gems**!\n\n"
                f"🧪 **Gained:** **+2,000 🧪 Dust**\n"
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
            gained = 2000 * self.quantity
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
