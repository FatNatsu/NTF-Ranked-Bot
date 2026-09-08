from discord.ext import commands

class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.active_session = None
        self.current_round = 0
        self.standings = {}

async def setup(bot):
    await bot.add_cog(Session(bot))
