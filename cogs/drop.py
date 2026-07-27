import asyncio
import time
import random
import discord
from discord.ext import commands
from discord import app_commands
from config import DROP_PRIORITY_SEC, DROP_CLAIM_TIMEOUT_SEC
from db import get_connection, release_connection
from database import (
    get_user_cooldowns, set_user_cooldown, get_effective_cooldowns,
    get_user_drop_tickets, add_user_drop_tickets,
    get_user_grab_tickets, add_user_grab_tickets,
    save_card_to_inventory, get_cards_from_db_pool, roll_card_quality,
    get_next_mint, generate_card_code
)
from utils.renderer import render_three_cards_composite
from utils.anilist import fetch_random_anilist_cards
from cogs.wishlist import get_wishlist_pings

class CardGrabButton(discord.ui.Button):
    def __init__(self, index: int, card_info: dict):
        super().__init__(
            label=f"Grab Card {index + 1}",
            emoji=["1️⃣", "2️⃣", "3️⃣"][index],
            style=discord.ButtonStyle.primary,
            custom_id=f"coocoo_grab_{index}_{random.randint(10000, 99999)}"
        )
        self.index = index
        self.card_info = card_info

    async def callback(self, interaction: discord.Interaction):
        view: CardDropView = self.view
        async with view.lock:
            if self.index in view.claimed_by:
                await interaction.response.send_message("Coo coo! ⚠️ This card has already been claimed!", ephemeral=True)
                return

            now_ts = int(time.time())

            # Check Grab Cooldown (5 Minutes, or 2.5 Minutes for Premium)
            _, l_grab, _ = get_user_cooldowns(interaction.user.id)
            _, g_cd = get_effective_cooldowns(interaction.user.id)
            elapsed_grab = now_ts - l_grab
            used_grab_ticket = False
            if elapsed_grab < g_cd:
                g_tickets = get_user_grab_tickets(interaction.user.id)
                if g_tickets > 0:
                    add_user_grab_tickets(interaction.user.id, -1)
                    used_grab_ticket = True
                else:
                    rem = g_cd - elapsed_grab
                    mins = rem // 60
                    secs = rem % 60
                    await interaction.response.send_message(
                        f"Coo coo! ⏳ Your **Grab** is on cooldown! Return in **{mins}m {secs}s**! Type `!cd` to view your cooldowns or `/shop` to buy Grab Tickets 🖐️!",
                        ephemeral=True
                    )
                    return

            # Check Exclusive Priority Window for the Dropper
            elapsed_drop = time.time() - view.drop_time
            if elapsed_drop < DROP_PRIORITY_SEC and interaction.user.id != view.dropper_id:
                rem_prio = int(DROP_PRIORITY_SEC - elapsed_drop) + 1
                await interaction.response.send_message(
                    f"Coo coo! ⏳ <@{view.dropper_id}> has **{int(DROP_PRIORITY_SEC)} seconds of exclusive drop priority**! ({rem_prio}s remaining)",
                    ephemeral=True
                )
                return

            view.claimed_by[self.index] = interaction.user.display_name
            if not used_grab_ticket:
                set_user_cooldown(interaction.user.id, "grab", now_ts)
            
            self.disabled = True
            self.label = f"Card {self.index + 1}: {interaction.user.display_name}"
            self.style = discord.ButtonStyle.success

            q_val = self.card_info.get("quality") or roll_card_quality()
            self.card_info["quality"] = q_val

            save_card_to_inventory(
                user_id=interaction.user.id,
                code=self.card_info["code"],
                character_name=self.card_info["name"],
                series_name=self.card_info["series"],
                image_url=self.card_info["image"],
                rarity=self.card_info["rarity"],
                mint_number=self.card_info["temp_mint"],
                edition=1,
                quality=q_val,
                dropped_by=view.dropper_id,
                frame="default",
            )

            if used_grab_ticket:
                rem_gt = get_user_grab_tickets(interaction.user.id)
                try:
                    await interaction.channel.send(
                        f"🖐️ {interaction.user.mention} used an **Extra Grab Ticket**! Grab cooldown bypassed! ({rem_gt} tickets remaining)"
                    )
                except Exception:
                    pass

            await interaction.response.edit_message(embed=view.build_embed(), view=view)
            await interaction.followup.send(
                f"🎉 {interaction.user.mention} grabbed **{self.card_info['name']}** (**Edition 1 • Print #{self.card_info['temp_mint']} • {q_val}**)! `Card ID: {self.card_info['code']}`"
            )


class CardDropView(discord.ui.View):
    def __init__(self, cards: list, dropper_user, used_ticket: bool = False):
        super().__init__(timeout=DROP_CLAIM_TIMEOUT_SEC)
        self.lock = asyncio.Lock()
        self.cards = cards
        self.dropper_user = dropper_user
        self.dropper_id = dropper_user.id
        self.used_ticket = used_ticket
        self.drop_time = time.time()
        self.claimed_by = {}
        self.message = None
        for idx, card in enumerate(cards):
            self.add_item(CardGrabButton(idx, card))

    @property
    def is_fully_claimed(self) -> bool:
        return len(self.claimed_by) == len(self.cards)

    def build_embed(self) -> discord.Embed:
        lines = []
        emojis = ["1️⃣", "2️⃣", "3️⃣"]
        for idx, card in enumerate(self.cards):
            emoji = emojis[idx]
            if idx in self.claimed_by:
                lines.append(f"{emoji} ~~**{card['name']}**~~ · *{card['series']}* — ✅ **Claimed by {self.claimed_by[idx]}**")
            else:
                lines.append(f"{emoji} **{card['name']}** · *{card['series']}*")
        
        ticket_text = "🎟️ **Extra Drop Ticket Used!** (Drop Cooldown Bypassed!)\n" if self.used_ticket else ""
        
        desc = "\n".join(lines) + f"\n\n{ticket_text}"
        if not self.is_fully_claimed:
            desc += f"⏳ **Priority:** {self.dropper_user.mention} has **{int(DROP_PRIORITY_SEC)} seconds of exclusive drop priority**!\nClick a button below to grab a card!"
        else:
            desc += "🎉 **All cards from this drop have been claimed!**"

        embed = discord.Embed(
            title=f"🎴 {self.dropper_user.display_name}'s Card Drop!",
            description=desc,
            color=discord.Color.gold() if not self.is_fully_claimed else discord.Color.green()
        )
        embed.set_image(url="attachment://drop.png")
        embed.set_footer(text="Coo Coo Card Engine • Side-By-Side View")
        return embed

    async def on_timeout(self):
        if not self.is_fully_claimed:
            for child in self.children:
                if isinstance(child, CardGrabButton) and child.index not in self.claimed_by:
                    child.disabled = True
                    child.label = f"Card {child.index + 1} Expired"
                    child.style = discord.ButtonStyle.secondary
            if self.message:
                try:
                    await self.message.edit(embed=self.build_embed(), view=self)
                except Exception:
                    pass

class AdminForceDropSelect(discord.ui.Select):
    def __init__(self, drop_cog, ctx_or_interaction, user, rows: list[tuple]):
        self.drop_cog = drop_cog
        self.ctx_or_interaction = ctx_or_interaction
        self.user = user
        self.rows = rows
        
        options = []
        for i, row in enumerate(rows):
            char_name, series, img_url, rarity = row
            options.append(discord.SelectOption(
                label=f"{char_name}",
                description=f"{series} • {rarity}",
                value=str(i)
            ))
        
        super().__init__(placeholder="Multiple characters found. Select one to force drop...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        ctx_user = self.ctx_or_interaction.user if isinstance(self.ctx_or_interaction, discord.Interaction) else self.ctx_or_interaction.author
        if interaction.user.id != ctx_user.id:
            await interaction.response.send_message("Coo coo! You can't use this menu!", ephemeral=True)
            return

        selected_idx = int(self.values[0])
        row = self.rows[selected_idx]
        
        await interaction.response.defer()
        
        for child in self.view.children:
            child.disabled = True
        await interaction.message.edit(view=self.view)
        
        await self.drop_cog.execute_card_drop(self.ctx_or_interaction, self.user, forced_row=row, bypass_cooldown=True)

class AdminForceDropSelectView(discord.ui.View):
    def __init__(self, drop_cog, ctx_or_interaction, user, rows: list[tuple]):
        super().__init__(timeout=60)
        self.add_item(AdminForceDropSelect(drop_cog, ctx_or_interaction, user, rows))


class DropCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def execute_card_drop(self, ctx_or_interaction, user, forced_character: str = None, forced_row: tuple = None, bypass_cooldown: bool = False):
        if forced_character:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT character_name, series_name, image_url, rarity FROM cards_pool WHERE LOWER(character_name) ILIKE %s ORDER BY favourites DESC LIMIT 25", (f"%{forced_character.strip().lower()}%",))
            rows = cursor.fetchall()
            release_connection(conn)
            
            if not rows:
                msg = f"Coo coo! ⚠️ Character matching `{forced_character}` not found in master pool!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(msg)
                return
            
            if len(rows) == 1:
                forced_row = rows[0]
            else:
                view = AdminForceDropSelectView(self, ctx_or_interaction, user, rows)
                msg = f"🔍 Found multiple characters matching `{forced_character}`. Please select which one to force drop:"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg, view=view)
                else:
                    await ctx_or_interaction.send(msg, view=view)
                return
        try:
            now_ts = int(time.time())
            l_drop, _, _ = get_user_cooldowns(user.id)
            d_cd, _ = get_effective_cooldowns(user.id)
            elapsed_drop = now_ts - l_drop

            used_ticket = False
            if not bypass_cooldown:
                if elapsed_drop < d_cd:
                    tickets = get_user_drop_tickets(user.id)
                    if tickets > 0:
                        add_user_drop_tickets(user.id, -1)
                        used_ticket = True
                    else:
                        rem = d_cd - elapsed_drop
                        mins = rem // 60
                        secs = rem % 60
                        msg = f"Coo coo! ⏳ Your **Drop** is on cooldown! Return in **{mins}m {secs}s**! Type `!cd` to check your cooldowns or `/shop` to buy Drop Tickets 🎟️!"
                        if isinstance(ctx_or_interaction, discord.Interaction):
                            await ctx_or_interaction.followup.send(msg, ephemeral=True)
                        else:
                            await ctx_or_interaction.send(msg)
                        return

            cards = get_cards_from_db_pool(3)

            if forced_row:
                fc_name, fc_series, fc_img, fc_rarity = forced_row
                fc_mint = get_next_mint(fc_name)
                cards[0] = {
                    "code": generate_card_code(),
                    "name": fc_name,
                    "series": fc_series,
                    "image": fc_img,
                    "rarity": fc_rarity,
                    "quality": roll_card_quality(),
                    "temp_mint": fc_mint,
                    "edition": 1
                }

            if not cards or len(cards) < 3:
                cards = await fetch_random_anilist_cards(3)

            if not cards or len(cards) < 3:
                msg = "Coo coo! ⚠️ Couldn't fetch cards for drop. Please try again in a moment!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(msg)
                else:
                    await ctx_or_interaction.send(msg)
                return

            if not used_ticket:
                set_user_cooldown(user.id, "drop", now_ts)

            buf = await render_three_cards_composite(cards)
            file = discord.File(fp=buf, filename="drop.png")

            view = CardDropView(cards, dropper_user=user, used_ticket=used_ticket)
            embed = view.build_embed()

            if used_ticket:
                rem_t = get_user_drop_tickets(user.id)
                notice_text = f"🎟️ {user.mention} used an **Extra Drop Ticket**! Drop cooldown bypassed! ({rem_t} tickets remaining)"
                try:
                    await ctx_or_interaction.channel.send(notice_text)
                except Exception:
                    pass

            if isinstance(ctx_or_interaction, discord.Interaction):
                msg = await ctx_or_interaction.followup.send(embed=embed, file=file, view=view)
                view.message = msg
            else:
                msg = await ctx_or_interaction.send(embed=embed, file=file, view=view)
                view.message = msg

            # --- Wishlist Ping ---
            try:
                card_names = [c["name"] for c in cards]
                channel = ctx_or_interaction.channel
                ping_text = await get_wishlist_pings(channel, card_names)
                if ping_text:
                    await channel.send(ping_text)
            except Exception:
                pass
        except Exception as e:
            print(f"Error in execute_card_drop: {e}")
            import traceback
            traceback.print_exc()
            err_msg = f"Coo coo! ⚠️ An error occurred while generating card drop: {e}"
            try:
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(err_msg)
                else:
                    await ctx_or_interaction.send(err_msg)
            except Exception:
                pass

    @app_commands.command(name="drop", description="Drops 3 random Anime Cards from the Supabase card pool")
    async def drop_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.execute_card_drop(interaction, interaction.user)

    @commands.command(name="drop")
    async def drop_prefix(self, ctx):
        await self.execute_card_drop(ctx, ctx.author)

    @commands.command(name="d")
    async def drop_prefix_d(self, ctx):
        await self.execute_card_drop(ctx, ctx.author)

    @commands.command(name="forcedrop", aliases=["fd"])
    async def force_drop_prefix(self, ctx, *, char_name: str = None):
        from config import BOT_OWNER_IDS
        if ctx.author.id not in BOT_OWNER_IDS:
            await ctx.send("Coo coo! ⚠️ This command is restricted to the Bot Owner!")
            return
        await self.execute_card_drop(ctx, ctx.author, forced_character=char_name, bypass_cooldown=True)

    @app_commands.command(name="forcedrop", description="[Owner Only] Force a 3-card drop featuring a specific character")
    @app_commands.default_permissions(administrator=True)
    async def force_drop_slash(self, interaction: discord.Interaction, character: str = None, target: discord.User = None):
        from config import BOT_OWNER_IDS
        if interaction.user.id not in BOT_OWNER_IDS:
            await interaction.response.send_message("Coo coo! ⚠️ Restricted to Bot Owner!", ephemeral=True)
            return
        try:
            await interaction.response.defer()
        except Exception:
            pass
        dest = target or interaction.user
        await self.execute_card_drop(interaction, dest, forced_character=character, bypass_cooldown=True)

async def setup(bot):
    await bot.add_cog(DropCog(bot))
