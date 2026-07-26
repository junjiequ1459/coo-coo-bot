import time

import discord

from config import COLOR_ROLES, LEGACY_COLOR_ROLES


COLOR_BUTTON_COOLDOWNS = {}
COOLDOWN_DURATION_SEC = 5


class ColorButton(discord.ui.Button):
    def __init__(self, color_info):
        button_label = color_info.get("label", color_info["name"])
        super().__init__(
            label=button_label,
            style=discord.ButtonStyle.secondary,
            custom_id=(
                "coocoo_color_"
                f"{color_info['name'].lower().replace(' ', '_')}"
            ),
        )
        self.color_info = color_info

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        now = time.time()
        last_press = COLOR_BUTTON_COOLDOWNS.get(member.id, 0)
        remaining = COOLDOWN_DURATION_SEC - (now - last_press)

        if remaining > 0:
            await interaction.followup.send(
                "Coo coo! ⏳ Rate limit active! Please wait "
                f"**{int(remaining) + 1}s** before changing your color again!",
                ephemeral=True,
            )
            return

        COLOR_BUTTON_COOLDOWNS[member.id] = now

        target_role_name = self.color_info["name"]
        target_role = discord.utils.get(guild.roles, name=target_role_name)

        if not target_role:
            try:
                target_role = await guild.create_role(
                    name=target_role_name,
                    color=discord.Color(self.color_info["hex"]),
                    hoist=True,
                    reason="Coo Coo Color Role Auto-Creation",
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "Coo coo! ⚠️ I don't have 'Manage Roles' permission!",
                    ephemeral=True,
                )
                return
        else:
            try:
                await target_role.edit(
                    color=discord.Color(self.color_info["hex"]),
                    hoist=True,
                )
            except Exception:
                pass

        color_role_names = [
            color["name"] for color in COLOR_ROLES
        ] + LEGACY_COLOR_ROLES
        roles_to_remove = [
            role
            for role in member.roles
            if role.name in color_role_names and role.name != target_role_name
        ]
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove)
            except discord.Forbidden:
                pass

        if target_role in member.roles:
            await interaction.followup.send(
                f"Coo coo! 🐦 You already have **{target_role_name}**!",
                ephemeral=True,
            )
            return

        try:
            await member.add_roles(target_role)
            color_description = self.color_info.get("color_desc", "")
            description = (
                f" ({color_description})"
                if color_description
                else ""
            )
            await interaction.followup.send(
                "Coo coo! 🐦 Your name color is now "
                f"**{target_role_name}**{description}!",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Coo coo! ⚠️ I cannot assign this role. Please ensure my "
                "**Coo Coo Bot** role is dragged **ABOVE** the color roles "
                "in Server Settings -> Roles!",
                ephemeral=True,
            )
        except Exception as error:
            await interaction.followup.send(
                f"Coo coo! ⚠️ Could not assign role: {error}",
                ephemeral=True,
            )


class ColorPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for color in COLOR_ROLES:
            self.add_item(ColorButton(color))
