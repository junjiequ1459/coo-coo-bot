import time
import discord
from discord.ext import commands
from discord import app_commands
from config import DAILY_COOLDOWN_SEC
from database import (
    get_user_gems, get_user_dust, add_user_gems,
    get_user_cooldowns, set_user_cooldown, transfer_gems
)

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def process_balance(self, ctx_or_interaction):
        target = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        gems = get_user_gems(target.id)

        embed = discord.Embed(
            title=f"💎 {target.display_name}'s Gem Pouch",
            description=f"Current Balance: **{gems:,} Gems 💎**",
            color=discord.Color.from_rgb(0, 229, 255)
        )
        embed.set_footer(text="Type !daily or /daily to claim 500 free Gems every 24 hours!")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            try:
                await ctx_or_interaction.author.send(embed=embed)
                await ctx_or_interaction.message.reply("Coo coo! 📩 Sent your Gem balance to your DMs so it stays private!", delete_after=5)
            except Exception:
                await ctx_or_interaction.send(embed=embed)

    async def process_daily(self, ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        now_ts = int(time.time())

        l_drop, l_grab, last_daily = get_user_cooldowns(user.id)
        elapsed = now_ts - last_daily

        if elapsed < DAILY_COOLDOWN_SEC:
            remaining = DAILY_COOLDOWN_SEC - elapsed
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60

            msg = f"Coo coo! ⏳ You have already claimed your daily Gems! Return in **{hours}h {minutes}m {seconds}s**! Type `!cd` to view your cooldowns."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        reward = 500
        current_gems = get_user_gems(user.id)
        new_gems = current_gems + reward
        
        add_user_gems(user.id, reward)
        set_user_cooldown(user.id, "daily", now_ts)

        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=(
                f"Coo coo! 🐦 {user.mention} claimed **+500 💎 Gems**!\n\n"
                f"⏰ Next Daily available in **24 hours**!"
            ),
            color=discord.Color.green()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_pay(self, ctx_or_interaction, target: discord.User, amount: int):
        sender = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

        if target.bot:
            msg = "Coo coo! ⚠️ You cannot send Gems to bots!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        if target.id == sender.id:
            msg = "Coo coo! ⚠️ You cannot pay Gems to yourself!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        if amount <= 0:
            msg = "Coo coo! ⚠️ Amount must be greater than 0 Gems!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        success = transfer_gems(sender.id, target.id, amount)
        if success:
            embed = discord.Embed(
                title="💸 Gems Transferred!",
                description=f"Successfully sent **{amount:,} 💎 Gems** to {target.mention}!",
                color=discord.Color.gold()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
        else:
            sender_gems = get_user_gems(sender.id)
            msg = f"Coo coo! ⚠️ You don't have enough Gems! You only have **{sender_gems:,} 💎**!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)

    async def process_dust_balance(self, ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        dust = get_user_dust(user.id)

        embed = discord.Embed(
            title=f"🧪 {user.display_name}'s Dust Flask",
            description=f"Current Balance: **{dust:,} Dust 🧪**",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Burn duplicate or unwanted cards with !burn <card_id> to generate Dust!")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def process_admin_givegems(self, ctx_or_interaction, target: discord.User, amount: int):
        sender = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        from config import BOT_OWNER_IDS
        if sender.id not in BOT_OWNER_IDS:
            msg = "Coo coo! ⚠️ This command is restricted to the Bot Owner!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        new_bal = add_user_gems(target.id, amount)
        embed = discord.Embed(
            title="👑 Admin Gem Grant",
            description=(
                f"🎉 **{sender.mention}** granted **{amount:,} 💎 Gems** to {target.mention}!\n\n"
                f"💎 **New Balance:** **{new_bal:,} Gems 💎**"
            ),
            color=discord.Color.gold()
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    # --- COMMAND HANDLERS ---
    @app_commands.command(name="givegems", description="[Owner Only] Grant Gems directly to any user")
    async def givegems_slash(self, interaction: discord.Interaction, target: discord.User, amount: int):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_admin_givegems(interaction, target, amount)

    @commands.command(name="givegems")
    async def givegems_prefix(self, ctx, target: discord.User, amount: int):
        await self.process_admin_givegems(ctx, target, amount)

    @commands.command(name="addgems")
    async def addgems_prefix(self, ctx, target: discord.User, amount: int):
        await self.process_admin_givegems(ctx, target, amount)

    @app_commands.command(name="bal", description="Check your private personal Gems balance")
    async def bal_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        await self.process_balance(interaction)

    @app_commands.command(name="balance", description="Check your private personal Gems balance")
    async def balance_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        await self.process_balance(interaction)

    @commands.command(name="balance")
    async def balance_prefix(self, ctx):
        await self.process_balance(ctx)

    @commands.command(name="bal")
    async def balance_prefix_bal(self, ctx):
        await self.process_balance(ctx)

    @commands.command(name="gems")
    async def balance_prefix_gems(self, ctx):
        await self.process_balance(ctx)

    @app_commands.command(name="daily", description="Claim your daily 500 Gems reward (Available every 24 hours)")
    async def daily_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_daily(interaction)

    @commands.command(name="daily")
    async def daily_prefix(self, ctx):
        await self.process_daily(ctx)

    @app_commands.command(name="pay", description="Transfer Gems directly to another player")
    async def pay_slash(self, interaction: discord.Interaction, target: discord.User, amount: int):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_pay(interaction, target, amount)

    @commands.command(name="pay")
    async def pay_prefix(self, ctx, target: discord.User, amount: int):
        await self.process_pay(ctx, target, amount)

    @commands.command(name="give")
    async def pay_prefix_give(self, ctx, target: discord.User, amount: int):
        await self.process_pay(ctx, target, amount)

    @app_commands.command(name="dust", description="Check your current Dust flask balance")
    async def dust_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_dust_balance(interaction)

    @commands.command(name="dust")
    async def dust_prefix(self, ctx):
        await self.process_dust_balance(ctx)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
