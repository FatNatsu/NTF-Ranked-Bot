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
        self.refresh_buttons()

    def refresh_buttons(self):
        self.clear_items()

        session = self.cog.sessions[self.guild_id]

        if session["round"] > 3:
            return

        pairings = ROUND_SCHEDULE[session["round"]]
        teams = list(session["teams"].keys())

        for match_index, (a, b) in enumerate(pairings):
            team_a = teams[a]
            team_b = teams[b]

            self.add_item(ResultButton(self.cog, self.guild_id, match_index, team_a, "A"))
            self.add_item(ResultButton(self.cog, self.guild_id, match_index, team_b, "B"))


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
            await interaction.response.send_message(
                "Admins only.",
                ephemeral=True
            )
            return

        session = self.cog.sessions[self.guild_id]

        if self.match_index in session["submitted"]:
            await interaction.response.send_message(
                "Winner already submitted.",
                ephemeral=True
            )
            return

        pairings = ROUND_SCHEDULE[session["round"]]
        teams = list(session["teams"].keys())

        a, b = pairings[self.match_index]

        session["results"].append({
            "team_a": teams[a],
            "team_b": teams[b],
            "winner": self.winner
        })

        session["submitted"].add(self.match_index)

        await interaction.response.defer()

        if len(session["submitted"]) == 2:

            session["submitted"].clear()
            session["round"] += 1

            if session["round"] <= 3:

                self.view.refresh_buttons()

                await interaction.message.edit(
                    content=f"**Round {session['round']}**",
                    view=self.view
                )

                await self.cog.update_progress(self.guild_id)

            else:

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
            "progress_message": None
        }

        await self.create_progress(guild.id)

        view = SessionControl(self, guild.id)

        await control_channel.send(
            content="**Round 1**",
            view=view
        )

    async def create_progress(self, guild_id):

        session = self.sessions[guild_id]

        embed = self.build_progress_embed(session)

        message = await session["progress_channel"].send(embed=embed)

        session["progress_message"] = message

    async def update_progress(self, guild_id):

        session = self.sessions[guild_id]

        embed = self.build_progress_embed(session)

        await session["progress_message"].edit(embed=embed)

    def build_progress_embed(self, session):

        embed = discord.Embed(
            title=f"⚽ {session['code']}",
            description=f"**{session['mode']} • Round {min(session['round'],3)}**",
            colour=0x2EC4FF
        )

        standings = {}

        for team in session["teams"]:
            standings[team] = {"W": 0, "L": 0}

        for result in session["results"]:

            if result["winner"] == "A":
                standings[result["team_a"]]["W"] += 1
                standings[result["team_b"]]["L"] += 1
            else:
                standings[result["team_b"]]["W"] += 1
                standings[result["team_a"]]["L"] += 1

        for team, data in standings.items():

            players = session["teams"][team]["players"]
            captain = session["teams"][team]["captain"]

            text = f"👑 <@{captain}>\n"

            for player in players:
                if player != captain:
                    text += f"• <@{player}>\n"

            text += f"\n**Record:** {data['W']}W-{data['L']}L"

            embed.add_field(
                name=f"{team} ({len(players)}/6)",
                value=text,
                inline=False
            )

        embed.add_field(
            name="🪑 Shared Bench",
            value=f"{len(session.get('bench', []))}/4 Players",
            inline=False
        )

        return embed

    async def finish_session(self, guild_id):

        session = self.sessions[guild_id]

        # -------------------------
        # Apply MMR
        # -------------------------

        changes = await apply_league_session(session)

        # -------------------------
        # Final standings
        # -------------------------

        standings = {}

        for team in session["teams"]:
            standings[team] = {"W": 0, "L": 0}

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

        embed = discord.Embed(
            title=f"🏆 {session['code']} Complete",
            description="Final Standings",
            colour=0xFFD700
        )

        medals = ["🥇", "🥈", "🥉", "4️⃣"]

        for i, (team, record) in enumerate(ranking):

            players = session["teams"][team]["players"]

            avg_change = round(
                sum(changes[p] for p in players) / len(players)
            )

            embed.add_field(
                name=f"{medals[i]} {team}",
                value=f"**{record['W']}W-{record['L']}L**\nMMR: {avg_change:+}",
                inline=False
            )

        await session["progress_channel"].send(embed=embed)

        # -------------------------
        # Cleanup
        # -------------------------

        for vc in session["voice_channels"]:
            try:
                await vc.delete()
            except:
                pass

        try:
            await session["category"].delete()
        except:
            pass

        # -------------------------
        # Reopen Queue
        # -------------------------

        queue_cog = self.bot.get_cog("Queue")

        if queue_cog:
            queue_cog.queue.clear()
            queue_cog.queue_open = False

        del self.sessions[guild_id]

    @app_commands.command(
        name="sessionstatus",
        description="Show current session status."
    )
    async def sessionstatus(self, interaction: discord.Interaction):

        session = self.sessions.get(interaction.guild.id)

        if not session:
            await interaction.response.send_message(
                "No active session."
            )
            return

        await interaction.response.send_message(
            embed=self.build_progress_embed(session)
        )


async def setup(bot):
    await bot.add_cog(Session(bot))
