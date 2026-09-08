import discord
from discord.ext import commands

class MatchView(discord.ui.View):
    def __init__(self, session_cog):
        super().__init__(timeout=None)
        self.session = session_cog

        self.refresh_buttons()

    def refresh_buttons(self):
        self.clear_items()

        if not self.session.active:
            return

        games = self.session.current_games()

        for team_a, team_b in games:

            self.add_item(WinnerButton(self.session, team_a))
            self.add_item(WinnerButton(self.session, team_b))

class WinnerButton(discord.ui.Button):
    def __init__(self, session, team):

        super().__init__(
            label=f"{team} Wins",
            style=discord.ButtonStyle.success
        )

        self.session = session
        self.team = team

    async def callback(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Admins only.",
                ephemeral=True
            )
            return

        self.session.record_win(self.team)

        await self.session.update_live_hub()

        await interaction.response.defer()


class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.active = None
        self.live_message = None
        self.live_channel = None

    def create(self, teams):

        clubs = [t["club"] for t in teams]

        fixtures = {}

        if len(clubs) == 4:

            fixtures = {
                1: [(clubs[0], clubs[1]), (clubs[2], clubs[3])],
                2: [(clubs[0], clubs[2]), (clubs[1], clubs[3])],
                3: [(clubs[0], clubs[3]), (clubs[1], clubs[2])]
            }

            mode = "League"

        else:

            fixtures = {
                1: [(clubs[0], clubs[1])]
            }

            mode = "Rivals"

        self.active = {
            "mode": mode,
            "round": 1,
            "fixtures": fixtures,
            "teams": teams,
            "standings": {club: 0 for club in clubs},
            "completed": []
        }

    def current_games(self):

        return self.active["fixtures"][self.active["round"]]

    def record_win(self, winner):

        self.active["standings"][winner] += 1
        self.active["completed"].append(winner)

        needed = len(self.current_games())

        if len(self.active["completed"]) == needed:

            self.active["completed"] = []

            if self.active["round"] < len(self.active["fixtures"]):
                self.active["round"] += 1

            else:
                self.active["finished"] = True

    async def create_live_hub(self, channel):

        self.live_channel = channel

        embed = self.build_embed()

        self.live_message = await channel.send(
            embed=embed,
            view=MatchView(self)
        )

    async def update_live_hub(self):

        if self.live_message is None:
            return

        if self.active.get("finished"):

            winner = max(
                self.active["standings"],
                key=self.active["standings"].get
            )

            embed = self.build_embed()

            embed.title = "🏆 Session Complete"

            embed.description = f"**Champions:** {winner}"

            await self.live_message.edit(
                embed=embed,
                view=None
            )

            return

        await self.live_message.edit(
            embed=self.build_embed(),
            view=MatchView(self)
        )

    def build_embed(self):

        embed = discord.Embed(
            title=f"⚽ NTF {self.active['mode']} Session",
            description=f"**Round {self.active['round']}**",
            colour=0x2EC4FF
        )

        for team in self.active["teams"]:

            text = ""

            for i, player in enumerate(team["players"]):

                if i == 0:
                    text += f"👑 <@{player['id']}>\n"
                else:
                    text += f"• <@{player['id']}>\n"

            embed.add_field(
                name=f"{team['club']} • {len(team['players'])}/6",
                value=text,
                inline=False
            )

        fixtures = ""

        for a, b in self.current_games():

            fixtures += f"⚽ {a} vs {b}\n"

        embed.add_field(
            name="Current Matches",
            value=fixtures,
            inline=False
        )

        standings = ""

        ordered = sorted(
            self.active["standings"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for club, pts in ordered:
            standings += f"{club} — {pts}\n"

        embed.add_field(
            name="Standings",
            value=standings,
            inline=False
        )

        embed.add_field(
            name="🪑 Bench",
            value="0/4 Slots Used",
            inline=False
        )

        return embed


async def setup(bot):
    await bot.add_cog(Session(bot))
