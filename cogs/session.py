import discord
from discord.ext import commands
from discord import app_commands

from database.mmr import apply_league_session

ROUND_SCHEDULE = {
    1: [(0, 1), (2, 3)],
    2: [(0, 2), (1, 3)],
    3: [(0, 3), (1, 2)]
}

TEAM_EMOJIS = {
    "Fram Esports": "🔷",
    "Joyboi": "🟣",
    "Warya Wonders": "🟢",
    "The Fifth Pass": "🟡"
}


# ---------------- RESULT BUTTON ----------------

class ResultButton(discord.ui.Button):

    def __init__(self, cog, guild_id, match_index, label, winner, row):
        super().__init__(
            label=f"{label} Wins",
            style=discord.ButtonStyle.danger,
            row=row
        )

        self.cog = cog
        self.guild_id = guild_id
        self.match_index = match_index
        self.winner = winner

    async def callback(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "Admins only.",
                ephemeral=True
            )

        await interaction.response.defer()

        session = self.cog.sessions[self.guild_id]

        if self.match_index in session["submitted"]:
            return

        pairings = ROUND_SCHEDULE[session["round"]]
        teams = list(session["teams"].keys())

        a, b = pairings[self.match_index]

        session["results"].append({
            "round": session["round"],
            "team_a": teams[a],
            "team_b": teams[b],
            "winner": self.winner
        })

        session["submitted"].add(self.match_index)

        # Lock only this match
        for item in self.view.children:
            if isinstance(item, ResultButton) and item.match_index == self.match_index:
                item.disabled = True

                if item.winner == self.winner:
                    item.style = discord.ButtonStyle.success
                else:
                    item.style = discord.ButtonStyle.secondary

        await interaction.edit_original_response(view=self.view)

        await self.cog.update_progress(self.guild_id)

        if len(session["submitted"]) < len(pairings):
            return

        session["submitted"].clear()

        if session["round"] == 3:
            return await self.cog.finish_session(self.guild_id)

        session["round"] += 1

        await session["control_message"].edit(
            content=f"## 🏆 {session['code']} • Round {session['round']}",
            view=SessionControl(self.cog, self.guild_id)
        )

        await self.cog.update_progress(self.guild_id)


# ---------------- SESSION CONTROL ----------------

class SessionControl(discord.ui.View):

    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)

    close_group = app_commands.Group(
        name="close",
        description="Session closing commands."
    )

        # Live fixtures
        if session["round"] <= 3:

            fixtures = ""

            for i, (a, b) in enumerate(
                ROUND_SCHEDULE[session["round"]],
                start=1
            ):

                fixtures += (
                    f"## ⚔️ Match {i}\n"
                value=text if text else "Empty",
                inline=False
            )

        bench = (
            "\n".join(f"• <@{x}>" for x in session["bench"])
            if session["bench"]
            else "No substitutes."
        )

        embed.add_field(
            name=f"🪑 Shared Bench ({len(session['bench'])}/4)",
            value=bench,
            inline=False
        )

        embed.set_footer(
            text="Live updates after every submitted result."
        )

        return embed

    async def update_progress(self, guild_id):

        session = self.sessions[guild_id]

        await session["progress_message"].edit(
            embed=self.build_progress_embed(session)
        )

        for channel in [
            session["progress_channel"],
            session["control_channel"]
        ]:
            try:
                await channel.delete()
            except:
                pass

        try:
    # ---------------- /close session ----------------

    @close_group.command(
        name="session",
        description="Force close the current session."
    )
    @app_commands.default_permissions(administrator=True)
    async def close_session(self, interaction: discord.Interaction):

        if interaction.guild.id not in self.sessions:
            return await interaction.response.send_message(
                "❌ No active session.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        await self.cleanup_session(interaction.guild.id)

        try:
            await interaction.followup.send(
                "🧹 Session closed successfully.",
                ephemeral=True
            )
        except discord.NotFound:
            pass


async def setup(bot):
    cog = Session(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.close_group)
