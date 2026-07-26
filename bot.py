import os
import asyncio
from aiohttp import web
import discord
from discord.ext import commands
from discord import app_commands
from config import TOKEN
from cogs.views.colors import ColorPickerView

# ==========================================
# 🤖 BOT DISCORD CLIENT SETUP & HEALTHCHECK
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

async def get_prefix(bot, message):
    prefixes = ["!"]
    message_words = message.content.lstrip().split(maxsplit=1)
    command_word = message_words[0] if message_words else ""
    if 0 < len(command_word) <= 3:
        prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot, message)

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None, case_insensitive=True)
commands_synced = False
healthcheck_task = None
persistent_views_registered = False

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
    global commands_synced, healthcheck_task, persistent_views_registered
    print(f"🐦 Coo Coo is ONLINE as {bot.user.name} ({bot.user.id})!")

    if healthcheck_task is None:
        healthcheck_task = asyncio.create_task(start_healthcheck_server())

    if not persistent_views_registered:
        bot.add_view(ColorPickerView())
        persistent_views_registered = True

    if commands_synced:
        return
    
    # 1. Clear duplicate guild-level overrides from all servers
    for guild in bot.guilds:
        try:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"🧹 Purged duplicate guild commands for '{guild.name}'!")
        except Exception as e:
            print(f"Guild purge error for {guild.name}: {e}")

    # 2. Sync single clean global tree (prevents duplicate command listings)
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} Global Slash Commands to Discord (Zero Duplicates)!")
        commands_synced = True
    except Exception as e:
        print(f"Global tree sync error: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    ctx = await bot.get_context(message)
    if ctx.command is not None:
        # Block "i" from triggering inventory when it's part of a sentence
        # e.g. "i want to play" should NOT open inventory
        if ctx.prefix == "" and ctx.invoked_with.lower() == "i":
            if message.content.strip().lower() != "i":
                return

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Coo coo! ⚠️ Missing required argument! Usage: `{ctx.prefix}{ctx.command.signature}`")
        return
    print(f"Error in prefix command '{ctx.command}': {error}")
    import traceback
    traceback.print_exc()
    await ctx.send(f"Coo coo! ⚠️ An error occurred: `{error}`")

async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"Error in slash command '{interaction.command}': {error}")
    import traceback
    traceback.print_exc()
    msg = f"Coo coo! ⚠️ An error occurred: `{error}`"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

bot.tree.on_error = on_tree_error

async def main():
    async with bot:
        cogs = [
            "cogs.drop",
            "cogs.inventory",
            "cogs.card_actions",
            "cogs.lookup",
            "cogs.wishlist",
            "cogs.favorites",
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
