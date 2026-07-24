import time
import random
import discord
from discord.ext import commands
from discord import app_commands
from database import (
    get_user_cooldowns, set_user_cooldown, get_effective_cooldowns,
    get_user_drop_tickets, add_user_drop_tickets,
    get_user_grab_tickets, add_user_grab_tickets,
    save_card_to_inventory, get_cards_from_db_pool, roll_card_quality
)
from utils.renderer import render_three_cards_composite
from utils.anilist import fetch_random_anilist_cards

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
        if view.claimed:
            await interaction.response.send_message("Coo coo! ⚠️ This drop has already been claimed!", ephemeral=True)
            return

        now_ts = int(time.time())

        # Check Grab Cooldown (5 Minutes, or 2.5 Minutes for Premium)
        l_drop, l_grab, l_daily = get_user_cooldowns(interaction.user.id)
        d_cd, g_cd = get_effective_cooldowns(interaction.user.id)
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

        # Check 30 Seconds Exclusive Priority Window for the Dropper
        elapsed_drop = time.time() - view.drop_time
        if elapsed_drop < 30.0 and interaction.user.id != view.dropper_id:
            rem_prio = int(30.0 - elapsed_drop) + 1
            await interaction.response.send_message(
                f"Coo coo! ⏳ <@{view.dropper_id}> has **30 seconds of exclusive drop priority**! ({rem_prio}s remaining)",
                ephemeral=True
            )
            return

        view.claimed = True
        if not used_grab_ticket:
            set_user_cooldown(interaction.user.id, "grab", now_ts)
        
        for child in view.children:
            child.disabled = True
            if child == self:
                child.label = f"Claimed by {interaction.user.display_name}"
                child.style = discord.ButtonStyle.success

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
            quality=q_val
        )

        embed = discord.Embed(
            title=f"🎉 Claimed: {self.card_info['name']}",
            description=(
                f"👤 **Claimed by:** {interaction.user.mention}\n"
                f"📺 **Series:** {self.card_info['series']}\n"
                f"🌟 **Quality:** {q_val}\n"
                f"🆔 **Card ID:** `{self.card_info['code']}`"
            ),
            color=discord.Color.gold()
        )

        if used_grab_ticket:
            rem_gt = get_user_grab_tickets(interaction.user.id)
            try:
                await interaction.channel.send(
                    f"🖐️ {interaction.user.mention} used an **Extra Grab Ticket**! Grab cooldown bypassed! ({rem_gt} tickets remaining)"
                )
            except Exception:
                pass

        await interaction.response.edit_message(embeds=[embed], view=view)
        await interaction.followup.send(
            f"🎉 {interaction.user.mention} grabbed **{self.card_info['name']}** (**Edition 1 • Print #{self.card_info['temp_mint']} • {q_val}**)! `Card ID: {self.card_info['code']}`"
        )

class CardDropView(discord.ui.View):
    def __init__(self, cards: list, dropper_id: int):
        super().__init__(timeout=300)
        self.cards = cards
        self.dropper_id = dropper_id
        self.drop_time = time.time()
        self.claimed = False
        self.message = None
        for idx, card in enumerate(cards):
            self.add_item(CardGrabButton(idx, card))

    async def on_timeout(self):
        if not self.claimed:
            for child in self.children:
                child.disabled = True
                child.label = "Drop Expired"
                child.style = discord.ButtonStyle.secondary
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass

class DropCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def execute_card_drop(self, ctx_or_interaction, user):
        try:
            now_ts = int(time.time())
            l_drop, l_grab, l_daily = get_user_cooldowns(user.id)
            d_cd, g_cd = get_effective_cooldowns(user.id)
            elapsed_drop = now_ts - l_drop

            used_ticket = False
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

            ticket_text = "🎟️ **Extra Drop Ticket Used!** (Drop Cooldown Bypassed!)\n" if used_ticket else ""

            embed = discord.Embed(
                title=f"🎴 {user.display_name}'s Card Drop!",
                description=(
                    f"1️⃣ **{cards[0]['name']}** · *{cards[0]['series']}*\n"
                    f"2️⃣ **{cards[1]['name']}** · *{cards[1]['series']}*\n"
                    f"3️⃣ **{cards[2]['name']}** · *{cards[2]['series']}*\n\n"
                    f"{ticket_text}"
                    f"⏳ **Priority:** {user.mention} has **30 seconds of exclusive drop priority**!\n"
                    f"Click a button below to grab a card!"
                ),
                color=discord.Color.gold()
            )
            embed.set_image(url="attachment://drop.png")
            embed.set_footer(text="Coo Coo Card Engine • Side-By-Side View")

            view = CardDropView(cards, dropper_id=user.id)

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

    @app_commands.command(name="drop", description="Drops 3 random Anime Cards from your local character DB")
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

async def setup(bot):
    await bot.add_cog(DropCog(bot))
