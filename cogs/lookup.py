from db import get_connection, release_connection
import discord
from discord.ext import commands
from discord import app_commands
from utils.renderer import render_single_card
from config import display_rarity
from cogs.views.lookup import (
    CharacterSearchPaginatorView, SeriesCharacterPaginatorView,
    SeriesListPaginatorView,
)

class LookupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def display_single_character_lookup(self, ctx_or_interaction, char_name: str, series: str, img_url: str, rarity: str, print_num_target: int = None):
        conn = get_connection()
        cursor = conn.cursor()

        # If a specific print number was requested (e.g. !lu Yor Forger 1)
        if print_num_target is not None:
            cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, quality FROM inventory WHERE LOWER(character_name) = LOWER(%s) AND mint_number = %s", (char_name, print_num_target))
            inv_row = cursor.fetchone()
            release_connection(conn)

            if not inv_row:
                msg = f"Coo coo! ⚠️ **{char_name}** Print #{print_num_target} has not been claimed yet or is not in inventory!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg)
                else:
                    await ctx_or_interaction.send(msg)
                return

            cid, code, uid, cname, sname, rval, mnum, edval, iurl, qval = inv_row
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

            buf, is_gif = await render_single_card(card_data)
            ext = "gif" if is_gif else "png"
            file = discord.File(fp=buf, filename=f"card.{ext}")
            owner = self.bot.get_user(uid)
            owner_mention = owner.mention if owner else f"<@{uid}>"

            embed = discord.Embed(
                title=f"🎴 {char_name} · Print #{mnum}",
                description=(
                    f"📺 **Series:** {sname}\n"
                    f"✨ **Rarity:** {display_rarity(rval)}\n"
                    f"🌟 **Quality:** {card_data['quality']}\n"
                    f"🆔 **Card ID:** `{card_data['code'].upper()}`\n"
                    f"👤 **Owner:** {owner_mention}"
                ),
                color=discord.Color.purple()
            )
            embed.set_image(url=f"attachment://card.{ext}")

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed, file=file)
            else:
                await ctx_or_interaction.send(embed=embed, file=file)
            return

        # Overview Mode: list all claimed prints for this character across all players!
        cursor.execute("SELECT code, user_id, mint_number, edition, quality FROM inventory WHERE LOWER(character_name) = LOWER(%s) ORDER BY mint_number ASC", (char_name,))
        inv_rows = cursor.fetchall()
        release_connection(conn)

        embed = discord.Embed(
            title=f"🔍 Character Lookup: {char_name}",
            description=(
                f"📺 **Series:** {series}\n"
                f"✨ **Rarity:** {display_rarity(rarity)}\n"
                f"📊 **Claimed in Circulation:** **{len(inv_rows)} cards**"
            ),
            color=discord.Color.purple()
        )
        # Generate a generic preview of the card
        card_data = {
            "character_name": char_name,
            "series_name": series,
            "rarity": rarity,
            "mint_number": "?",
            "edition": 1,
            "quality": "Mint ⭐⭐⭐⭐",
            "image_url": img_url,
            "code": "PREVIEW"
        }
        
        buf, is_gif = await render_single_card(card_data)
        ext = "gif" if is_gif else "png"
        file = discord.File(fp=buf, filename=f"preview.{ext}")
        embed.set_image(url=f"attachment://preview.{ext}")

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
            await ctx_or_interaction.followup.send(embed=embed, file=file)
        else:
            await ctx_or_interaction.send(embed=embed, file=file)

    async def process_character_lookup(self, ctx_or_interaction, query: str):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        if not query:
            msg = "Coo coo! ⚠️ Please specify a character name, card code, or print number! e.g. `!lu Yor Forger`, `!lu Firefly #1`, or `!lu c0001`"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        cleaned_q = query.strip()

        # Check if query is a direct card code (e.g. c0001, c1) or numeric inventory ID
        code_search = cleaned_q.lower()
        if (code_search.startswith('c') and code_search[1:].isdigit()) or code_search.isdigit():
            conn = get_connection()
            cursor = conn.cursor()
            query_id_str = code_search[1:] if code_search.startswith('c') else code_search
            cursor.execute("""
            SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, quality
            FROM inventory 
            WHERE LOWER(code) = %s OR CAST(id AS TEXT) = %s
            """, (code_search, query_id_str))
            inv_row = cursor.fetchone()
            release_connection(conn)

            if inv_row:
                cid, code, uid, cname, sname, rval, mnum, edval, iurl, qval = inv_row
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

                buf, is_gif = await render_single_card(card_data)
                ext = "gif" if is_gif else "png"
                file = discord.File(fp=buf, filename=f"card.{ext}")
                owner = self.bot.get_user(uid)
                owner_mention = owner.mention if owner else f"<@{uid}>"

                embed = discord.Embed(
                    title=f"🎴 {cname} · Print #{mnum}",
                    description=(
                        f"📺 **Series:** {sname}\n"
                        f"✨ **Rarity:** {display_rarity(rval)}\n"
                        f"🌟 **Quality:** {card_data['quality']}\n"
                        f"🆔 **Card ID:** `{card_data['code'].upper()}`\n"
                        f"👤 **Owner:** {owner_mention}"
                    ),
                    color=discord.Color.purple()
                )
                embed.set_image(url=f"attachment://card.{ext}")

                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(embed=embed, file=file)
                else:
                    await ctx_or_interaction.send(embed=embed, file=file)
                return

        # Parse character search query and optional print number target (e.g. "Firefly #1" or "goku 1")
        parts = cleaned_q.split()
        print_num_target = None
        
        if len(parts) > 1 and parts[-1].lstrip('#').isdigit():
            print_num_target = int(parts[-1].lstrip('#'))
            char_search = " ".join(parts[:-1])
        else:
            char_search = " ".join(parts)

        # If a specific print number was requested (e.g. !lu goku 1 or !lu Firefly 1)
        if print_num_target is not None:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 1. Check if a claimed card exists in inventory matching char_search and mint_number
            tokens = [t.strip().lower() for t in char_search.split() if t.strip()]
            clauses = ["REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(character_name), 'ō', 'o'), 'ū', 'u'), 'ā', 'a'), 'ē', 'e'), 'ī', 'i') ILIKE %s" for _ in tokens]
            params = [f"%{t}%" for t in tokens]
            params.append(print_num_target)

            inv_sql = f"""
            SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality, grabbed_at
            FROM inventory
            WHERE {' AND '.join(clauses)} AND mint_number = %s
            ORDER BY length(character_name) ASC
            LIMIT 1
            """
            cursor.execute(inv_sql, tuple(params))
            inv_row = cursor.fetchone()
            release_connection(conn)

            if inv_row:
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

                buf, is_gif = await render_single_card(card_data)
                ext = "gif" if is_gif else "png"
                file = discord.File(fp=buf, filename=f"card.{ext}")
                owner = self.bot.get_user(uid)
                owner_mention = owner.mention if owner else f"<@{uid}>"

                embed = discord.Embed(
                    title=f"🎴 {cname} · Print #{mnum}",
                    description=(
                        f"📺 **Series:** {sname}\n"
                        f"✨ **Rarity:** {display_rarity(rval)}\n"
                        f"🌟 **Quality:** {card_data['quality']}\n"
                        f"🆔 **Card ID:** `{card_data['code'].upper()}`\n"
                        f"👤 **Owner:** {owner_mention}"
                    ),
                    color=discord.Color.purple()
                )
                embed.set_image(url=f"attachment://card.{ext}")

                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(embed=embed, file=file)
                else:
                    await ctx_or_interaction.send(embed=embed, file=file)
                return

        paginator = CharacterSearchPaginatorView(self.bot, user, char_search, print_num_target)
        if paginator.total_matches == 0:
            msg = f"Coo coo! ⚠️ Character matching `{char_search}` not found in master database pool!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        # If a single match, or if a print_num_target was specified, display top match directly!
        if paginator.total_matches == 1 or print_num_target is not None:
            match = paginator.current_matches[0]
            await self.display_single_character_lookup(ctx_or_interaction, match[0], match[1], match[2], match[3], print_num_target)
            return

        # Multiple matches: render interactive paginated selection list!
        embed = paginator.build_embed()
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=paginator)
        else:
            await ctx_or_interaction.send(embed=embed, view=paginator)

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

    @app_commands.command(name="lu", description="Lookup character details, circulation stats, or a specific print number")
    async def lu_slash(self, interaction: discord.Interaction, character: str, print_num: int = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        q = f"{character} {print_num}" if print_num else character
        await self.process_character_lookup(interaction, q)

    @commands.command(name="lu", aliases=["lookup"])
    async def lu_prefix(self, ctx, *, query: str = None):
        if query and query.lower().startswith("s:"):
            s_query = query[2:].strip()
            await self.process_series_lookup(ctx, s_query)
        else:
            await self.process_character_lookup(ctx, query)

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

async def setup(bot):
    await bot.add_cog(LookupCog(bot))
