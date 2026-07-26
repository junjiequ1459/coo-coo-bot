import discord

from config import display_rarity
from db import get_connection, release_connection


class CharacterSearchPaginatorView(discord.ui.View):
    def __init__(self, bot, user: discord.User, search_query: str, print_num_target: int = None):
        super().__init__(timeout=180.0)
        self.bot = bot
        self.user = user
        self.search_query = search_query
        self.print_num_target = print_num_target
        self.current_page = 0
        self.per_page = 5
        self.total_matches = self.count_matches()
        self.max_pages = max(1, (self.total_matches + self.per_page - 1) // self.per_page)
        self.current_matches = []
        self.update_view_items()

    def count_matches(self) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        tokens = [t.strip().lower() for t in self.search_query.split() if t.strip()]
        if not tokens:
            release_connection(conn)
            return 0

        clauses = []
        params = []
        for t in tokens:
            clauses.append("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(character_name), 'ō', 'o'), 'ū', 'u'), 'ā', 'a'), 'ē', 'e'), 'ī', 'i') ILIKE %s")
            params.append(f"%{t}%")

        sql = f"SELECT COUNT(*) FROM cards_pool WHERE {' AND '.join(clauses)}"
        cursor.execute(sql, tuple(params))
        cnt = cursor.fetchone()[0]
        release_connection(conn)
        return cnt

    def fetch_page_matches(self) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        tokens = [t.strip().lower() for t in self.search_query.split() if t.strip()]
        if not tokens:
            release_connection(conn)
            return []

        clauses = []
        params = []
        for t in tokens:
            clauses.append("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(character_name), 'ō', 'o'), 'ū', 'u'), 'ā', 'a'), 'ē', 'e'), 'ī', 'i') ILIKE %s")
            params.append(f"%{t}%")

        offset = self.current_page * self.per_page
        params.extend([self.per_page, offset])
        sql = f"""
        SELECT character_name, series_name, image_url, rarity
        FROM cards_pool
        WHERE {' AND '.join(clauses)}
        ORDER BY length(character_name) ASC, character_name ASC
        LIMIT %s OFFSET %s
        """
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        release_connection(conn)
        return rows

    def update_view_items(self):
        self.clear_items()
        self.current_matches = self.fetch_page_matches()

        # Add selection button for each match on current page (up to 5)
        for idx, match in enumerate(self.current_matches):
            cname, _, _, _ = match
            btn = discord.ui.Button(
                label=f"{idx + 1}. {cname[:22]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"char_sel_{idx}_{self.current_page}"
            )
            btn.callback = self.make_select_callback(match)
            self.add_item(btn)

        # Pagination controls
        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0), custom_id=f"cs_prev_{self.current_page}")
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            ind_btn = discord.ui.Button(label=f"Page {self.current_page + 1}/{self.max_pages}", style=discord.ButtonStyle.secondary, disabled=True, custom_id=f"cs_ind_{self.current_page}")
            self.add_item(ind_btn)

            next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.max_pages - 1), custom_id=f"cs_next_{self.current_page}")
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

    def make_select_callback(self, match_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
                return
            await interaction.response.defer()
            cname, sname, iurl, rval = match_data
            cog = self.bot.get_cog("LookupCog")
            if cog:
                await cog.display_single_character_lookup(interaction, cname, sname, iurl, rval, self.print_num_target)
        return callback

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🔍 Character Search Results: `{self.search_query}`",
            description=f"Found **{self.total_matches}** matching characters in master pool.\nClick a button below to inspect a character!",
            color=discord.Color.purple()
        )

        for idx, match in enumerate(self.current_matches):
            cname, sname, _, rval = match
            embed.add_field(
                name=f"{idx + 1}️⃣ **{cname}**",
                value=f"📺 *{sname}* | {display_rarity(rval)}",
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages} • Showing 5 per page")
        return embed

class SeriesListPaginatorView(discord.ui.View):
    def __init__(self, bot, user: discord.User, series_query: str):
        super().__init__(timeout=180.0)
        self.bot = bot
        self.user = user
        self.series_query = series_query
        self.current_page = 0
        self.per_page = 5
        self.matching_series = self.fetch_all_series()
        self.total_matches = len(self.matching_series)
        self.max_pages = max(1, (self.total_matches + self.per_page - 1) // self.per_page)
        self.current_page_series = []
        self.update_view_items()

    def fetch_all_series(self) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        tokens = [t.strip().lower() for t in self.series_query.split() if t.strip()]
        if not tokens:
            release_connection(conn)
            return []

        clauses = []
        params = []
        for t in tokens:
            clauses.append("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(series_name), 'ō', 'o'), 'ū', 'u'), 'ā', 'a'), 'ē', 'e'), 'ī', 'i') ILIKE %s")
            params.append(f"%{t}%")

        sql = f"SELECT DISTINCT series_name FROM cards_pool WHERE {' AND '.join(clauses)} ORDER BY series_name ASC"
        cursor.execute(sql, tuple(params))
        rows = [r[0] for r in cursor.fetchall()]
        release_connection(conn)
        return rows

    def update_view_items(self):
        self.clear_items()
        start = self.current_page * self.per_page
        end = start + self.per_page
        self.current_page_series = self.matching_series[start:end]

        for idx, sname in enumerate(self.current_page_series):
            btn = discord.ui.Button(
                label=f"{idx + 1}. {sname[:22]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"series_sel_{idx}_{self.current_page}"
            )
            btn.callback = self.make_select_callback(sname)
            self.add_item(btn)

        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0), custom_id=f"sl_prev_{self.current_page}")
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            ind_btn = discord.ui.Button(label=f"Page {self.current_page + 1}/{self.max_pages}", style=discord.ButtonStyle.secondary, disabled=True, custom_id=f"sl_ind_{self.current_page}")
            self.add_item(ind_btn)

            next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.max_pages - 1), custom_id=f"sl_next_{self.current_page}")
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

    def make_select_callback(self, series_name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
                return
            await interaction.response.defer()
            cog = self.bot.get_cog("LookupCog")
            if cog:
                await cog.display_single_series_roster(interaction, series_name)
        return callback

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        conn = get_connection()
        cursor = conn.cursor()

        embed = discord.Embed(
            title=f"📺 Series Search Results: `{self.series_query}`",
            description=f"Found **{self.total_matches}** matching anime series.\nClick a series button below to view its character roster!",
            color=discord.Color.blue()
        )

        for idx, sname in enumerate(self.current_page_series):
            cursor.execute("SELECT COUNT(*) FROM cards_pool WHERE series_name = %s", (sname,))
            char_cnt = cursor.fetchone()[0]

            embed.add_field(
                name=f"{idx + 1}️⃣ **{sname}**",
                value=f"🎴 **{char_cnt} Characters** in Master Pool",
                inline=False
            )

        release_connection(conn)
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages} • Showing 5 series per page")
        return embed

class SeriesCharacterPaginatorView(discord.ui.View):
    def __init__(self, bot, user: discord.User, series_name: str):
        super().__init__(timeout=180.0)
        self.bot = bot
        self.user = user
        self.series_name = series_name
        self.current_page = 0
        self.per_page = 5
        self.total_matches = self.count_matches()
        self.max_pages = max(1, (self.total_matches + self.per_page - 1) // self.per_page)
        self.current_matches = []
        self.update_view_items()

    def count_matches(self) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cards_pool WHERE LOWER(series_name) = LOWER(%s)", (self.series_name,))
        cnt = cursor.fetchone()[0]
        release_connection(conn)
        return cnt

    def fetch_page_matches(self) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        offset = self.current_page * self.per_page
        cursor.execute("""
        SELECT character_name, series_name, image_url, rarity
        FROM cards_pool
        WHERE LOWER(series_name) = LOWER(%s)
        ORDER BY character_name ASC
        LIMIT %s OFFSET %s
        """, (self.series_name, self.per_page, offset))
        rows = cursor.fetchall()
        release_connection(conn)
        return rows

    def update_view_items(self):
        self.clear_items()
        self.current_matches = self.fetch_page_matches()

        for idx, match in enumerate(self.current_matches):
            cname, _, _, _ = match
            btn = discord.ui.Button(
                label=f"{idx + 1}. {cname[:22]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"schar_sel_{idx}_{self.current_page}"
            )
            btn.callback = self.make_select_callback(match)
            self.add_item(btn)

        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0), custom_id=f"sc_prev_{self.current_page}")
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            ind_btn = discord.ui.Button(label=f"Page {self.current_page + 1}/{self.max_pages}", style=discord.ButtonStyle.secondary, disabled=True, custom_id=f"sc_ind_{self.current_page}")
            self.add_item(ind_btn)

            next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.max_pages - 1), custom_id=f"sc_next_{self.current_page}")
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

    def make_select_callback(self, match_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
                return
            await interaction.response.defer()
            cname, sname, iurl, rval = match_data
            cog = self.bot.get_cog("LookupCog")
            if cog:
                await cog.display_single_character_lookup(interaction, cname, sname, iurl, rval)
        return callback

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot control someone else's lookup menu!", ephemeral=True)
            return
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_view_items()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        conn = get_connection()
        cursor = conn.cursor()

        embed = discord.Embed(
            title=f"📺 Series Roster: {self.series_name}",
            description=f"Found **{self.total_matches}** characters in this anime series.\nClick a character button below to inspect circulation details!",
            color=discord.Color.blue()
        )

        for idx, match in enumerate(self.current_matches):
            cname, _, _, rval = match
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE LOWER(character_name) = LOWER(%s)", (cname,))
            claimed_cnt = cursor.fetchone()[0]

            embed.add_field(
                name=f"{idx + 1}️⃣ **{cname}**",
                value=f"✨ **Rarity:** {display_rarity(rval)} | 📊 **Claimed in Circulation:** {claimed_cnt}",
                inline=False
            )

        release_connection(conn)
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages} • Showing 5 characters per page")
        return embed
