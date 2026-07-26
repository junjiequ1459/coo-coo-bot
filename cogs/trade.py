import discord
from discord.ext import commands
from discord import app_commands
from cogs.views.trade import ACTIVE_TRADES, TradeSession

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
