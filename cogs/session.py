import discord
from discord.ext import commands
from discord import app_commands

from database.mmr import apply_league_session

ROUND_SCHEDULE = {
    1: [(0, 1), (2, 3)],
    2: [(0, 2), (1, 3)],
    3: [(0, 3), (1, 2)]
}


class SessionControl(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        self.build_buttons()

    def build_buttons(self):
        self.clear_items()

        session = self.cog.sessions[self.guild_id]

        if session["round"] > 3:
            return

        teams = list(session["teams"].keys())

        for index, (a, b) in enumerate(ROUND_SCHEDULE[session["round"]]):
            self.add_item(ResultButton(self.cog, self.guild_id, index, teams[a], "A"))
            self.add_item(ResultButton(self.cog, self.guild_id, index, teams[b], "B"))


class ResultButton(discord.ui.Button):
    def __init__(self, cog, guild_id, match_index, label, winner):
        super().__init__(
            label=f"{label} Win",
            style=discord.ButtonStyle.primary
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

        session = self.cog.sessions[self.guild_id]

        if self.match_index in session["submitted"]:
            return await interaction.response.send_message(
                "Winner already submitted.",
                ephemeral=True
            )

        teams = list(session["teams"].keys())
        a, b = ROUND_SCHEDULE[session["round"]][self.match_index]

        session["results"].append({
            "team_a": teams[a],
            "team_b": teams[b],
            "winner": self.winner
        })

        session["submitted"].add(self.match_index)

        if len(session["submitted"]) < len(ROUND_SCHEDULE[session["round"]]):
            return await interaction.response.send_message(
                "Result recorded. Waiting for the other match.",
                ephemeral=True
            )

        session["submitted"].clear()
        session["round"] += 1

        if session["round"] <= 3:

            await interaction.response.edit_message(
                content=f"## Round {session['round']}",
                view=SessionControl(self.cog, self.guild_id)
            )

            await self.cog.update_progress(self.guild_id)

        else:

            await interaction.response.defer()
            await self.cog.finish_session(self.guild_id)


class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    async def register_session(
        self,
        guild,
        session_code,
        mode,
        teams,
        category,
        progress_channel,
        control_channel,
        voice_channels
    ):

        self.sessions[guild.id] = {
            "code": session_code,
            "mode": mode,
            "round": 1,
            "teams": teams,
            "results": [],
            "submitted": set(),
            "category": category,
            "progress_channel": progress_channel,
            "control_channel": control_channel,
            "voice_channels": voice_channels,
            "bench": [],
            "progress_message": None
        }

        embed = self.build_progress_embed(self.sessions[guild.id])

        msg = await progress_channel.send(embed=embed)

        self.sessions[guild.id]["progress_message"] = msg

        await control_channel.send(
            "## Round 1",
            view=SessionControl(self, guild.id)
        )

    def build_progress_embed(self, session):

        embed = discord.Embed(
            title=f"⚽ {session['code']}",
            description=f"**{session['mode']} • Round {min(session['round'],3)}**",
            colour=0x2EC4FF
        )

        standings = {
            team: {"W": 0, "L": 0}
            for team in session["teams"]
        }

        for result in session["results"]:

            if result["winner"] == "A":
                standings[result["team_a"]]["W"] += 1
                standings[result["team_b"]]["L"] += 1
            else:
                standings[result["team_b"]]["W"] += 1
                standings[result["team_a"]]["L"] += 1

        for team in session["teams"]:

            captain = session["teams"][team]["captain"]
            players = session["teams"][team]["players"]

            text = ""

            if captain:
                text += f"👑 <@{captain}>\n"

            for player in players:
                if player != captain:
                    text += f"• <@{player}>\n"

            text += f"\n**Record:** {standings[team]['W']}W-{standings[team]['L']}L"

            embed.add_field(
                name=f"{team} ({len(players)}/6)",
                value=text or "Empty",
                inline=False
            )

        bench_text = (
            "\n".join(f"• <@{p}>" for p in session["bench"])
            if session["bench"]
            else "No substitutes."
        )

        embed.add_field(
            name=f"🪑 Shared Bench ({len(session['bench'])}/4)",
            value=bench_text,
            inline=False
        )

        embed.set_footer(text="Updates automatically every round.")

        return embed

    async def update_progress(self, guild_id):

        session = self.sessions[guild_id]

        embed = self.build_progress_embed(session)

        await session["progress_message"].edit(embed=embed)

    async def finish_session(self, guild_id):

        session = self.sessions[guild_id]

        changes = await apply_league_session(session)

        standings = {
            team: {"W": 0, "L": 0}
            for team in session["teams"]
        }

        for result in session["results"]:
            if result["winner"] == "A":
                standings[result["team_a"]]["W"] += 1
                standings[result["team_b"]]["L"] += 1
            else:
                standings[result["team_b"]]["W"] += 1
                standings[result["team_a"]]["L"] += 1

        ranking = sorted(
            standings.items(),
            key=lambda x: x[1]["W"],
            reverse=True
        )

        medals = ["🥇", "🥈", "🥉", "4️⃣"]

        embed = discord.Embed(
            title=f"🏆 {session['code']} Complete",
            colour=0xFFD700
        )

        for i, (team, record) in enumerate(ranking):

            players = session["teams"][team]["players"]

            avg = (
                round(sum(changes[p] for p in players) / len(players))
                if players else 0
            )

            embed.add_field(
                name=f"{medals[i]} {team}",
                value=f"**{record['W']}W-{record['L']}L**\nMMR {avg:+}",
                inline=False
            )

        await session["progress_channel"].send(embed=embed)

        leaderboard = self.bot.get_cog("Leaderboard")
        if leaderboard:
            await leaderboard.update_leaderboard(session["progress_channel"].guild)

        await self.cleanup_session(guild_id)

    async def cleanup_session(self, guild_id):

        session = self.sessions[guild_id]

        for channel in session["voice_channels"]:
            try:
                await channel.delete()
            except:
                pass

        try:
            await session["progress_channel"].delete()
        except:
            pass

        try:
            await session["control_channel"].delete()
        except:
            pass

        try:
            await session["category"].delete()
        except:
            pass

        queue = self.bot.get_cog("Queue")

        if queue:
            queue.queue.clear()
            queue.queue_open = False
            try:
                await queue.update_queue_message()
            except:
                pass

        del self.sessions[guild_id]

    @app_commands.command(
        name="sessionstatus",
        description="Show the current session."
    )
    async def sessionstatus(self, interaction: discord.Interaction):

        session = self.sessions.get(interaction.guild.id)

        if not session:
            return await interaction.response.send_message(
                "No active session."
            )

        await interaction.response.send_message(
            embed=self.build_progress_embed(session)
        )

    @app_commands.command(
        name="close_session",
        description="Force close the current session (testing)."
    )
    @app_commands.default_permissions(administrator=True)
    async def close_session(self, interaction: discord.Interaction):

        session = self.sessions.get(interaction.guild.id)

        if not session:
            return await interaction.response.send_message(
                "❌ There is no active session.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🧹 Force closing session...",
            ephemeral=True
        )

        await self.cleanup_session(interaction.guild.id)


async def setup(bot):
    await bot.add_cog(Session(bot))
