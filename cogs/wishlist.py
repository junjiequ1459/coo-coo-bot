import psycopg2
import discord
from discord.ext import commands
from discord import app_commands
from db import get_connection, release_connection

def _init_wishlist_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlists (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            character_name TEXT NOT NULL,
            UNIQUE(user_id, character_name)
        )
    ''')
    conn.commit()
    release_connection(conn)

_init_wishlist_table()

async def get_wishlist_pings(channel, card_names: list) -> str:
    """
    Given a list of character names from a drop, check if any users
    in the server have those characters wishlisted.
    Returns a string of mentions to append to the drop message, or empty string.
    """
    if not card_names:
        return ""
    
    conn = get_connection()
    cursor = conn.cursor()
    
    placeholders = ",".join(["%s"] * len(card_names))
    query = f"SELECT user_id, character_name FROM wishlists WHERE LOWER(character_name) IN ({placeholders})"
    
    # We compare in lowercase to ensure case-insensitive matching
    cursor.execute(query, [name.lower() for name in card_names])
    rows = cursor.fetchall()
    release_connection(conn)
    
    if not rows:
        return ""
        
    matches = {}
    for uid, char_name in rows:
        member = channel.guild.get_member(uid)
        if member:
            # Re-capitalize char_name to match original dropped name if possible
            original_name = next((n for n in card_names if n.lower() == char_name.lower()), char_name)
            matches.setdefault(original_name, []).append(member.mention)
            
    if not matches:
        return ""
        
    alerts = []
    for char_name, mentions in matches.items():
        alerts.append(f"{char_name} wishlisted by {', '.join(mentions)}")
        
    return "💖 **Wishlist Alert!** " + " | ".join(alerts) + "!"


class WishlistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def process_wish(self, ctx_or_interaction, query: str):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check current wishlist count
        cursor.execute("SELECT COUNT(*) FROM wishlists WHERE user_id = %s", (user.id,))
        count = cursor.fetchone()[0]
        
        if count >= 10:
            release_connection(conn)
            msg = "Coo coo! ⚠️ Your wishlist is full! (10/10) Please remove a character before adding another."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        cursor.execute("SELECT DISTINCT character_name FROM cards_pool WHERE character_name ILIKE %s", (f"%{query}%",))
        rows = cursor.fetchall()
        
        if not rows:
            release_connection(conn)
            msg = f"Coo coo! ⚠️ No characters found matching `{query}`!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return
            
        exact_match = None
        for r in rows:
            if r[0].lower() == query.lower():
                exact_match = r[0]
                break
                
        if exact_match:
            char_name = exact_match
        elif len(rows) == 1:
            char_name = rows[0][0]
        else:
            release_connection(conn)
            options = ", ".join([f"`{r[0]}`" for r in rows[:5]])
            if len(rows) > 5:
                options += f" ... and {len(rows)-5} more"
            msg = f"Coo coo! ⚠️ Multiple characters found matching `{query}`! Please be more specific:\n{options}"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return
            
        try:
            cursor.execute("INSERT INTO wishlists (user_id, character_name) VALUES (%s, %s)", (user.id, char_name))
            conn.commit()
            success = True
        except (psycopg2.IntegrityError, Exception):
            conn.rollback()
            success = False
            
        # Get new count
        cursor.execute("SELECT COUNT(*) FROM wishlists WHERE user_id = %s", (user.id,))
        new_count = cursor.fetchone()[0]
        release_connection(conn)
        
        if success:
            embed = discord.Embed(
                title="💖 Wishlist Added!",
                description=f"**{user.mention}** added **{char_name}** to their wishlist!\n\n*(Wishlist capacity: {new_count}/10)*",
                color=discord.Color.pink()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
        else:
            msg = f"Coo coo! ⚠️ **{char_name}** is already on your wishlist!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)

    async def process_unwish(self, ctx_or_interaction, query: str):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # We need to find the exact character in the wishlist
        cursor.execute("SELECT character_name FROM wishlists WHERE user_id = %s AND character_name ILIKE %s", (user.id, f"%{query}%"))
        rows = cursor.fetchall()
        
        if not rows:
            release_connection(conn)
            msg = f"Coo coo! ⚠️ No characters found on your wishlist matching `{query}`!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return
            
        exact_match = None
        for r in rows:
            if r[0].lower() == query.lower():
                exact_match = r[0]
                break
                
        if exact_match:
            char_name = exact_match
        elif len(rows) == 1:
            char_name = rows[0][0]
        else:
            release_connection(conn)
            options = ", ".join([f"`{r[0]}`" for r in rows])
            msg = f"Coo coo! ⚠️ Multiple characters found on your wishlist matching `{query}`! Please be more specific:\n{options}"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return
            
        cursor.execute("DELETE FROM wishlists WHERE user_id = %s AND character_name = %s", (user.id, char_name))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM wishlists WHERE user_id = %s", (user.id,))
        new_count = cursor.fetchone()[0]
        release_connection(conn)
        
        embed = discord.Embed(
            title="💔 Wishlist Removed!",
            description=f"**{user.mention}** removed **{char_name}** from their wishlist.\n\n*(Wishlist capacity: {new_count}/10)*",
            color=discord.Color.dark_grey()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_wishlist(self, ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT character_name FROM wishlists WHERE user_id = %s", (user.id,))
        rows = cursor.fetchall()
        release_connection(conn)
        
        count = len(rows)
        if count == 0:
            msg = "Coo coo! ⚠️ Your wishlist is empty!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return
            
        char_list = "\n".join([f"💖 {r[0]}" for r in rows])
        embed = discord.Embed(
            title=f"📖 {user.display_name}'s Wishlist ({count}/10)",
            description=char_list,
            color=discord.Color.pink()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="wish", description="Add a character to your wishlist")
    async def wish_slash(self, interaction: discord.Interaction, character: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_wish(interaction, character)

    @commands.command(name="wish")
    async def wish_prefix(self, ctx, *, character: str):
        await self.process_wish(ctx, character)

    @app_commands.command(name="unwish", description="Remove a character from your wishlist")
    async def unwish_slash(self, interaction: discord.Interaction, character: str):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_unwish(interaction, character)

    @commands.command(name="unwish")
    async def unwish_prefix(self, ctx, *, character: str):
        await self.process_unwish(ctx, character)

    @app_commands.command(name="wishlist", description="View your wishlist")
    async def wishlist_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_wishlist(interaction)

    @commands.command(name="wishlist", aliases=["wl"])
    async def wishlist_prefix(self, ctx):
        await self.process_wishlist(ctx)

async def setup(bot):
    await bot.add_cog(WishlistCog(bot))
