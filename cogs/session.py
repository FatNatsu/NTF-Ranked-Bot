import discord
from discord.ext import commands

class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = None

    def start_league(self, clubs):
        self.active = {
            "mode": "4team",
            "round": 1,
            "clubs": clubs,
            "standings": {club: 0 for club in clubs},
            "fixtures": {
                1: [(clubs[0], clubs[1]), (clubs[2], clubs[3])],
                2: [(clubs[0], clubs[2]), (clubs[1], clubs[3])],
                3: [(clubs[0], clubs[3]), (clubs[1], clubs[2])]
            },
            "played": []
        }

    def start_rivals(self, clubs):
        self.active = {
            "mode": "2team",
            "clubs": clubs,
            "standings": {club: 0 for club in clubs},
            "played": []
        }

    async def post_round(self, channel):
        if not self.active:
            return

        if self.active["mode"] == "4team":
            r = self.active["round"]
            games = self.active["fixtures"][r]

            embed = discord.Embed(
                title=f"⚽ Round {r}",
                colour=0x2EC4FF
            )

            embed.description = (
                f"**{games[0][0]} vs {games[0][1]}**\n"
                f"**{games[1][0]} vs {games[1][1]}**"
            )

            await channel.send(embed=embed)

    async def standings_embed(self):
        embed = discord.Embed(
            title="🏆 Live Standings",
            colour=0x2EC4FF
        )

        ordered = sorted(
            self.active["standings"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        text = ""

        for club, points in ordered:
            text += f"**{club}** — {points} pts\n"

        embed.description = text

        return embed

async def setup(bot):
    await bot.add_cog(Session(bot))
