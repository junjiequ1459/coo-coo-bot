import discord


COLLECTION_RARITY_GEMS = {
    "Mythic": "✶",
    "Legendary": "⬢",
    "Epic": "⬢",
    "Rare": "⬢",
    "Common": "⬢",
}


def display_collection_rarity(rarity: str) -> str:
    gem = COLLECTION_RARITY_GEMS.get(rarity, "⬢")
    return f"{gem} {rarity}"


class CollectionPaginatorView(discord.ui.View):
    def __init__(
        self,
        user: discord.User,
        rows: list,
        tag_filter: str | None = None,
    ):
        super().__init__(timeout=180.0)
        self.user = user
        self.rows = rows
        self.tag_filter = tag_filter
        self.current_page = 0
        self.per_page = 10
        self.max_pages = max(
            1,
            (len(rows) + self.per_page - 1) // self.per_page,
        )
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.max_pages - 1
        self.page_indicator.label = (
            f"Page {self.current_page + 1}/{self.max_pages}"
        )

    def build_embed(self) -> discord.Embed:
        title_suffix = (
            f" (Tag: [{self.tag_filter}])"
            if self.tag_filter
            else ""
        )
        embed = discord.Embed(
            title=(
                f"🎴 {self.user.display_name}'s Card Collection"
                f"{title_suffix}"
            ),
            description=f"Total Cards: **{len(self.rows)}**",
            color=discord.Color.purple(),
        )

        start_index = self.current_page * self.per_page
        page_rows = self.rows[start_index:start_index + self.per_page]

        for row in page_rows:
            if len(row) >= 10:
                (
                    card_id,
                    code,
                    character_name,
                    series,
                    rarity,
                    mint_number,
                    edition,
                    _,
                    tag,
                    quality,
                ) = row[:10]
            else:
                (
                    card_id,
                    code,
                    character_name,
                    series,
                    rarity,
                    mint_number,
                    edition,
                    _,
                    tag,
                ) = row
                quality = "Good ⭐⭐"

            card_code = code or f"c{card_id:04d}"
            edition = edition or 1
            tag_display = f" 🏷️ `[{tag}]`" if tag else ""
            embed.add_field(
                name=(
                    f"🆔 Card ID: `{card_code}` • "
                    f"{character_name}{tag_display}"
                ),
                value=(
                    f"Edition {edition} • Print #{mint_number} | {quality}\n"
                    f"📺 *{series}* | {display_collection_rarity(rarity)}"
                ),
                inline=False,
            )

        embed.set_footer(
            text=(
                f"Page {self.current_page + 1} of {self.max_pages} • "
                "Type /card code:<code> to see full card artwork!"
            )
        )
        return embed

    @discord.ui.button(
        label="◀️ Prev",
        style=discord.ButtonStyle.secondary,
        custom_id="coll_prev_btn",
    )
    async def prev_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "Coo coo! ⚠️ You cannot control someone else's menu!",
                ephemeral=True,
            )
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self,
            )

    @discord.ui.button(
        label="Page 1/1",
        style=discord.ButtonStyle.primary,
        disabled=True,
        custom_id="coll_page_ind",
    )
    async def page_indicator(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        pass

    @discord.ui.button(
        label="Next ▶️",
        style=discord.ButtonStyle.secondary,
        custom_id="coll_next_btn",
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "Coo coo! ⚠️ You cannot control someone else's menu!",
                ephemeral=True,
            )
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self,
            )
