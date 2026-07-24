import os
import asyncio
import aiohttp
from aiohttp import web
import discord
from discord.ext import commands
from config import TOKEN
from cogs.utilities import ColorPickerView

# ==========================================
# 🤖 BOT DISCORD CLIENT SETUP & HEALTHCHECK
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None, case_insensitive=True)

async def handle_healthcheck(request):
    return web.Response(text="Coo Coo Bot is Healthy and Online 24/7! 🐦🎴")

async def start_healthcheck_server():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    app.router.add_get("/health", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Railway HTTP Healthcheck Server active on port {port}!")

@bot.event
async def on_ready():
    print(f"🐦 Coo Coo is ONLINE as {bot.user.name} ({bot.user.id})!")
    bot.loop.create_task(start_healthcheck_server())
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} Global Slash Commands to Discord!")
    except Exception as e:
        print(f"Global tree sync error: {e}")

    bot.add_view(ColorPickerView())

async def main():
    async with bot:
        cogs = [
            "cogs.drop",
            "cogs.inventory",
            "cogs.economy",
            "cogs.shop",
            "cogs.trade",
            "cogs.cooldowns",
            "cogs.utilities",
            "cogs.admin"
        ]
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f"✅ Loaded cog: {cog}")
            except Exception as e:
                print(f"❌ Failed to load cog {cog}: {e}")
                
        await bot.start(TOKEN)

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Error: Please put your Discord Bot Token in the .env file!")
    else:
        asyncio.run(main())
