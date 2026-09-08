import random
import aiosqlite
import discord
from discord.ext import commands

DB_NAME = "ntf.db"

CLUB_POOL = [
    "Fram Esports",
    "Joyboi",
    "Warya Wonders",
    "The Fifth Pass",
]

class Matchmaking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def start_session(self, guild, queue):
        category = await guild.create_category("In Progress - NTF-0001")

        clubs = random.sample(CLUB_POOL, 4)

        voice_channels = []
        teams = {}

        for i, club in enumerate(clubs):
            vc = await guild.create_voice_channel(club, category=category)
            voice_channels.append(vc)

            teams[club] = {
                "captain": queue[0] if i == 0 and queue else None,
                "players": [queue[0]] if i == 0 and queue else []
            }

        bench = await guild.create_voice_channel("🪑 Bench", category=category)
        voice_channels.append(bench)

        progress = await guild.create_text_channel("in-progress", category=category)
        control = await guild.create_text_channel("session-control", category=category)

        session = self.bot.get_cog("Session")

        if session:
            await session.register_session(
                guild=guild,
                session_code="NTF-0001",
                mode="League",
                teams=teams,
                category=category,
                progress_channel=progress,
                control_channel=control,
                voice_channels=voice_channels
            )

async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
