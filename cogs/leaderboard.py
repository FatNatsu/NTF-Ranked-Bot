import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands

DB_NAME = "ntf.db"


def get_rating(mmr: int):
    if mmr >= 2500:
        return "S+"
    if mmr >= 2200:
        return "S"
    if mmr >= 1900:
        return "A+"
    if mmr >= 1600:
        return "A"
    if mmr >= 1300:
        return "B+"
    if mmr >= 1000:
        return "B"
    if mmr >= 700:
        return "C+"
    if mmr >= 400:
        return "C"
    if mmr >= 200:
        return "D"
    return "E"


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_top_players(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("""
                SELECT user_id, mmr
                FROM players
                ORDER BY mmr DESC
                LIMIT 10
            """)
            return await cur.fetchall()

    async def get_player_position(self, user_id):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("""
                SELECT user_id
                FROM players
                ORDER BY mmr DESC
            """)
            players = await cur.fetchall()

        for pos, (pid,) in enumerate(players, start=1):
            if pid == user_id:
                return pos

        return None

    async def build_embed(self, guild, viewer_id=None):
        embed = discord.Embed(
            title="🏆 NTF Leaderboard",
            description="**Live Rankings**",
            colour=0x2EC4FF
        )

        medals = ["🥇", "🥈", "🥉"]

        top = await self.get_top_players()

        if top:
            text = ""

            for i, (uid, mmr) in enumerate(top):
                member = guild.get_member(uid)

                if member:
                    name = member.display_name
                else:
                    try:
                        user = await self.bot.fetch_user(uid)
                        name = user.name
                    except:
                        name = f"Player {uid}"

                place = medals[i] if i < 3 else f"{i+1}."

                text += (
                    f"{place} **{name}**\n"
                    f"`{get_rating(mmr)}` • **{mmr} MMR**\n\n"
                )

            embed.description = text

        else:
            embed.description = "No ranked players yet."

        if viewer_id:
            position = await self.get_player_position(viewer_id)

            if position:
                async with aiosqlite.connect(DB_NAME) as db:
                    cur = await db.execute(
                        "SELECT mmr FROM players WHERE user_id=?",
                        (viewer_id,)
                    )
                    row = await cur.fetchone()

                if row:
                    mmr = row[0]

                    embed.add_field(
                        name="Your Position",
                        value=f"**#{position} • {get_rating(mmr)} • {mmr} MMR**",
                        inline=False
                    )

        embed.set_footer(text="Updates automatically after every session.")

        return embed

    async def update_leaderboard(self, guild):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("""
                SELECT channel_id, message_id
                FROM leaderboard_message
                WHERE guild_id=?
            """, (guild.id,))
            row = await cur.fetchone()

        if not row:
            return

        channel = guild.get_channel(row[0])
