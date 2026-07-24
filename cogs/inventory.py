import time
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from config import DB_PATH, BURN_REWARDS
from database import (
    get_user_inventory, get_card_by_code_and_owner, update_card_tag,
    delete_card_from_inventory, get_user_dust, add_user_dust,
    get_user_gems, get_user_drop_tickets, get_user_grab_tickets,
    is_user_premium, get_user_premium_until, update_card_quality
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

class CollectionPaginatorView(discord.ui.View):
    def __init__(self, user: discord.User, rows: list, tag_filter: str = None):
        super().__init__(timeout=180.0)
        self.user = user
        self.rows = rows
        self.tag_filter = tag_filter
        self.current_page = 0
        self.per_page = 10
        self.max_pages = max(1, (len(rows) + self.per_page - 1) // self.per_page)
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.max_pages - 1)
        self.page_indicator.label = f"Page {self.current_page + 1}/{self.max_pages}"

    def build_embed(self) -> discord.Embed:
        title_suffix = f" (Tag: [{self.tag_filter}])" if self.tag_filter else ""
        embed = discord.Embed(
            title=f"🎴 {self.user.display_name}'s Card Collection{title_suffix}",
            description=f"Total Cards: **{len(self.rows)}**",
            color=discord.Color.purple()
        )

        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.rows))
        page_rows = self.rows[start_idx:end_idx]

        for row in page_rows:
            if len(row) >= 10:
                card_id, code, char_name, series, rarity, mint_num, edition, img_url, tag_val, q_val = row[:10]
            else:
                card_id, code, char_name, series, rarity, mint_num, edition, img_url, tag_val = row
                q_val = "Good ⭐⭐"

            code_str = code if code else f"c{card_id:04d}"
            ed_val = edition if edition else 1
            tag_disp = f" 🏷️ `[{tag_val}]`" if tag_val else ""
            embed.add_field(
                name=f"🆔 Card ID: `{code_str}` • {char_name}{tag_disp}",
                value=f"Edition {ed_val} • Print #{mint_num} | {q_val}\n📺 *{series}* | {rarity}",
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages} • Type /card code:<code> to see full card artwork!")
        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.secondary, custom_id="coll_prev_btn")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's menu!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.primary, disabled=True, custom_id="coll_page_ind")
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary, custom_id="coll_next_btn")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's menu!", ephemeral=True)
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

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

        view = CollectionPaginatorView(user, rows, tag_filter)
        embed = view.build_embed()

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=view if view.max_pages > 1 else None)
        else:
            await ctx_or_interaction.send(embed=embed, view=view if view.max_pages > 1 else None)

    async def process_view_card(self, ctx_or_interaction, card_code_query: str = None):
        try:
            user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
            conn = sqlite3.connect(DB_PATH, timeout=20.0)
            cursor = conn.cursor()

            if not card_code_query:
                cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality, grabbed_at FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
                row = cursor.fetchone()
            else:
                query_str = card_code_query.lower().strip()
                cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality, grabbed_at FROM inventory WHERE (code = ? OR id = ?)", (query_str, query_str))
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
                    msg = f"Coo coo! ⚠️ Card ID or Tag `{card_code_query}` not found!"
                    
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg)
                else:
                    await ctx_or_interaction.send(msg)
                return

            cid, code, uid, char_name, series, rarity, mint_num, edition, img_url, tag_val, q_val, grabbed_at = row
            conn.close()

            owner = self.bot.get_user(uid)
            owner_name = owner.mention if owner else f"<@{uid}>"
            ed_val = edition if edition else 1
            code_str = code if code else f"c{cid:04d}"
            q_disp = (q_val or "Good ⭐⭐").strip()

            card_data = {
                "id": cid,
                "code": code_str,
                "character_name": char_name,
                "series_name": series,
                "rarity": rarity,
                "mint_number": mint_num,
                "edition": ed_val,
                "quality": q_disp,
                "image_url": img_url
            }

            buf = await render_single_card(card_data)
            file = discord.File(fp=buf, filename="card.png")

            tag_disp = f"🏷️ **Tag:** `[{tag_val}]`\n" if tag_val else ""

            embed = discord.Embed(
                title=f"🆔 Card ID: {code_str} • {char_name}",
                description=(
                    f"📺 **Series:** {series}\n"
                    f"🌟 **Quality:** {q_disp}\n"
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
        except Exception as e:
            print(f"Error in process_view_card: {e}")
            import traceback
            traceback.print_exc()
            err_msg = f"Coo coo! ⚠️ An error occurred while loading card artwork: {e}"
            try:
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(err_msg)
                else:
                    await ctx_or_interaction.send(err_msg)
            except Exception:
                pass

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

    async def process_items_inventory(self, ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        gems = get_user_gems(user.id)
        dust = get_user_dust(user.id)
        drop_t = get_user_drop_tickets(user.id)
        grab_t = get_user_grab_tickets(user.id)
        now_ts = int(time.time())

        if is_user_premium(user.id):
            prem_until = get_user_premium_until(user.id)
            rem_days = max(1, (prem_until - now_ts) // 86400)
            prem_text = f"👑 **PREMIUM ACTIVE** ({rem_days} days left — 7.5m Drop / 2.5m Grab CD!)"
        else:
            prem_text = "⚪ Standard Member (15m Drop / 5m Grab CD)"

        embed = discord.Embed(
            title=f"🎒 {user.display_name}'s Inventory & Bag",
            description=f"Below are all the items and currencies currently in your bag:",
            color=discord.Color.gold()
        )

        embed.add_field(name="💎 Gems Balance", value=f"**{gems:,} Gems 💎**", inline=True)
        embed.add_field(name="🧪 Dust Flask", value=f"**{dust:,} Dust 🧪**", inline=True)
        embed.add_field(name="🎟️ Drop Tickets", value=f"**{drop_t} Ticket(s) 🎟️**", inline=True)
        embed.add_field(name="🖐️ Grab Tickets", value=f"**{grab_t} Ticket(s) 🖐️**", inline=True)
        embed.add_field(name="👤 Membership Status", value=prem_text, inline=False)

        embed.set_footer(text="Type /collection or !c to view your Anime Cards binder!")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    # --- CARDS COLLECTION COMMANDS ---
    @app_commands.command(name="collection", description="View your collected Anime Cards binder (Optional tag filter)")
    async def collection_slash(self, interaction: discord.Interaction, tag: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_inventory(interaction, tag)

    @commands.command(name="collection")
    async def collection_prefix(self, ctx, *, tag: str = None):
        await self.process_inventory(ctx, tag)

    @commands.command(name="c")
    async def collection_prefix_c(self, ctx, *, tag: str = None):
        await self.process_inventory(ctx, tag)

    @commands.command(name="binder")
    async def collection_prefix_binder(self, ctx, *, tag: str = None):
        await self.process_inventory(ctx, tag)

    @commands.command(name="col")
    async def collection_prefix_col(self, ctx, *, tag: str = None):
        await self.process_inventory(ctx, tag)

    # --- ITEMS INVENTORY COMMANDS ---
    @app_commands.command(name="inventory", description="View your items, gems, drop/grab tickets, and membership status")
    async def inventory_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_items_inventory(interaction)

    @commands.command(name="inventory")
    async def inventory_prefix(self, ctx):
        await self.process_items_inventory(ctx)

    @commands.command(name="inv")
    async def inventory_prefix_inv(self, ctx):
        await self.process_items_inventory(ctx)

    @commands.command(name="i")
    async def inventory_prefix_i(self, ctx):
        await self.process_items_inventory(ctx)

    @commands.command(name="items")
    async def inventory_prefix_items(self, ctx):
        await self.process_items_inventory(ctx)

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

    async def process_repair_card(self, ctx_or_interaction, card_code_query: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        card_row = get_card_by_code_and_owner(card_code_query if card_code_query else "", user.id) if card_code_query else None
        if not card_row:
            conn = sqlite3.connect(DB_PATH, timeout=20.0)
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            conn.close()

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
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        cursor.execute("SELECT image_url FROM inventory WHERE (code = ? OR id = ?) AND user_id = ?", (code_str.lower(), code_str, user.id))
        img_row = cursor.fetchone()
        conn.close()
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

    async def display_single_character_lookup(self, ctx_or_interaction, char_name: str, series: str, img_url: str, rarity: str, print_num_target: int = None):
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()

        # If a specific print number was requested (e.g. !lu Yor Forger 1)
        if print_num_target is not None:
            cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality, grabbed_at FROM inventory WHERE LOWER(character_name) = LOWER(?) AND mint_number = ?", (char_name, print_num_target))
            inv_row = cursor.fetchone()
            conn.close()

            if not inv_row:
                msg = f"Coo coo! ⚠️ **{char_name}** Print #{print_num_target} has not been claimed yet or is not in inventory!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg)
                else:
                    await ctx_or_interaction.send(msg)
                return

            cid, code, uid, cname, sname, rval, mnum, edval, iurl, tval, qval, grabbed_at = inv_row
            card_data = {
                "id": cid,
                "code": code if code else f"c{cid:04d}",
                "character_name": cname,
                "series_name": sname,
                "rarity": rval,
                "mint_number": mnum,
                "edition": edval if edval else 1,
                "quality": qval if qval else "Good ⭐⭐",
                "image_url": iurl
            }

            buf = await render_single_card(card_data)
            file = discord.File(fp=buf, filename="card.png")
            owner = self.bot.get_user(uid)
            owner_mention = owner.mention if owner else f"<@{uid}>"

            embed = discord.Embed(
                title=f"🎴 {char_name} · Print #{mnum}",
                description=(
                    f"📺 **Series:** {sname}\n"
                    f"✨ **Rarity:** {rval}\n"
                    f"🌟 **Quality:** {card_data['quality']}\n"
                    f"🆔 **Card ID:** `{card_data['code'].upper()}`\n"
                    f"👤 **Owner:** {owner_mention}"
                ),
                color=discord.Color.purple()
            )
            embed.set_image(url="attachment://card.png")

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed, file=file)
            else:
                await ctx_or_interaction.send(embed=embed, file=file)
            return

        # Overview Mode: list all claimed prints for this character across all players!
        cursor.execute("SELECT code, user_id, mint_number, edition, quality FROM inventory WHERE LOWER(character_name) = LOWER(?) ORDER BY mint_number ASC", (char_name,))
        inv_rows = cursor.fetchall()
        conn.close()

        embed = discord.Embed(
            title=f"🔍 Character Lookup: {char_name}",
            description=(
                f"📺 **Series:** {series}\n"
                f"✨ **Rarity:** {rarity}\n"
                f"📊 **Claimed in Circulation:** **{len(inv_rows)} cards**"
            ),
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=img_url)

        if not inv_rows:
            embed.add_field(
                name="🎴 Copies in Circulation",
                value="*No copies of this card have been claimed yet!*",
                inline=False
            )
        else:
            lines = []
            for r in inv_rows[:10]:
                ccode, uid, mnum, edval, qval = r
                owner = self.bot.get_user(uid)
                owner_disp = owner.mention if owner else f"<@{uid}>"
                q_disp = qval if qval else "Good ⭐⭐"
                lines.append(f"• **Print #{mnum}** (ED {edval or 1}) — `{ccode}` | {q_disp} ➔ {owner_disp}")
            
            embed.add_field(
                name="🎴 Claimed Prints List",
                value="\n".join(lines),
                inline=False
            )
            if len(inv_rows) > 10:
                embed.set_footer(text=f"Showing 10 of {len(inv_rows)} prints • Type !lu {char_name} <print_num> to view a specific card!")
            else:
                embed.set_footer(text=f"Type !lu {char_name} <print_num> to view a specific card!")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_character_lookup(self, ctx_or_interaction, query: str):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        if not query:
            msg = "Coo coo! ⚠️ Please specify a character name or print number! e.g. `!lu Yor Forger` or `!lu Gojo 1`"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        parts = query.strip().split()
        print_num_target = None
        if len(parts) > 1 and parts[-1].isdigit():
            print_num_target = int(parts[-1])
            char_search = " ".join(parts[:-1])
        else:
            char_search = " ".join(parts)

        paginator = CharacterSearchPaginatorView(self.bot, user, char_search, print_num_target)
        if paginator.total_matches == 0:
            msg = f"Coo coo! ⚠️ Character matching `{char_search}` not found in master database pool!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        if paginator.total_matches == 1:
            # Single exact match: display character overview directly!
            match = paginator.current_matches[0]
            await self.display_single_character_lookup(ctx_or_interaction, match[0], match[1], match[2], match[3], print_num_target)
            return

        # Multiple matches: render interactive paginated selection list!
        embed = paginator.build_embed()
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=paginator)
        else:
            await ctx_or_interaction.send(embed=embed, view=paginator)

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

    @app_commands.command(name="lu", description="Lookup character details, circulation stats, or a specific print number")
    async def lu_slash(self, interaction: discord.Interaction, character: str, print_num: int = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        q = f"{character} {print_num}" if print_num else character
        await self.process_character_lookup(interaction, q)

    @commands.command(name="lu", aliases=["lookup", "klu", "klookup"])
    async def lu_prefix(self, ctx, *, query: str = None):
        if query and query.lower().startswith("s:"):
            s_query = query[2:].strip()
            await self.process_series_lookup(ctx, s_query)
        else:
            await self.process_character_lookup(ctx, query)

    async def process_series_lookup(self, ctx_or_interaction, series_query: str):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        if not series_query:
            msg = "Coo coo! ⚠️ Please specify a series name! e.g. `!slu SPY x FAMILY` or `!slu Bleach`"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        list_paginator = SeriesListPaginatorView(self.bot, user, series_query.strip())
        if list_paginator.total_matches == 0:
            msg = f"Coo coo! ⚠️ Series matching `{series_query}` not found in master database pool!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        if list_paginator.total_matches == 1:
            exact_series = list_paginator.matching_series[0]
            await self.display_single_series_roster(ctx_or_interaction, exact_series)
            return

        embed = list_paginator.build_embed()
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=list_paginator)
        else:
            await ctx_or_interaction.send(embed=embed, view=list_paginator)

    async def display_single_series_roster(self, ctx_or_interaction, series_name: str):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        char_paginator = SeriesCharacterPaginatorView(self.bot, user, series_name)
        embed = char_paginator.build_embed()
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=char_paginator)
        else:
            await ctx_or_interaction.send(embed=embed, view=char_paginator)

    @app_commands.command(name="slu", description="Lookup all characters in a specific anime series")
    async def slu_slash(self, interaction: discord.Interaction, series: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_series_lookup(interaction, series)

    @commands.command(name="slu", aliases=["serieslookup", "slookup"])
    async def slu_prefix(self, ctx, *, series: str = None):
        await self.process_series_lookup(ctx, series)

class CharacterSearchPaginatorView(discord.ui.View):
    def __init__(self, bot, user: discord.User, search_query: str, print_num_target: int = None):
        super().__init__(timeout=180.0)
        self.bot = bot
        self.user = user
        self.search_query = search_query
        self.print_num_target = print_num_target
        self.current_page = 0
        self.per_page = 5
        self.total_matches = self.count_matches()
        self.max_pages = max(1, (self.total_matches + self.per_page - 1) // self.per_page)
        self.current_matches = []
        self.update_view_items()

    def count_matches(self) -> int:
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        tokens = [t.strip().lower() for t in self.search_query.split() if t.strip()]
        if not tokens:
            conn.close()
            return 0
        
        clauses = []
        params = []
        for t in tokens:
            clauses.append("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(character_name), 'ō', 'o'), 'ū', 'u'), 'ā', 'a'), 'ē', 'e'), 'ī', 'i') LIKE ?")
            params.append(f"%{t}%")
        
        sql = f"SELECT COUNT(*) FROM cards_pool WHERE {' AND '.join(clauses)}"
        cursor.execute(sql, tuple(params))
        cnt = cursor.fetchone()[0]
        conn.close()
        return cnt

    def fetch_page_matches(self) -> list:
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        tokens = [t.strip().lower() for t in self.search_query.split() if t.strip()]
        if not tokens:
            conn.close()
            return []

        clauses = []
        params = []
        for t in tokens:
            clauses.append("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(character_name), 'ō', 'o'), 'ū', 'u'), 'ā', 'a'), 'ē', 'e'), 'ī', 'i') LIKE ?")
            params.append(f"%{t}%")
        
        offset = self.current_page * self.per_page
        params.extend([self.per_page, offset])
        sql = f"""
        SELECT character_name, series_name, image_url, rarity 
        FROM cards_pool 
        WHERE {' AND '.join(clauses)} 
        ORDER BY length(character_name) ASC, character_name ASC 
        LIMIT ? OFFSET ?
        """
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def update_view_items(self):
        self.clear_items()
        self.current_matches = self.fetch_page_matches()

        # Add selection button for each match on current page (up to 5)
        for idx, match in enumerate(self.current_matches):
            cname, sname, iurl, rval = match
            btn = discord.ui.Button(
                label=f"{idx + 1}. {cname[:22]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"char_sel_{idx}_{self.current_page}"
            )
            btn.callback = self.make_select_callback(match)
            self.add_item(btn)

        # Pagination controls
        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0), custom_id=f"cs_prev_{self.current_page}")
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            ind_btn = discord.ui.Button(label=f"Page {self.current_page + 1}/{self.max_pages}", style=discord.ButtonStyle.secondary, disabled=True, custom_id=f"cs_ind_{self.current_page}")
            self.add_item(ind_btn)

            next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.max_pages - 1), custom_id=f"cs_next_{self.current_page}")
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

    def make_select_callback(self, match_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
                return
            await interaction.response.defer()
            cname, sname, iurl, rval = match_data
            cog = self.bot.get_cog("InventoryCog")
            if cog:
                await cog.display_single_character_lookup(interaction, cname, sname, iurl, rval, self.print_num_target)
        return callback

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🔍 Character Search Results: `{self.search_query}`",
            description=f"Found **{self.total_matches}** matching characters in master pool.\nClick a button below to inspect a character!",
            color=discord.Color.purple()
        )

        for idx, match in enumerate(self.current_matches):
            cname, sname, iurl, rval = match
            embed.add_field(
                name=f"{idx + 1}️⃣ **{cname}**",
                value=f"📺 *{sname}* | {rval}",
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages} • Showing 5 per page")
        return embed

class SeriesListPaginatorView(discord.ui.View):
    def __init__(self, bot, user: discord.User, series_query: str):
        super().__init__(timeout=180.0)
        self.bot = bot
        self.user = user
        self.series_query = series_query
        self.current_page = 0
        self.per_page = 5
        self.matching_series = self.fetch_all_series()
        self.total_matches = len(self.matching_series)
        self.max_pages = max(1, (self.total_matches + self.per_page - 1) // self.per_page)
        self.current_page_series = []
        self.update_view_items()

    def fetch_all_series(self) -> list:
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        tokens = [t.strip().lower() for t in self.series_query.split() if t.strip()]
        if not tokens:
            conn.close()
            return []

        clauses = []
        params = []
        for t in tokens:
            clauses.append("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(series_name), 'ō', 'o'), 'ū', 'u'), 'ā', 'a'), 'ē', 'e'), 'ī', 'i') LIKE ?")
            params.append(f"%{t}%")

        sql = f"SELECT DISTINCT series_name FROM cards_pool WHERE {' AND '.join(clauses)} ORDER BY series_name ASC"
        cursor.execute(sql, tuple(params))
        rows = [r[0] for r in cursor.fetchall()]
        conn.close()
        return rows

    def update_view_items(self):
        self.clear_items()
        start = self.current_page * self.per_page
        end = start + self.per_page
        self.current_page_series = self.matching_series[start:end]

        for idx, sname in enumerate(self.current_page_series):
            btn = discord.ui.Button(
                label=f"{idx + 1}. {sname[:22]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"series_sel_{idx}_{self.current_page}"
            )
            btn.callback = self.make_select_callback(sname)
            self.add_item(btn)

        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0), custom_id=f"sl_prev_{self.current_page}")
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            ind_btn = discord.ui.Button(label=f"Page {self.current_page + 1}/{self.max_pages}", style=discord.ButtonStyle.secondary, disabled=True, custom_id=f"sl_ind_{self.current_page}")
            self.add_item(ind_btn)

            next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.max_pages - 1), custom_id=f"sl_next_{self.current_page}")
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

    def make_select_callback(self, series_name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
                return
            await interaction.response.defer()
            cog = self.bot.get_cog("InventoryCog")
            if cog:
                await cog.display_single_series_roster(interaction, series_name)
        return callback

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()

        embed = discord.Embed(
            title=f"📺 Series Search Results: `{self.series_query}`",
            description=f"Found **{self.total_matches}** matching anime series.\nClick a series button below to view its character roster!",
            color=discord.Color.blue()
        )

        for idx, sname in enumerate(self.current_page_series):
            cursor.execute("SELECT COUNT(*) FROM cards_pool WHERE series_name = ?", (sname,))
            char_cnt = cursor.fetchone()[0]

            embed.add_field(
                name=f"{idx + 1}️⃣ **{sname}**",
                value=f"🎴 **{char_cnt} Characters** in Master Pool",
                inline=False
            )

        conn.close()
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages} • Showing 5 series per page")
        return embed

class SeriesCharacterPaginatorView(discord.ui.View):
    def __init__(self, bot, user: discord.User, series_name: str):
        super().__init__(timeout=180.0)
        self.bot = bot
        self.user = user
        self.series_name = series_name
        self.current_page = 0
        self.per_page = 5
        self.total_matches = self.count_matches()
        self.max_pages = max(1, (self.total_matches + self.per_page - 1) // self.per_page)
        self.current_matches = []
        self.update_view_items()

    def count_matches(self) -> int:
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cards_pool WHERE LOWER(series_name) = LOWER(?)", (self.series_name,))
        cnt = cursor.fetchone()[0]
        conn.close()
        return cnt

    def fetch_page_matches(self) -> list:
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        offset = self.current_page * self.per_page
        cursor.execute("""
        SELECT character_name, series_name, image_url, rarity 
        FROM cards_pool 
        WHERE LOWER(series_name) = LOWER(?) 
        ORDER BY character_name ASC 
        LIMIT ? OFFSET ?
        """, (self.series_name, self.per_page, offset))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def update_view_items(self):
        self.clear_items()
        self.current_matches = self.fetch_page_matches()

        for idx, match in enumerate(self.current_matches):
            cname, sname, iurl, rval = match
            btn = discord.ui.Button(
                label=f"{idx + 1}. {cname[:22]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"schar_sel_{idx}_{self.current_page}"
            )
            btn.callback = self.make_select_callback(match)
            self.add_item(btn)

        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0), custom_id=f"sc_prev_{self.current_page}")
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            ind_btn = discord.ui.Button(label=f"Page {self.current_page + 1}/{self.max_pages}", style=discord.ButtonStyle.secondary, disabled=True, custom_id=f"sc_ind_{self.current_page}")
            self.add_item(ind_btn)

            next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.max_pages - 1), custom_id=f"sc_next_{self.current_page}")
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

    def make_select_callback(self, match_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
                return
            await interaction.response.defer()
            cname, sname, iurl, rval = match_data
            cog = self.bot.get_cog("InventoryCog")
            if cog:
                await cog.display_single_character_lookup(interaction, cname, sname, iurl, rval)
        return callback

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()

        embed = discord.Embed(
            title=f"📺 Series Roster: {self.series_name}",
            description=f"Found **{self.total_matches}** characters in this anime series.\nClick a character button below to inspect circulation details!",
            color=discord.Color.blue()
        )

        for idx, match in enumerate(self.current_matches):
            cname, sname, iurl, rval = match
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE LOWER(character_name) = LOWER(?)", (cname,))
            claimed_cnt = cursor.fetchone()[0]

            embed.add_field(
                name=f"{idx + 1}️⃣ **{cname}**",
                value=f"✨ **Rarity:** {rval} | 📊 **Claimed in Circulation:** {claimed_cnt}",
                inline=False
            )

        conn.close()
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages} • Showing 5 characters per page")
        return embed

async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
