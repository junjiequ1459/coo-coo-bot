import discord
from discord.ext import commands
from discord import app_commands
from database import (
    get_user_gems, transfer_gems, get_card_by_code_and_owner, transfer_cards_between_users
)

ACTIVE_TRADES = {}  # {channel_id: TradeSession}

class AddCardModal(discord.ui.Modal, title="Offer Card or Gems"):
    input_val = discord.ui.TextInput(
        label="Card ID or Gems Amount",
        placeholder="Enter 6-char Card ID (e.g. 136hma) OR Gems (e.g. 250g or 250gems)",
        min_length=1,
        max_length=15,
        required=True
    )

    def __init__(self, trade_session):
        super().__init__()
        self.trade_session = trade_session

    async def on_submit(self, interaction: discord.Interaction):
        val = self.input_val.value.strip().lower()
        if val.endswith("g") or val.endswith("gems") or val.isdigit():
            clean_num = val.rstrip("gems").rstrip("g").strip()
            if clean_num.isdigit():
                await self.trade_session.set_gems(interaction, int(clean_num))
                return
        await self.trade_session.add_card(interaction, self.input_val.value.strip())

class RemoveCardModal(discord.ui.Modal, title="Remove Card or Reset Gems"):
    input_val = discord.ui.TextInput(
        label="Card ID to Remove (or 'gems' to reset gems)",
        placeholder="Enter Card ID currently in trade or type 'gems'",
        min_length=1,
        max_length=15,
        required=True
    )

    def __init__(self, trade_session):
        super().__init__()
        self.trade_session = trade_session

    async def on_submit(self, interaction: discord.Interaction):
        val = self.input_val.value.strip().lower()
        if val in ["gems", "gem", "g"]:
            await self.trade_session.set_gems(interaction, 0)
            return
        await self.trade_session.remove_card(interaction, self.input_val.value.strip())

class TradeView(discord.ui.View):
    def __init__(self, trade_session):
        super().__init__(timeout=300)
        self.trade_session = trade_session

    @discord.ui.button(label="Offer Card / Gems", style=discord.ButtonStyle.primary, emoji="➕")
    async def offer_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await interaction.response.send_modal(AddCardModal(self.trade_session))

    @discord.ui.button(label="Remove Offer", style=discord.ButtonStyle.secondary, emoji="➖")
    async def remove_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await interaction.response.send_modal(RemoveCardModal(self.trade_session))

    @discord.ui.button(label="Confirm Trade", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await self.trade_session.confirm_user(interaction, interaction.user.id)

    @discord.ui.button(label="Cancel Trade", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await self.trade_session.cancel_trade(interaction, interaction.user)

class TradeSession:
    def __init__(self, channel, p1: discord.User, p2: discord.User):
        self.channel = channel
        self.p1 = p1
        self.p2 = p2
        self.p1_cards = []
        self.p2_cards = []
        self.p1_gems = 0
        self.p2_gems = 0
        self.p1_confirmed = False
        self.p2_confirmed = False
        self.message = None
        self.view = TradeView(self)

    def render_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔄 Active Trade Session",
            description=f"Trading between {self.p1.mention} and {self.p2.mention}",
            color=discord.Color.blue()
        )

        p1_items = []
        if self.p1_gems > 0:
            p1_items.append(f"• 💎 **{self.p1_gems:,} Gems**")
        if self.p1_cards:
            for c in self.p1_cards:
                p1_items.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")

        p1_text = "\n".join(p1_items) if p1_items else "*No items offered yet*"
        p1_status = "✅ **CONFIRMED**" if self.p1_confirmed else "⏳ *Waiting...*"

        p2_items = []
        if self.p2_gems > 0:
            p2_items.append(f"• 💎 **{self.p2_gems:,} Gems**")
        if self.p2_cards:
            for c in self.p2_cards:
                p2_items.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")

        p2_text = "\n".join(p2_items) if p2_items else "*No items offered yet*"
        p2_status = "✅ **CONFIRMED**" if self.p2_confirmed else "⏳ *Waiting...*"

        embed.add_field(
            name=f"👤 {self.p1.display_name}'s Offer ({p1_status})",
            value=p1_text,
            inline=True
        )
        embed.add_field(
            name=f"👤 {self.p2.display_name}'s Offer ({p2_status})",
            value=p2_text,
            inline=True
        )
        embed.set_footer(text="Offer cards/gems via buttons or type !ta <code_or_amountG> in chat!")
        return embed

    async def update_message(self, interaction=None):
        embed = self.render_embed()
        if interaction:
            try:
                await interaction.response.edit_message(embed=embed, view=self.view)
                return
            except Exception:
                pass
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self.view)
            except Exception:
                pass

    async def set_gems(self, interaction_or_ctx, amount: int):
        is_p1 = (interaction_or_ctx.user.id if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.id) == self.p1.id
        user = self.p1 if is_p1 else self.p2

        if amount < 0:
            msg = "Coo coo! ⚠️ Gem offer cannot be negative!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        user_balance = get_user_gems(user.id)
        if amount > user_balance:
            msg = f"Coo coo! ⚠️ You only have **{user_balance:,} 💎 Gems** in your balance!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        if is_p1:
            self.p1_gems = amount
        else:
            self.p2_gems = amount

        self.p1_confirmed = False
        self.p2_confirmed = False

        if isinstance(interaction_or_ctx, discord.Interaction):
            await self.update_message(interaction_or_ctx)
        else:
            await self.update_message()

    async def add_card(self, interaction_or_ctx, code_str: str):
        is_p1 = (interaction_or_ctx.user.id if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.id) == self.p1.id
        user = self.p1 if is_p1 else self.p2
        target_list = self.p1_cards if is_p1 else self.p2_cards

        card_row = get_card_by_code_and_owner(code_str, user.id)
        if not card_row:
            msg = f"Coo coo! ⚠️ Card `{code_str}` is not in your inventory!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        cid, code, uid, char_name, series, rarity, mint_num, edition, tag = card_row
        card_code = code if code else f"c{cid:04d}"

        if any(c["code"] == card_code for c in target_list):
            msg = f"Coo coo! ⚠️ Card `{card_code}` is already in the trade!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        target_list.append({
            "id": cid,
            "code": card_code,
            "character_name": char_name,
            "series_name": series,
            "rarity": rarity
        })

        self.p1_confirmed = False
        self.p2_confirmed = False

        if isinstance(interaction_or_ctx, discord.Interaction):
            await self.update_message(interaction_or_ctx)
        else:
            await self.update_message()

    async def remove_card(self, interaction_or_ctx, code_str: str):
        is_p1 = (interaction_or_ctx.user.id if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.id) == self.p1.id
        target_list = self.p1_cards if is_p1 else self.p2_cards

        code_clean = code_str.lower().strip()
        matching = [c for c in target_list if c["code"].lower() == code_clean]
        if not matching:
            msg = f"Coo coo! ⚠️ Card `{code_str}` is not in your offered trade list!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        target_list.remove(matching[0])

        self.p1_confirmed = False
        self.p2_confirmed = False

        if isinstance(interaction_or_ctx, discord.Interaction):
            await self.update_message(interaction_or_ctx)
        else:
            await self.update_message()

    async def confirm_user(self, interaction_or_ctx, user_id: int):
        if user_id == self.p1.id:
            self.p1_confirmed = True
        elif user_id == self.p2.id:
            self.p2_confirmed = True

        if self.p1_confirmed and self.p2_confirmed:
            p1_codes = [c["code"] for c in self.p1_cards]
            p2_codes = [c["code"] for c in self.p2_cards]

            card_success = transfer_cards_between_users(self.p1.id, p1_codes, self.p2.id, p2_codes)

            gem_success_1 = True
            if self.p1_gems > 0:
                gem_success_1 = transfer_gems(self.p1.id, self.p2.id, self.p1_gems)

            gem_success_2 = True
            if self.p2_gems > 0:
                gem_success_2 = transfer_gems(self.p2.id, self.p1.id, self.p2_gems)

            if card_success and gem_success_1 and gem_success_2:
                p1_rec_items = []
                if self.p2_gems > 0:
                    p1_rec_items.append(f"• 💎 **{self.p2_gems:,} Gems**")
                if self.p2_cards:
                    for c in self.p2_cards:
                        p1_rec_items.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")
                p1_rec_text = "\n".join(p1_rec_items) if p1_rec_items else "*None (Gift)*\n"

                p2_rec_items = []
                if self.p1_gems > 0:
                    p2_rec_items.append(f"• 💎 **{self.p1_gems:,} Gems**")
                if self.p1_cards:
                    for c in self.p1_cards:
                        p2_rec_items.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")
                p2_rec_text = "\n".join(p2_rec_items) if p2_rec_items else "*None (Gift)*\n"

                embed = discord.Embed(
                    title="🎉 Trade Completed Successfully!",
                    description=f"🤝 **{self.p1.mention}** and **{self.p2.mention}** have completed their trade!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name=f"📦 {self.p1.display_name} received:",
                    value=p1_rec_text,
                    inline=False
                )
                embed.add_field(
                    name=f"📦 {self.p2.display_name} received:",
                    value=p2_rec_text,
                    inline=False
                )

                for child in self.view.children:
                    child.disabled = True
                if isinstance(interaction_or_ctx, discord.Interaction):
                    await interaction_or_ctx.response.edit_message(embed=embed, view=self.view)
                else:
                    await self.message.edit(embed=embed, view=self.view)
            else:
                msg = "Coo coo! ⚠️ Database transfer error occurred during trade!"
                if isinstance(interaction_or_ctx, discord.Interaction):
                    await interaction_or_ctx.response.send_message(msg, ephemeral=True)
                else:
                    await interaction_or_ctx.send(msg)

            if self.channel.id in ACTIVE_TRADES:
                del ACTIVE_TRADES[self.channel.id]
        else:
            if isinstance(interaction_or_ctx, discord.Interaction):
                await self.update_message(interaction_or_ctx)
            else:
                await self.update_message()

    async def cancel_trade(self, interaction_or_ctx, user: discord.User):
        embed = discord.Embed(
            title="❌ Trade Cancelled",
            description=f"Trade session was cancelled by {user.mention}.",
            color=discord.Color.red()
        )
        for child in self.view.children:
            child.disabled = True

        if isinstance(interaction_or_ctx, discord.Interaction):
            await interaction_or_ctx.response.edit_message(embed=embed, view=self.view)
        else:
            await self.message.edit(embed=embed, view=self.view)

        if self.channel.id in ACTIVE_TRADES:
            del ACTIVE_TRADES[self.channel.id]

class TradeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def start_trade_session(self, ctx_or_interaction, partner: discord.User):
        author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        channel = ctx_or_interaction.channel

        if partner.bot:
            msg = "Coo coo! ⚠️ You cannot trade with bots!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        if partner.id == author.id:
            msg = "Coo coo! ⚠️ You cannot trade with yourself!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        if channel.id in ACTIVE_TRADES:
            msg = "Coo coo! ⚠️ There is already an active trade session in this channel!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        session = TradeSession(channel, author, partner)
        ACTIVE_TRADES[channel.id] = session

        embed = session.render_embed()

        if isinstance(ctx_or_interaction, discord.Interaction):
            msg = await ctx_or_interaction.followup.send(embed=embed, view=session.view)
            session.message = msg
        else:
            msg = await ctx_or_interaction.send(embed=embed, view=session.view)
            session.message = msg

    @app_commands.command(name="trade", description="Initiates a Karuta-style card/gems trade with another player")
    async def trade_slash(self, interaction: discord.Interaction, partner: discord.User):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.start_trade_session(interaction, partner)

    @commands.command(name="trade")
    async def trade_prefix(self, ctx, partner: discord.User):
        await self.start_trade_session(ctx, partner)

    @commands.command(name="t")
    async def trade_prefix_shortcut(self, ctx, partner: discord.User):
        await self.start_trade_session(ctx, partner)

    @commands.command(name="ta")
    async def trade_add_prefix(self, ctx, code_or_gems: str):
        if ctx.channel.id not in ACTIVE_TRADES:
            await ctx.send("Coo coo! ⚠️ There is no active trade session in this channel!")
            return
        session = ACTIVE_TRADES[ctx.channel.id]
        if ctx.author.id not in [session.p1.id, session.p2.id]:
            await ctx.send("Coo coo! ⚠️ You are not part of the active trade in this channel!")
            return
        
        val = code_or_gems.lower().strip()
        if val.endswith("g") or val.endswith("gems") or val.isdigit():
            clean_num = val.rstrip("gems").rstrip("g").strip()
            if clean_num.isdigit():
                await session.set_gems(ctx, int(clean_num))
                return
        await session.add_card(ctx, code_or_gems)

    @commands.command(name="tr")
    async def trade_remove_prefix(self, ctx, code_or_gems: str):
        if ctx.channel.id not in ACTIVE_TRADES:
            await ctx.send("Coo coo! ⚠️ There is no active trade session in this channel!")
            return
        session = ACTIVE_TRADES[ctx.channel.id]
        if ctx.author.id not in [session.p1.id, session.p2.id]:
            await ctx.send("Coo coo! ⚠️ You are not part of the active trade in this channel!")
            return

        val = code_or_gems.lower().strip()
        if val in ["gems", "gem", "g"]:
            await session.set_gems(ctx, 0)
            return
        await session.remove_card(ctx, code_or_gems)

async def setup(bot):
    await bot.add_cog(TradeCog(bot))
