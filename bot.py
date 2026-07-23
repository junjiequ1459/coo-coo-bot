import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import random
import asyncio
import traceback

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

COLOR_ROLES = [
    {"name": "Cherry Pink", "emoji": "🩷", "hex": 0xFFB6C1},
    {"name": "Lavender", "emoji": "💜", "hex": 0x9370DB},
    {"name": "Sunset Red", "emoji": "🔴", "hex": 0xE60023},
    {"name": "Mint Green", "emoji": "💚", "hex": 0x98FF98},
    {"name": "Sky Blue", "emoji": "🩵", "hex": 0x87CEEB},
    {"name": "Lemon Yellow", "emoji": "💛", "hex": 0xFFFACD},
    {"name": "Peach Coral", "emoji": "🧡", "hex": 0xFF7F50},
    {"name": "Royal Blue", "emoji": "💙", "hex": 0x007AFF},
    {"name": "Pure White", "emoji": "🤍", "hex": 0xFFFFFF},
    {"name": "Midnight", "emoji": "🖤", "hex": 0x36393F},
]

KARUTA_ROLE_INFO = {"name": "Karuta Drop Ping", "emoji": "🎴"}

PIGEON_MESSAGES = [
    "Coo coo! 🍞 Don't let a bad sketch ruin your day. Even a dropped bagel on 5th Ave gets a second chance!",
    "Coo coo! 🎨 You don't need perfection, you just need to start. Look at me — I can't read the room, but I still show up!",
    "Coo coo! 🍟 If someone tells you your goals are too big, tell them you're just aerodynamically blessed like me!",
    "Coo coo! 🗽 Life is tough, but so is NYC sidewalk pizza. Keep chewing and keep creating!",
    "Coo coo! 🌾 Take a break, stretch your wrist, and drink water. You can't draw masterpieces on an empty stomach!",
    "Coo coo! 👔 Wear your bowtie with confidence, even when you're just hunting for breadcrumbs!",
    "Coo coo! ✨ Art block is temporary, but your talent is forever. Go make something cool!",
    "Coo coo! 🥯 They said I couldn't fly over the park bench because I was too fat. I waddled instead. Adapt and conquer!",
    "Coo coo! 💅 Never be afraid to third-wheel your own success!",
    "Coo coo! 🎨 Yuki told me every artist starts with a rough draft. Mine was a pretzel stain on the sidewalk!",
    "Coo coo! 🌟 Ratan told me to reach for the stars. I reached for a French fry instead, but the energy is the same!",
    "Coo coo! 🍕 Keep pushing forward! Every line you draw brings you closer to your dream!"
]

class ColorButton(discord.ui.Button):
    def __init__(self, color_info):
        super().__init__(
            label=f"{color_info['emoji']} {color_info['name']}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"coocoo_color_{color_info['name'].lower().replace(' ', '_')}"
        )
        self.color_info = color_info

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        target_role_name = self.color_info["name"]
        target_role = discord.utils.get(guild.roles, name=target_role_name)

        if not target_role:
            try:
                target_role = await guild.create_role(
                    name=target_role_name,
                    color=discord.Color(self.color_info["hex"]),
                    reason="Coo Coo Color Role Auto-Creation"
                )
            except discord.Forbidden:
                await interaction.followup.send("Coo coo! ⚠️ I don't have 'Manage Roles' permission!", ephemeral=True)
                return
        else:
            try:
                await target_role.edit(color=discord.Color(self.color_info["hex"]))
            except Exception:
                pass

        color_role_names = [c["name"] for c in COLOR_ROLES]
        roles_to_remove = [r for r in member.roles if r.name in color_role_names and r.name != target_role_name]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        if target_role not in member.roles:
            await member.add_roles(target_role)
            await interaction.followup.send(
                f"Coo coo! 🐦 {self.color_info['emoji']} Your name color is now **{target_role_name}**!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"Coo coo! 🐦 You already have **{target_role_name}**!", ephemeral=True)

class KarutaRoleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="🎴 Karuta Drop Ping Role",
            style=discord.ButtonStyle.primary,
            custom_id="coocoo_toggle_karuta_drop_ping"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        role_name = KARUTA_ROLE_INFO["name"]
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            try:
                role = await guild.create_role(name=role_name, color=discord.Color.gold(), reason="Coo Coo Karuta Role Creation")
            except discord.Forbidden:
                await interaction.followup.send("Coo coo! ⚠️ Need 'Manage Roles' permission!", ephemeral=True)
                return

        if role in member.roles:
            await member.remove_roles(role)
            await interaction.followup.send("Coo coo! ❌ Removed **Karuta Drop Ping** role.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.followup.send("Coo coo! ✅ Added **Karuta Drop Ping** role!", ephemeral=True)

class ColorPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for color in COLOR_ROLES:
            self.add_item(ColorButton(color))

class KarutaRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(KarutaRoleButton())

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🐦 Coo Coo is ONLINE as {bot.user.name} ({bot.user.id})!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} Global Commands!")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

    bot.add_view(ColorPickerView())
    bot.add_view(KarutaRoleView())

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general") or discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        embed = discord.Embed(
            title=f"🐦 Coo Coo Welcomes {member.display_name}!",
            description=(
                f"Coo coo! 🍞 Welcome to the nest, {member.mention}!\n\n"
                f"I'm Coo Coo — New York's fattest pigeon and Yuki's friend! "
                f"Head over to `#get-roles` to pick a name color!\n\n"
                f"Here, take a fresh pretzel crust 🥨!"
            ),
            color=discord.Color.from_rgb(255, 182, 193)
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.strip().lower()
    if content_lower in ["k!drop", "k!d", "kd", "kdrop"]:
        await message.channel.send(f"Coo coo! 🍞 30-minute **Karuta Drop** timer set for {message.author.mention}!")
        asyncio.create_task(schedule_reminder(message.channel, message.author, 1800, "Coo coo! 🎴 Your **Karuta Drop (`k!drop`)** is ready again!"))

    await bot.process_commands(message)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"❌ Slash command error: {error}")

# ==========================================
# 🎨 COLOR & MASCOT COMMANDS
# ==========================================

@bot.command(name="setup-colors")
async def setup_colors_prefix(ctx):
    embed = discord.Embed(
        title="🐦 Coo Coo's Color Nest",
        description="Pick a color below to customize your username color in the server!",
        color=discord.Color.from_rgb(138, 158, 167)
    )
    embed.set_footer(text="Coo Coo • Select your favorite vibe!")
    await ctx.send(embed=embed, view=ColorPickerView())

@bot.tree.command(name="setup-colors", description="Spawns the Coo Coo Color Selection Buttons")
async def setup_colors_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    embed = discord.Embed(
        title="🐦 Coo Coo's Color Nest",
        description="Pick a color below to customize your username color in the server!",
        color=discord.Color.from_rgb(138, 158, 167)
    )
    embed.set_footer(text="Coo Coo • Select your favorite vibe!")
    await interaction.followup.send(embed=embed, view=ColorPickerView())

@bot.command(name="coo")
async def coo_prefix(ctx):
    msg = random.choice(PIGEON_MESSAGES)
    await ctx.send(f"🐦 **Coo Coo**: {msg}")

@bot.tree.command(name="coo", description="Coo Coo shares motivational pigeon wisdom!")
async def coo_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    msg = random.choice(PIGEON_MESSAGES)
    await interaction.followup.send(f"🐦 **Coo Coo**: {msg}")

# ==========================================
# 🎴 KARUTA COMMANDS & TIMERS
# ==========================================

async def schedule_reminder(channel, user, seconds: int, message: str):
    await asyncio.sleep(seconds)
    try:
        await channel.send(f"⏰ {user.mention} {message}")
    except Exception as e:
        print(f"Reminder error: {e}")

@bot.tree.command(name="kdrop", description="Sets a 30-minute Karuta Drop timer")
async def kdrop_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await interaction.followup.send(f"Coo coo! 🍞 30-minute **Karuta Drop** timer set for {interaction.user.mention}!")
    asyncio.create_task(schedule_reminder(interaction.channel, interaction.user, 1800, "Coo coo! 🎴 Your **Karuta Drop (`k!drop`)** is ready again!"))

@bot.command(name="kdrop")
async def kdrop_prefix(ctx):
    await ctx.send(f"Coo coo! 🍞 30-minute **Karuta Drop** timer set for {ctx.author.mention}!")
    asyncio.create_task(schedule_reminder(ctx.channel, ctx.author, 1800, "Coo coo! 🎴 Your **Karuta Drop (`k!drop`)** is ready again!"))

@bot.tree.command(name="kgrab", description="Sets a 10-minute Karuta Grab timer")
async def kgrab_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await interaction.followup.send(f"Coo coo! 🎴 10-minute **Karuta Grab** timer set for {interaction.user.mention}!")
    asyncio.create_task(schedule_reminder(interaction.channel, interaction.user, 600, "Coo coo! ⚡ Your **Karuta Grab (`k!grab`)** is ready!"))

@bot.command(name="kgrab")
async def kgrab_prefix(ctx):
    await ctx.send(f"Coo coo! 🎴 10-minute **Karuta Grab** timer set for {ctx.author.mention}!")
    asyncio.create_task(schedule_reminder(ctx.channel, ctx.author, 600, "Coo coo! ⚡ Your **Karuta Grab (`k!grab`)** is ready!"))

@bot.tree.command(name="kwork", description="Sets a 14-hour Karuta Work timer")
async def kwork_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await interaction.followup.send(f"Coo coo! 🛠️ 14-hour **Karuta Work** timer set for {interaction.user.mention}!")
    asyncio.create_task(schedule_reminder(interaction.channel, interaction.user, 50400, "Coo coo! 🛠️ Your **Karuta Work (`k!work`)** shift is ready!"))

@bot.command(name="kwork")
async def kwork_prefix(ctx):
    await ctx.send(f"Coo coo! 🛠️ 14-hour **Karuta Work** timer set for {ctx.author.mention}!")
    asyncio.create_task(schedule_reminder(ctx.channel, ctx.author, 50400, "Coo coo! 🛠️ Your **Karuta Work (`k!work`)** shift is ready!"))

@bot.tree.command(name="kdaily", description="Sets a 24-hour Karuta Daily timer")
async def kdaily_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await interaction.followup.send(f"Coo coo! 🌟 24-hour **Karuta Daily** timer set for {interaction.user.mention}!")
    asyncio.create_task(schedule_reminder(interaction.channel, interaction.user, 86400, "Coo coo! 🌟 Your **Karuta Daily (`k!vote`)** is ready!"))

@bot.command(name="kdaily")
async def kdaily_prefix(ctx):
    await ctx.send(f"Coo coo! 🌟 24-hour **Karuta Daily** timer set for {ctx.author.mention}!")
    asyncio.create_task(schedule_reminder(ctx.channel, ctx.author, 86400, "Coo coo! 🌟 Your **Karuta Daily (`k!vote`)** is ready!"))

@bot.tree.command(name="karuta-help", description="Displays Karuta commands & guide")
async def karuta_help_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    embed = discord.Embed(
        title="🎴 Coo Coo's Karuta Cheat Sheet",
        description="Here are essential Karuta commands & Coo Coo timer triggers!",
        color=discord.Color.gold()
    )
    embed.add_field(name="🎴 Core Karuta Commands", value=(
        "`k!d` (or `k!drop`) - Drop 3 cards\n"
        "`k!g <1-3>` - Grab a dropped card\n"
        "`k!i` - View your inventory & cards\n"
        "`k!w` - Work your job for gold & items\n"
        "`k!v` - Daily vote for rewards\n"
        "`k!lu <name>` - Lookup a character card"
    ), inline=False)
    embed.add_field(name="⏰ Coo Coo Cooldown Timers", value=(
        "`/kdrop` (or typing `k!drop`) - Set 30-min drop reminder\n"
        "`/kgrab` - Set 10-min grab reminder\n"
        "`/kwork` - Set 14-hr work reminder\n"
        "`/kdaily` - Set 24-hr daily vote reminder"
    ), inline=False)
    embed.set_footer(text="Coo Coo • Official Karuta Assistant")
    await interaction.followup.send(embed=embed)

@bot.command(name="karuta-help")
async def karuta_help_prefix(ctx):
    embed = discord.Embed(
        title="🎴 Coo Coo's Karuta Cheat Sheet",
        description="Here are essential Karuta commands & Coo Coo timer triggers!",
        color=discord.Color.gold()
    )
    embed.add_field(name="🎴 Core Karuta Commands", value=(
        "`k!d` (or `k!drop`) - Drop 3 cards\n"
        "`k!g <1-3>` - Grab a dropped card\n"
        "`k!i` - View your inventory & cards\n"
        "`k!w` - Work your job for gold & items\n"
        "`k!v` - Daily vote for rewards\n"
        "`k!lu <name>` - Lookup a character card"
    ), inline=False)
    embed.add_field(name="⏰ Coo Coo Cooldown Timers", value=(
        "`!kdrop` (or typing `k!drop`) - Set 30-min drop reminder\n"
        "`!kgrab` - Set 10-min grab reminder\n"
        "`!kwork` - Set 14-hr work reminder\n"
        "`!kdaily` - Set 24-hr daily vote reminder"
    ), inline=False)
    embed.set_footer(text="Coo Coo • Official Karuta Assistant")
    await ctx.send(embed=embed)

@bot.tree.command(name="karuta-role", description="Spawns the Karuta Drop Ping Role Button")
async def karuta_role_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    embed = discord.Embed(
        title="🎴 Karuta Drop Notifications",
        description="Click the button below to toggle the **@Karuta Drop Ping** role and get notified whenever cards are dropped!",
        color=discord.Color.gold()
    )
    await interaction.followup.send(embed=embed, view=KarutaRoleView())

@bot.command(name="karuta-role")
async def karuta_role_prefix(ctx):
    embed = discord.Embed(
        title="🎴 Karuta Drop Notifications",
        description="Click the button below to toggle the **@Karuta Drop Ping** role and get notified whenever cards are dropped!",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=KarutaRoleView())

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Error: Please put your Discord Bot Token in the .env file!")
    else:
        bot.run(TOKEN)
