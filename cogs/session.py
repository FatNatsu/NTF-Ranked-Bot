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

        # Wait until both matches are submitted
        if len(session["submitted"]) < len(pairings):
            return

        session["submitted"].clear()

        # Finished
        if session["round"] == 3:
            return await self.cog.finish_session(self.guild_id)

        # Next round
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

        session = cog.sessions[guild_id]
        teams = list(session["teams"].keys())

        pairings = ROUND_SCHEDULE[session["round"]]

        for match_index, (a, b) in enumerate(pairings):

            self.add_item(
                ResultButton(
                    cog,
                    guild_id,
                    match_index,
                    teams[a],
                    "A",
                    row=match_index
                )
            )

            self.add_item(
                ResultButton(
                    cog,
                    guild_id,
                    match_index,
                    teams[b],
                    "B",
                    row=match_index
                )
            )


# ---------------- SESSION COG ----------------

class Session(commands.Cog):

    close_group = app_commands.Group(
        name="close",
        description="Session closing commands."
    )

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
            "progress_message": None,
            "control_message": None
        }

        progress_message = await progress_channel.send(
            embed=self.build_progress_embed(self.sessions[guild.id])
        )

        control_message = await control_channel.send(
            f"## 🏆 {session_code} • Round 1",
            view=SessionControl(self, guild.id)
        )

        self.sessions[guild.id]["progress_message"] = progress_message
        self.sessions[guild.id]["control_message"] = control_message

    # ---------------- LIVE EMBED ----------------

    def build_progress_embed(self, session):

        embed = discord.Embed(
            title=f"⚽ {session['code']}",
            description=f"**{session['mode']} • Round {min(session['round'],3)}**",
            colour=0x2EC4FF
        )

        teams = list(session["teams"].keys())

        # Live fixtures
        if session["round"] <= 3:

            fixtures = ""

            for i, (a, b) in enumerate(
                ROUND_SCHEDULE[session["round"]],
                start=1
            ):
                fixtures += (
                    f"## ⚔️ Match {i}\n"
                    f"{TEAM_EMOJIS.get(teams[a],'⚽')} **{teams[a]}**\n"
                    f"**VS**\n"
                    f"{TEAM_EMOJIS.get(teams[b],'⚽')} **{teams[b]}**\n\n"
                )

            embed.add_field(
                name="🎮 LIVE FIXTURES",
                value=fixtures,
                inline=False
            )

        standings = {t: {"W": 0, "L": 0} for t in teams}

        completed = ""

        for result in session["results"]:

            if result["winner"] == "A":
                winner = result["team_a"]
                loser = result["team_b"]
            else:
                winner = result["team_b"]
                loser = result["team_a"]

            standings[winner]["W"] += 1
            standings[loser]["L"] += 1

            completed += (
                f"**Round {result['round']}**\n"
                f"{TEAM_EMOJIS.get(winner,'⚽')} **{winner}** defeated "
                f"{TEAM_EMOJIS.get(loser,'⚽')} {loser}\n\n"
            )

        if completed:
            embed.add_field(
                name="✅ COMPLETED MATCHES",
                value=completed,
                inline=False
            )

        # Team cards
        for team in teams:

            captain = session["teams"][team]["captain"]
            players = session["teams"][team]["players"]

            text = ""

            if captain:
                text += f"👑 <@{captain}>\n"

            for player in players:
                if player != captain:
                    text += f"• <@{player}>\n"

            text += f"\n🏆 **{standings[team]['W']}W-{standings[team]['L']}L**"

            embed.add_field(
                name=f"{TEAM_EMOJIS.get(team,'⚽')} {team} ({len(players)}/6)",
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

    # ---------------- FINISH ----------------

    async def finish_session(self, guild_id):

        session = self.sessions[guild_id]

        changes = await apply_league_session(session)

        standings = {team: 0 for team in session["teams"]}

        for result in session["results"]:
            if result["winner"] == "A":
                standings[result["team_a"]] += 1
            else:
                standings[result["team_b"]] += 1

        ranking = sorted(
            standings.items(),
            key=lambda x: x[1],
            reverse=True
        )

        medals = ["🥇", "🥈", "🥉", "4️⃣"]

        embed = discord.Embed(
            title=f"🏆 {session['code']} Complete",
            colour=0xFFD700
        )

        for i, (team, wins) in enumerate(ranking):

            losses = 3 - wins
            players = session["teams"][team]["players"]

            avg = 0
            if players:
                avg = round(sum(changes[p] for p in players) / len(players))

            embed.add_field(
                name=f"{medals[i]} {TEAM_EMOJIS.get(team,'⚽')} {team}",
                value=f"**{wins}W-{losses}L**\nMMR {avg:+}",
                inline=False
            )

        await session["progress_channel"].send(embed=embed)

        await self.cleanup_session(guild_id)

    # ---------------- CLEANUP ----------------

    async def cleanup_session(self, guild_id):

        session = self.sessions[guild_id]

        for vc in session["voice_channels"]:
            try:
                await vc.delete()
            except:
                pass

        for channel in (
            session["progress_channel"],
            session["control_channel"]
        ):
            try:
                await channel.delete()
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

    # ---------------- COMMANDS ----------------

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
