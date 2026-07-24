import time
import discord
from discord.ext import commands
from discord import app_commands
from config import DROP_COOLDOWN_SEC, GRAB_COOLDOWN_SEC, DAILY_COOLDOWN_SEC
from database import get_user_cooldowns, get_effective_cooldowns, is_user_premium, get_user_premium_until

class CooldownsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def process_cooldowns(self, ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        now_ts = int(time.time())
        l_drop, l_grab, l_daily = get_user_cooldowns(user.id)
        drop_cd_sec, grab_cd_sec = get_effective_cooldowns(user.id)

        # Calculate Drop CD
        drop_elapsed = now_ts - l_drop
        if drop_elapsed >= drop_cd_sec:
            drop_status = "✅ **Ready to Drop!** (`/drop` or `!d`)"
        else:
            rem_d = drop_cd_sec - drop_elapsed
            d_m = rem_d // 60
            d_s = rem_d % 60
            drop_status = f"⏳ Ready in **{d_m}m {d_s}s**"

        # Calculate Grab CD
        grab_elapsed = now_ts - l_grab
        if grab_elapsed >= grab_cd_sec:
            grab_status = "✅ **Ready to Grab!**"
        else:
            rem_g = grab_cd_sec - grab_elapsed
            g_m = rem_g // 60
            g_s = rem_g % 60
            grab_status = f"⏳ Ready in **{g_m}m {g_s}s**"

        # Calculate Daily CD (24 hrs)
        daily_elapsed = now_ts - l_daily
        if daily_elapsed >= DAILY_COOLDOWN_SEC:
            daily_status = "✅ **Ready to Claim!** (`/daily` or `!daily`)"
        else:
            rem_day = DAILY_COOLDOWN_SEC - daily_elapsed
            day_h = rem_day // 3600
            day_m = (rem_day % 3600) // 60
            day_s = rem_day % 60
            daily_status = f"⏳ Ready in **{day_h}h {day_m}m {day_s}s**"

        desc = "Below are your current command timers:"
        if is_user_premium(user.id):
            prem_until = get_user_premium_until(user.id)
            rem_days = max(1, (prem_until - now_ts) // 86400)
            desc += f"\n\n👑 **PREMIUM ACTIVE** (Halved Cooldowns active! Expires in {rem_days} days)"

        embed = discord.Embed(
            title=f"⏱️ {user.display_name}'s Command Cooldowns",
            description=desc,
            color=discord.Color.gold() if is_user_premium(user.id) else discord.Color.blue()
        )

        drop_label = "🎴 Card Drop Cooldown (7.5m 👑)" if is_user_premium(user.id) else "🎴 Card Drop Cooldown (15m)"
        grab_label = "🖐️ Card Grab Cooldown (2.5m 👑)" if is_user_premium(user.id) else "🖐️ Card Grab Cooldown (5m)"

        embed.add_field(
            name=drop_label,
            value=drop_status,
            inline=False
        )
        embed.add_field(
            name=grab_label,
            value=grab_status,
            inline=False
        )
        embed.add_field(
            name="🎁 Daily Gems Cooldown (24h)",
            value=daily_status,
            inline=False
        )

        embed.set_footer(text="Coo Coo Timers • Type /shop to buy Premium Pass for 7.5m drops!")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="cd", description="Check your current Drop, Grab, and Daily command cooldowns")
    async def cd_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_cooldowns(interaction)

    @app_commands.command(name="cooldowns", description="Check your current Drop, Grab, and Daily command cooldowns")
    async def cooldowns_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.process_cooldowns(interaction)

    @commands.command(name="cd")
    async def cd_prefix(self, ctx):
        await self.process_cooldowns(ctx)

    @commands.command(name="cooldowns")
    async def cooldowns_prefix(self, ctx):
        await self.process_cooldowns(ctx)

async def setup(bot):
    await bot.add_cog(CooldownsCog(bot))
