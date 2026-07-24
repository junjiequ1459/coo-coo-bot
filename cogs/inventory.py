import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from config import DB_PATH, BURN_REWARDS
from database import (
    get_user_inventory, get_card_by_code_and_owner, update_card_tag,
    delete_card_from_inventory, get_user_dust, add_user_dust
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

class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def process_inventory(self, ctx_or_interaction, tag_filter: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        rows = get_user_inventory(user.id, tag_filter)

        title_suffix = f" (Tag: [{tag_filter}])" if tag_filter else ""

        if not rows:
            msg = f"Coo coo! 🎴 No cards found in your collection{title_suffix}! Type `/drop` to start collecting!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        embed = discord.Embed(
            title=f"🎴 {user.display_name}'s Card Collection{title_suffix}",
            description=f"Total Cards: **{len(rows)}**",
            color=discord.Color.purple()
        )

        for row in rows[:10]:
            card_id, code, char_name, series, rarity, mint_num, edition, img_url, tag_val = row
            code_str = code if code else f"c{card_id:04d}"
            ed_val = edition if edition else 1
            tag_disp = f" 🏷️ `[{tag_val}]`" if tag_val else ""
            embed.add_field(
                name=f"🆔 Card ID: `{code_str}` • {char_name}{tag_disp}",
                value=f"Edition {ed_val} • Print #{mint_num} | 📺 *{series}* | {rarity}",
                inline=False
            )

        if len(rows) > 10:
            embed.set_footer(text=f"Showing 10 of {len(rows)} cards. Type /card code:<code> to see full card artwork!")
        else:
            embed.set_footer(text="Type /card code:<code> to see full card artwork!")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_view_card(self, ctx_or_interaction, card_code_query: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()

        if not card_code_query:
            cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, grabbed_at FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
        else:
            query_str = card_code_query.lower().strip()
            cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, grabbed_at FROM inventory WHERE (code = ? OR id = ?) AND user_id = ?", (query_str, query_str, user.id))
            row = cursor.fetchone()

            if not row:
                cursor.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ? AND LOWER(tag) = ?", (user.id, query_str))
                tag_count = cursor.fetchone()[0]
                if tag_count > 0:
                    conn.close()
                    await self.process_inventory(ctx_or_interaction, tag_filter=query_str)
                    return

        if not row:
            conn.close()
            if not card_code_query:
                msg = "Coo coo! ⚠️ You don't have any cards in your inventory yet! Type `/drop` to grab your first card!"
            else:
                msg = f"Coo coo! ⚠️ Card ID or Tag `{card_code_query}` not found in your inventory!"
                
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        cid, code, uid, char_name, series, rarity, mint_num, edition, img_url, tag_val, grabbed_at = row
        conn.close()

        owner = self.bot.get_user(uid)
        owner_name = owner.display_name if owner else f"User {uid}"
        ed_val = edition if edition else 1
        code_str = code if code else f"c{cid:04d}"

        card_data = {
            "id": cid,
            "code": code_str,
            "character_name": char_name,
            "series_name": series,
            "rarity": rarity,
            "mint_number": mint_num,
            "edition": ed_val,
            "image_url": img_url
        }

        buf = await render_single_card(card_data)
        file = discord.File(fp=buf, filename="card.png")

        tag_disp = f"🏷️ **Tag:** `[{tag_val}]`\n" if tag_val else ""

        embed = discord.Embed(
            title=f"🆔 Card ID: {code_str} • {char_name}",
            description=(
                f"📺 **Series:** {series}\n"
                f"👤 **Owner:** {owner_name}\n"
                f"{tag_disp}"
                f"📅 **Grabbed:** {grabbed_at}"
            ),
            color=discord.Color.magenta()
        )
        embed.set_image(url="attachment://card.png")
        embed.set_footer(text=f"Coo Coo Card Vault • Card ID: {code_str}")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, file=file)
        else:
            await ctx_or_interaction.send(embed=embed, file=file)

    async def process_burn_card(self, ctx_or_interaction, card_code: str):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        card_row = get_card_by_code_and_owner(card_code, user.id)

        if not card_row:
            msg = f"Coo coo! ⚠️ Card `{card_code}` not found in your inventory!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        cid, code, uid, char_name, series, rarity, mint_num, edition, tag = card_row
        code_str = code if code else f"c{cid:04d}"
        rewards = BURN_REWARDS.get(rarity, {"dust": 20})

        if rarity in ["🟣 Epic", "✨ Legendary"]:
            view = BurnConfirmView(user.id, code_str, char_name, rarity, rewards["dust"])
            embed = discord.Embed(
                title=f"⚠️ Are you sure you want to burn this {rarity} card?",
                description=(
                    f"🔥 You are about to burn **{char_name}** (`{code_str}`) — **{rarity}**!\n"
                    f"🧪 **Yield:** **+{rewards['dust']} Dust**\n\n"
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

        new_dust = add_user_dust(user.id, rewards["dust"])
        embed = discord.Embed(
            title=f"🔥 Burned: {char_name}",
            description=(
                f"🔥 **{user.mention}** burned `{code_str}` (**{char_name}** — {rarity}) into ashes!\n\n"
                f"🧪 **Gained Dust:** **+{rewards['dust']} Dust** *(Total Balance: {new_dust:,} 🧪 Dust)*"
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
            conn = sqlite3.connect(DB_PATH, timeout=20.0)
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, character_name FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            conn.close()

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
                conn = sqlite3.connect(DB_PATH, timeout=20.0)
                cursor = conn.cursor()
                cursor.execute("SELECT id, code, character_name FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
                row = cursor.fetchone()
                conn.close()

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
            conn = sqlite3.connect(DB_PATH, timeout=20.0)
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, character_name FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            conn.close()

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

    # --- COMMAND HANDLERS ---
    @app_commands.command(name="inventory", description="View your collected Anime Cards (Optional tag filter)")
    async def inventory_slash(self, interaction: discord.Interaction, tag: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_inventory(interaction, tag)

    @commands.command(name="inventory")
    async def inventory_prefix(self, ctx, *, tag: str = None):
        await self.process_inventory(ctx, tag)

    @commands.command(name="i")
    async def inventory_prefix_i(self, ctx, *, tag: str = None):
        await self.process_inventory(ctx, tag)

    @commands.command(name="inv")
    async def inventory_prefix_inv(self, ctx, *, tag: str = None):
        await self.process_inventory(ctx, tag)

    @app_commands.command(name="card", description="View full details and artwork of a card (Defaults to your latest card)")
    async def card_slash(self, interaction: discord.Interaction, code: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_view_card(interaction, code)

    @app_commands.command(name="view", description="View full details and artwork of a card (Defaults to your latest card)")
    async def view_slash(self, interaction: discord.Interaction, code: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_view_card(interaction, code)

    @commands.command(name="v")
    async def view_card_prefix_v(self, ctx, code: str = None):
        await self.process_view_card(ctx, code)

    @commands.command(name="view")
    async def view_card_prefix_view(self, ctx, code: str = None):
        await self.process_view_card(ctx, code)

    @commands.command(name="card")
    async def view_card_prefix_card(self, ctx, code: str = None):
        await self.process_view_card(ctx, code)

    @app_commands.command(name="burn", description="Burn an unwanted card to convert it into Dust")
    async def burn_slash(self, interaction: discord.Interaction, code: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_burn_card(interaction, code)

    @commands.command(name="burn")
    async def burn_prefix(self, ctx, code: str):
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

    @app_commands.command(name="vt", description="View all cards in a specific tag folder")
    async def vt_slash(self, interaction: discord.Interaction, tag: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_inventory(interaction, tag)

    @app_commands.command(name="viewtag", description="View all cards in a specific tag folder")
    async def viewtag_slash(self, interaction: discord.Interaction, tag: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_inventory(interaction, tag)

    @commands.command(name="vt")
    async def view_tag_prefix_vt(self, ctx, *, tag: str):
        await self.process_inventory(ctx, tag)

    @commands.command(name="viewtag")
    async def view_tag_prefix_viewtag(self, ctx, *, tag: str):
        await self.process_inventory(ctx, tag)

async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
