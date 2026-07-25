import discord
from discord.ext import commands
from discord import app_commands
from db import get_connection, release_connection
from config import display_rarity

MAX_FAVORITES = 5



class FavoritesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def process_fav(self, ctx_or_interaction, code: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        conn = get_connection()
        cursor = conn.cursor()

        # If no code, default to latest card
        if not code:
            cursor.execute("SELECT code FROM inventory WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user.id,))
            row = cursor.fetchone()
            if not row:
                release_connection(conn)
                msg = "Coo coo! ⚠️ You don't have any cards yet! Type `/drop` to start collecting!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(msg)
                return
            code = row[0]

        code = code.strip().lower()

        # Check card exists and belongs to user
        cursor.execute(
            "SELECT id, code, character_name, image_url FROM inventory WHERE (code = %s OR CAST(id AS TEXT) = %s) AND user_id = %s",
            (code, code, user.id)
        )
        card_row = cursor.fetchone()

        if not card_row:
            release_connection(conn)
            msg = f"Coo coo! ⚠️ Card `{code}` not found in your inventory!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        cid, card_code, char_name, img_url = card_row
        card_code = card_code if card_code else f"c{cid:04d}"

        # Check favorites count
        cursor.execute("SELECT COUNT(*) FROM favorites WHERE user_id = %s", (user.id,))
        fav_count = cursor.fetchone()[0]

        if fav_count >= MAX_FAVORITES:
            # Check if this card is already favorited (allow re-fav)
            cursor.execute("SELECT id FROM favorites WHERE user_id = %s AND card_code = %s", (user.id, card_code))
            if not cursor.fetchone():
                release_connection(conn)
                msg = f"Coo coo! ⚠️ Your favorites are full! (**{fav_count}/{MAX_FAVORITES}**) Use `!unfav <code>` to remove one first."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(msg)
                return

        # Check if already favorited
        cursor.execute("SELECT id FROM favorites WHERE user_id = %s AND card_code = %s", (user.id, card_code))
        if cursor.fetchone():
            release_connection(conn)
            msg = f"Coo coo! ⚠️ **{char_name}** (`{card_code}`) is already in your favorites!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        cursor.execute("INSERT INTO favorites (user_id, card_code) VALUES (%s, %s)", (user.id, card_code))
        conn.commit()
        new_count = fav_count + 1
        release_connection(conn)

        embed = discord.Embed(
            title="⭐ Added to Favorites!",
            description=(
                f"**{char_name}** (`{card_code}`) has been added to your favorites!\n\n"
                f"📋 **Favorites:** {new_count}/{MAX_FAVORITES} slots used"
            ),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=img_url if img_url else None)

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_unfav(self, ctx_or_interaction, code: str = None):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        if not code:
            msg = "Coo coo! ⚠️ Please specify a card code! e.g. `!unfav abc123`"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        code = code.strip().lower()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM favorites WHERE user_id = %s AND card_code = %s", (user.id, code))
        row = cursor.fetchone()

        if not row:
            release_connection(conn)
            msg = f"Coo coo! ⚠️ Card `{code}` is not in your favorites!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        cursor.execute("DELETE FROM favorites WHERE id = %s", (row[0],))
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM favorites WHERE user_id = %s", (user.id,))
        new_count = cursor.fetchone()[0]
        release_connection(conn)

        # Get card name for display
        conn2 = get_connection()
        cur2 = conn2.cursor()
        cur2.execute("SELECT character_name FROM inventory WHERE code = %s", (code,))
        name_row = cur2.fetchone()
        release_connection(conn2)
        char_disp = f"**{name_row[0]}** (`{code}`)" if name_row else f"`{code}`"

        embed = discord.Embed(
            title="💔 Removed from Favorites",
            description=f"{char_disp} has been removed from your favorites.\n\n📋 **Favorites:** {new_count}/{MAX_FAVORITES} slots used",
            color=discord.Color.dark_grey()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_favorites(self, ctx_or_interaction, target_user: discord.User = None):
        user = target_user or (ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT card_code FROM favorites WHERE user_id = %s ORDER BY id ASC", (user.id,))
        fav_rows = cursor.fetchall()

        if not fav_rows:
            release_connection(conn)
            if target_user and target_user.id != (ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author).id:
                msg = f"Coo coo! 📋 **{user.display_name}** has no favorites yet!"
            else:
                msg = "Coo coo! 📋 Your favorites are empty! Use `!fav <code>` to add cards."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        embed = discord.Embed(
            title=f"⭐ {user.display_name}'s Favorites ({len(fav_rows)}/{MAX_FAVORITES})",
            color=discord.Color.gold()
        )

        for idx, (card_code,) in enumerate(fav_rows):
            cursor.execute(
                "SELECT character_name, series_name, rarity, quality FROM inventory WHERE code = %s",
                (card_code,)
            )
            card = cursor.fetchone()
            if card:
                char_name, series, rarity, q_val = card
                q_disp = q_val if q_val else "Good ⭐⭐"
                embed.add_field(
                    name=f"{'⭐' * (idx + 1)} {char_name}",
                    value=f"🆔 `{card_code}` | {display_rarity(rarity)}\n📺 *{series}* | {q_disp}",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"{'⭐' * (idx + 1)} Unknown Card",
                    value=f"🆔 `{card_code}` — *Card no longer in inventory*",
                    inline=False
                )

        release_connection(conn)
        embed.set_footer(text="Use !fav <code> to add • !unfav <code> to remove")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    # --- Slash & Prefix Commands ---
    @app_commands.command(name="fav", description="Add a card to your favorites showcase (Defaults to latest card)")
    async def fav_slash(self, interaction: discord.Interaction, code: str = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_fav(interaction, code)

    @commands.command(name="fav")
    async def fav_prefix(self, ctx, code: str = None):
        await self.process_fav(ctx, code)

    @commands.command(name="favorite")
    async def favorite_prefix(self, ctx, code: str = None):
        await self.process_fav(ctx, code)

    @app_commands.command(name="unfav", description="Remove a card from your favorites")
    async def unfav_slash(self, interaction: discord.Interaction, code: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_unfav(interaction, code)

    @commands.command(name="unfav")
    async def unfav_prefix(self, ctx, code: str = None):
        await self.process_unfav(ctx, code)

    @app_commands.command(name="favorites", description="View your or another user's favorite cards showcase")
    async def favorites_slash(self, interaction: discord.Interaction, user: discord.User = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_favorites(interaction, user)

    @commands.command(name="favorites")
    async def favorites_prefix(self, ctx, user: discord.User = None):
        await self.process_favorites(ctx, user)

    @commands.command(name="favs")
    async def favs_prefix(self, ctx, user: discord.User = None):
        await self.process_favorites(ctx, user)

    @app_commands.command(name="profile", description="View a user's favorite cards showcase")
    async def profile_slash(self, interaction: discord.Interaction, user: discord.User = None):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_favorites(interaction, user)

    @commands.command(name="profile")
    async def profile_prefix(self, ctx, user: discord.User = None):
        await self.process_favorites(ctx, user)

async def setup(bot):
    await bot.add_cog(FavoritesCog(bot))
