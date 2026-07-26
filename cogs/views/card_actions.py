import discord

from config import display_rarity
from database import (
    add_user_dust, delete_card_from_inventory, get_user_dust,
    update_card_quality,
)
from utils.renderer import render_single_card


class BurnConfirmView(discord.ui.View):
    def __init__(self, owner_id: int, card_code: str, char_name: str, rarity: str, dust_reward: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.card_code = card_code
        self.char_name = char_name
        self.rarity = rarity
        self.dust_reward = dust_reward

    @discord.ui.button(label="Confirm Burn", style=discord.ButtonStyle.danger, emoji="🔥")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot confirm this burn!", ephemeral=True)
            return

        deleted = delete_card_from_inventory(self.card_code, self.owner_id)
        if not deleted:
            await interaction.response.send_message(f"Coo coo! ⚠️ Card `{self.card_code}` is no longer in your inventory!", ephemeral=True)
            return

        new_dust = add_user_dust(self.owner_id, self.dust_reward)
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title=f"🔥 Burned: {self.char_name}",
            description=(
                f"🔥 **{interaction.user.mention}** confirmed and burned `{self.card_code}` (**{self.char_name}** — {display_rarity(self.rarity)}) into ashes!\n\n"
                f"🧪 **Gained Dust:** **+{self.dust_reward} Dust** *(Total Balance: {new_dust:,} 🧪 Dust)*"
            ),
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot cancel this burn!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="❌ Burn Cancelled",
            description=f"Safe! **{self.char_name}** (`{self.card_code}`) was saved from the flames.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)

class RepairConfirmView(discord.ui.View):
    def __init__(self, owner_id: int, card_data: dict, next_quality: str, cost: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.card_data = card_data
        self.next_quality = next_quality
        self.cost = cost

    @discord.ui.button(label="Confirm Repair", style=discord.ButtonStyle.success, emoji="🛠️")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot confirm this repair!", ephemeral=True)
            return

        curr_dust = get_user_dust(self.owner_id)
        if curr_dust < self.cost:
            await interaction.response.send_message(
                f"Coo coo! ⚠️ You don't have enough Dust! Needed: **{self.cost} 🧪 Dust**, Current: **{curr_dust} 🧪 Dust**.",
                ephemeral=True
            )
            return

        add_user_dust(self.owner_id, -self.cost)
        update_card_quality(self.card_data["code"], self.owner_id, self.next_quality)

        self.card_data["quality"] = self.next_quality
        buf = await render_single_card(self.card_data)
        file = discord.File(fp=buf, filename="repaired.png")

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title=f"🛠️ Card Repaired: {self.card_data['character_name']}",
            description=(
                f"🎉 **{interaction.user.mention}** spent **{self.cost} 🧪 Dust** to repair `{self.card_data['code']}`!\n\n"
                f"🌟 **New Condition:** **{self.next_quality}**\n"
                f"🧪 **Remaining Dust:** **{curr_dust - self.cost:,} Dust 🧪**"
            ),
            color=discord.Color.green()
        )
        embed.set_image(url="attachment://repaired.png")

        await interaction.response.edit_message(embed=embed, view=self, attachments=[file])

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot cancel this repair!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="❌ Repair Cancelled",
            description=f"Transaction cancelled. No Dust was deducted.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)
