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
        # Wait until both matches are finished
        if len(session["submitted"]) < len(pairings):
            return

        session["submitted"].clear()

        # Session finished
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
# ---------------- SESSION COG ----------------
    # ---------------- LIVE EMBED ----------------

    def build_progress_embed(self, session):

        embed = discord.Embed(
            title=f"⚽ {session['code']}",
            description=f"**{session['mode']} • Round {min(session['round'],3)}**",
            colour=0x2EC4FF
        )

        teams = list(session["teams"].keys())

        # Live Fixtures
        if session["round"] <= 3:

            fixtures = ""

            for i, (a, b) in enumerate(
                ROUND_SCHEDULE[session["round"]],
                start=1
            ):

                fixtures += (
                    f"**⚔️ Match {i}**\n"
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
                value=text or "Empty",
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

    @app_commands.command(
        name="close_session",
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
    await bot.add_cog(Session(bot))
