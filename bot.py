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

class ColorPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for color in COLOR_ROLES:
            self.add_item(ColorButton(color))

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

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"❌ Slash command error: {error}")

# ==========================================
# 📜 PREFIX & SLASH COMMANDS
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

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Error: Please put your Discord Bot Token in the .env file!")
    else:
        bot.run(TOKEN)
