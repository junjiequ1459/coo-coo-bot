import time
from db import get_connection, release_connection
import discord
from discord.ext import commands
from discord import app_commands
from config import BURN_REWARDS
from database import (
    get_card_by_code_and_owner, update_card_tag,
    delete_card_from_inventory, get_user_dust, add_user_dust,
    update_card_quality, get_user_inventory
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
                f"🔥 **{interaction.user.mention}** confirmed and burned `{self.card_code}` (**{self.char_name}** — {self.rarity}) into ashes!\n\n"
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

class CardActionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def process_burn_card(self, ctx_or_interaction, card_code: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        if card_code:
            card_row = get_card_by_code_and_owner(card_code, user.id)
        else:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, tag, quality FROM inventory WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            release_connection(conn)
            card_row = row

        if not card_row:
            msg = "Coo coo! ⚠️ No card found to burn!" if not card_code else f"Coo coo! ⚠️ Card `{card_code}` not found in your inventory!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        if len(card_row) >= 10:
            cid, code, uid, char_name, series, rarity, mint_num, edition, tag, q_val = card_row[:10]
        else:
            cid, code, uid, char_name, series, rarity, mint_num, edition, tag = card_row[:9]
            q_val = "Good ⭐⭐"

        code_str = code if code else f"c{cid:04d}"
        base_dust = BURN_REWARDS.get(rarity, {"dust": 20})["dust"]

        q_clean = (q_val or "").lower()
        if "mint" in q_clean:
            mult = 2.0
        elif "excellent" in q_clean:
            mult = 1.5
        elif "poor" in q_clean:
            mult = 0.75
        elif "damaged" in q_clean:
            mult = 0.5
        else:
            mult = 1.0

        final_dust = max(1, int(base_dust * mult))

        if rarity in ["🟣 Epic", "✨ Legendary"]:
            view = BurnConfirmView(user.id, code_str, char_name, rarity, final_dust)
            embed = discord.Embed(
                title=f"⚠️ Are you sure you want to burn this {rarity} card?",
                description=(
                    f"🔥 You are about to burn **{char_name}** (`{code_str}`) — **{rarity}** ({q_val})!\n"
                    f"🧪 **Yield:** **+{final_dust} Dust** *(Quality Multiplier: x{mult})*\n\n"
                    f"⚠️ *This action is permanent and cannot be undone! Click below to confirm.*"
                ),
                color=discord.Color.dark_orange()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed, view=view)
            else:
                await ctx_or_interaction.send(embed=embed, view=view)
            return

        deleted = delete_card_from_inventory(code_str, user.id)
        if not deleted:
            msg = f"Coo coo! ⚠️ Error burning card `{code_str}`!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        new_dust = add_user_dust(user.id, final_dust)
        embed = discord.Embed(
            title=f"🔥 Burned: {char_name}",
            description=(
                f"🔥 **{user.mention}** burned `{code_str}` (**{char_name}** — {rarity} • {q_val}) into ashes!\n\n"
                f"🧪 **Gained Dust:** **+{final_dust} Dust** *(Total Balance: {new_dust:,} 🧪 Dust)*"
            ),
            color=discord.Color.red()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_tag_card(self, ctx_or_interaction, arg1: str = None, arg2: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        if not arg1 and not arg2:
            msg = "Coo coo! ⚠️ Usage: `!tag <tag_name>` (tags latest card) or `!tag <card_id> <tag_name>`"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        card_code = None
        tag_name = None

        if arg2 is None:
            tag_name = arg1.strip()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, character_name FROM inventory WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            release_connection(conn)

            if not row:
                msg = "Coo coo! ⚠️ You don't have any cards in your inventory yet!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(msg)
                return

            cid, code, char_name = row
            card_code = code if code else f"c{cid:04d}"
        else:
            potential_code = arg1.strip()
            potential_tag = arg2.strip()
            
            card_row = get_card_by_code_and_owner(potential_code, user.id)
            if card_row:
                card_code = potential_code
                tag_name = potential_tag
            else:
                tag_name = f"{potential_code} {potential_tag}".strip()
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, code, character_name FROM inventory WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user.id,))
                row = cursor.fetchone()
                release_connection(conn)

                if not row:
                    msg = "Coo coo! ⚠️ You don't have any cards in your inventory yet!"
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(msg, ephemeral=True)
                    else:
                        await ctx_or_interaction.send(msg)
                    return

                cid, code, char_name = row
                card_code = code if code else f"c{cid:04d}"

        success = update_card_tag(card_code, user.id, tag_name)
        if success:
            card_row = get_card_by_code_and_owner(card_code, user.id)
            char_disp = f" (**{card_row[3]}**)" if card_row else ""
            embed = discord.Embed(
                title="🏷️ Card Tagged!",
                description=f"Successfully assigned tag **`[{tag_name}]`** to card `{card_code.lower()}`{char_disp}!",
                color=discord.Color.blue()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
        else:
            msg = f"Coo coo! ⚠️ Card `{card_code}` not found in your inventory!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)

    async def process_untag_card(self, ctx_or_interaction, code: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        if not code:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, character_name FROM inventory WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            release_connection(conn)

            if not row:
                msg = "Coo coo! ⚠️ You don't have any cards in your inventory yet!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(msg)
                return

            cid, ccode, char_name = row
            card_code = ccode if ccode else f"c{cid:04d}"
        else:
            card_code = code

        success = update_card_tag(card_code, user.id, None)

        if success:
            embed = discord.Embed(
                title="🏷️ Card Untagged!",
                description=f"Removed tag from card `{card_code.lower()}`!",
                color=discord.Color.dark_grey()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
        else:
            msg = f"Coo coo! ⚠️ Card `{card_code}` not found in your inventory!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)

    async def process_repair_card(self, ctx_or_interaction, card_code_query: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        card_row = get_card_by_code_and_owner(card_code_query if card_code_query else "", user.id) if card_code_query else None
        if not card_row:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality FROM inventory WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            release_connection(conn)

            if row:
                cid, ccode, uid, char_name, series, rarity, mint_num, edition, img_url, tag_val, q_val = row
                card_row = (cid, ccode, uid, char_name, series, rarity, mint_num, edition, tag_val, q_val, img_url)

        if not card_row:
            msg = "Coo coo! ⚠️ No card found to repair!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        cid, code, uid, char_name, series, rarity, mint_num, edition, tag, q_val = card_row[:10]
        code_str = code if code else f"c{cid:04d}"
        q_curr = (q_val or "Good ⭐⭐").strip()

        # Fetch image URL if needed
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT image_url FROM inventory WHERE (code = %s OR CAST(id AS TEXT) = %s) AND user_id = %s", (code_str.lower(), code_str, user.id))
        img_row = cursor.fetchone()
        release_connection(conn)
        img_url = img_row[0] if img_row else ""

        q_clean = q_curr.lower()
        if "mint" in q_clean or "⭐⭐⭐⭐" in q_clean:
            msg = f"Coo coo! ✨ **{char_name}** (`{code_str}`) is already in pristine **Mint ⭐⭐⭐⭐** condition! No repairs needed!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        next_quality = "Mint ⭐⭐⭐⭐"
        cost = 1000
        if "damaged" in q_clean or "❌" in q_clean:
            next_quality = "Poor ⭐"
            cost = 500
        elif "poor" in q_clean or "⭐" in q_clean:
            next_quality = "Good ⭐⭐"
            cost = 1000
        elif "good" in q_clean or "⭐⭐" in q_clean:
            next_quality = "Excellent ⭐⭐⭐"
            cost = 2000
        elif "excellent" in q_clean or "⭐⭐⭐" in q_clean:
            next_quality = "Mint ⭐⭐⭐⭐"
            cost = 5000

        user_dust = get_user_dust(user.id)
        if user_dust < cost:
            msg = f"Coo coo! ⚠️ You need **{cost} 🧪 Dust** to repair **{char_name}** to **{next_quality}**! You currently have **{user_dust} 🧪 Dust**."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        card_data = {
            "id": cid,
            "code": code_str,
            "character_name": char_name,
            "series_name": series,
            "rarity": rarity,
            "mint_number": mint_num,
            "edition": edition or 1,
            "quality": q_curr,
            "image_url": img_url
        }

        view = RepairConfirmView(user.id, card_data, next_quality, cost)
        embed = discord.Embed(
            title=f"🛠️ Confirm Repair: {char_name}",
            description=(
                f"Are you sure you want to repair **{char_name}** (`{code_str}`)?\n\n"
                f"🌟 **Current Quality:** {q_curr}\n"
                f"✨ **Target Quality:** **{next_quality}**\n"
                f"🧪 **Repair Cost:** **{cost} 🧪 Dust**\n"
                f"🧪 **Your Dust Balance:** **{user_dust:,} Dust 🧪**\n\n"
                f"Click **Confirm Repair** below to upgrade your card!"
            ),
            color=discord.Color.gold()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

    @app_commands.command(name="burn", description="Burn an unwanted card to convert it into Dust (Defaults to latest card)")
    async def burn_slash(self, interaction: discord.Interaction, code: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_burn_card(interaction, code)

    @commands.command(name="burn")
    async def burn_prefix(self, ctx, code: str = None):
        await self.process_burn_card(ctx, code)

    @app_commands.command(name="tag", description="Assign a custom folder tag to a card (Defaults to latest card if code omitted)")
    async def tag_slash(self, interaction: discord.Interaction, tag: str, code: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        if code:
            await self.process_tag_card(interaction, code, tag)
        else:
            await self.process_tag_card(interaction, tag, None)

    @commands.command(name="tag")
    async def tag_prefix(self, ctx, arg1: str = None, *, arg2: str = None):
        await self.process_tag_card(ctx, arg1, arg2)

    @commands.command(name="t")
    async def tag_prefix_t(self, ctx, arg1: str = None, *, arg2: str = None):
        await self.process_tag_card(ctx, arg1, arg2)

    @app_commands.command(name="untag", description="Remove a folder tag from a card (Defaults to latest card)")
    async def untag_slash(self, interaction: discord.Interaction, code: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_untag_card(interaction, code)

    @commands.command(name="untag")
    async def untag_prefix(self, ctx, code: str = None):
        await self.process_untag_card(ctx, code)

    @commands.command(name="ut")
    async def untag_prefix_ut(self, ctx, code: str = None):
        await self.process_untag_card(ctx, code)

    @app_commands.command(name="vt", description="View all cards in a specific tag folder")
    async def vt_slash(self, interaction: discord.Interaction, tag: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        inv_cog = self.bot.get_cog('InventoryCog')
        if inv_cog:
            await inv_cog.process_inventory(interaction, tag)

    @app_commands.command(name="viewtag", description="View all cards in a specific tag folder")
    async def viewtag_slash(self, interaction: discord.Interaction, tag: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        inv_cog = self.bot.get_cog('InventoryCog')
        if inv_cog:
            await inv_cog.process_inventory(interaction, tag)

    @commands.command(name="vt")
    async def view_tag_prefix_vt(self, ctx, *, tag: str):
        inv_cog = self.bot.get_cog('InventoryCog')
        if inv_cog:
            await inv_cog.process_inventory(ctx, tag)

    @commands.command(name="viewtag")
    async def view_tag_prefix_viewtag(self, ctx, *, tag: str):
        inv_cog = self.bot.get_cog('InventoryCog')
        if inv_cog:
            await inv_cog.process_inventory(ctx, tag)

    @app_commands.command(name="repair", description="Repair and upgrade a card's condition using Dust (Defaults to latest card)")
    async def repair_slash(self, interaction: discord.Interaction, code: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_repair_card(interaction, code)

    @commands.command(name="repair")
    async def repair_prefix(self, ctx, code: str = None):
        await self.process_repair_card(ctx, code)

    @commands.command(name="rep")
    async def repair_prefix_rep(self, ctx, code: str = None):
        await self.process_repair_card(ctx, code)

    @commands.command(name="fix")
    async def repair_prefix_fix(self, ctx, code: str = None):
        await self.process_repair_card(ctx, code)

async def setup(bot):
    await bot.add_cog(CardActionsCog(bot))
