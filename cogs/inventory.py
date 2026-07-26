import time
from db import get_connection, release_connection
import discord
from discord.ext import commands
from discord import app_commands
from cogs.views.inventory import CollectionPaginatorView
from database import (
    get_user_inventory, get_user_dust, get_user_gems,
    get_user_drop_tickets, get_user_grab_tickets,
    is_user_premium, get_user_premium_until
)
from utils.renderer import render_single_card

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
            conn = get_connection()
            cursor = conn.cursor()

            if not card_code_query:
                cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality, grabbed_at, dropped_by FROM inventory WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user.id,))
                row = cursor.fetchone()
            else:
                query_str = card_code_query.lower().strip()
                cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality, grabbed_at, dropped_by FROM inventory WHERE (code = %s OR CAST(id AS TEXT) = %s)", (query_str, query_str))
                row = cursor.fetchone()

                if not row:
                    cursor.execute("SELECT COUNT(*) FROM inventory WHERE user_id = %s AND LOWER(tag) = %s", (user.id, query_str))
                    tag_count = cursor.fetchone()[0]
                    if tag_count > 0:
                        release_connection(conn)
                        await self.process_inventory(ctx_or_interaction, tag_filter=query_str)
                        return

            if not row:
                release_connection(conn)
                if not card_code_query:
                    msg = "Coo coo! ⚠️ You don't have any cards in your inventory yet! Type `/drop` to grab your first card!"
                else:
                    msg = f"Coo coo! ⚠️ Card ID or Tag `{card_code_query}` not found!"
                    
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg)
                else:
                    await ctx_or_interaction.send(msg)
                return

            cid, code, uid, char_name, series, rarity, mint_num, edition, img_url, tag_val, q_val, grabbed_at, dropped_by_id = row
            release_connection(conn)

            owner = self.bot.get_user(uid)
            owner_name = owner.mention if owner else f"<@{uid}>"
            dropper = self.bot.get_user(dropped_by_id) if dropped_by_id else None
            dropper_name = dropper.mention if dropper else (f"<@{dropped_by_id}>" if dropped_by_id else owner_name)
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
                    f"🎴 **Dropped by:** {dropper_name}\n"
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

    # --- CARD VIEW COMMANDS ---
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

async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
