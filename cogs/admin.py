import discord
from discord.ext import commands

class WinnerView(discord.ui.View):
    def __init__(self, session):
        super().__init__(timeout=None)
        self.session = session

    @discord.ui.button(label="Team 1 Wins", style=discord.ButtonStyle.success)
    async def team1(self, interaction, button):
        await self.finish(interaction, 0)

    @discord.ui.button(label="Team 2 Wins", style=discord.ButtonStyle.success)
    async def team2(self, interaction, button):
        await self.finish(interaction, 1)

    async def finish(self, interaction, winner_index):

        session = self.session.active

        if session["mode"] == "4team":

            round_num = session["round"]
            games = session["fixtures"][round_num]

            game = games[len(session["played"])]
            winner = game[winner_index]

            session["standings"][winner] += 1
            session["played"].append(winner)

            await interaction.response.edit_message(
                content=f"✅ {winner} recorded.",
                view=None
            )

            if len(session["played"]) == 2:

                session["played"] = []

                if session["round"] == 3:

                    await interaction.channel.send(
                        embed=await self.session.standings_embed()
                    )

                    winner = max(
                        session["standings"],
                        key=session["standings"].get
                    )

                    await interaction.channel.send(
                        f"🏆 **{winner} wins the session!**"
                    )

                else:

                    session["round"] += 1

                    await interaction.channel.send(
                        embed=await self.session.standings_embed()
                    )

                    await self.session.post_round(interaction.channel)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="controlpanel",
        description="Open the admin control panel."
    )
    @discord.app_commands.default_permissions(administrator=True)
    async def controlpanel(self, interaction: discord.Interaction):

        session = self.bot.get_cog("Session")

        if not session.active:
            await interaction.response.send_message(
                "No active session.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚙️ Session Control",
            view=WinnerView(session)
        )

async def setup(bot):
    await bot.add_cog(Admin(bot))
