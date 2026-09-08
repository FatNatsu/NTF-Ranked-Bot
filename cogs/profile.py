import aiosqlite
import discord
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


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_player(self, user_id):
        async with aiosqlite.connect(DB_NAME) as db:

            cur = await db.execute("""
            SELECT mmr,wins,losses,games_played
            FROM players
            WHERE user_id=?
            """, (user_id,))

            row = await cur.fetchone()

            if row is None:
                await db.execute("""
                INSERT INTO players(user_id)
                VALUES(?)
                """, (user_id,))
                await db.commit()
                return (100, 0, 0, 0)

            return row

    async def get_best_club(self, user_id):
        async with aiosqlite.connect(DB_NAME) as db:

            cur = await db.execute("""
            SELECT club_name,wins
            FROM club_history
            WHERE user_id=?
            ORDER BY wins DESC
            LIMIT 1
            """, (user_id,))

            row = await cur.fetchone()

            if row:
                return row

            return ("None Yet", 0)

    async def get_recent_form(self, user_id):
        async with aiosqlite.connect(DB_NAME) as db:

            cur = await db.execute("""
            SELECT result
            FROM recent_form
            WHERE user_id=?
            ORDER BY timestamp DESC
            LIMIT 5
            """, (user_id,))

            rows = await cur.fetchall()

        if not rows:
            return "No games played"

        return " ".join(
            "🟢" if r[0] == "W" else "🔴"
            for r in rows
        )

    @app_commands.command(
        name="profile",
        description="View a player's NTF profile."
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None
    ):

        if user is None:
            user = interaction.user

        mmr, wins, losses, games = await self.get_player(user.id)

        rating = get_rating(mmr)

        club, club_wins = await self.get_best_club(user.id)

        form = await self.get_recent_form(user.id)

        win_rate = 0

        if games:
            win_rate = round((wins / games) * 100, 1)

        embed = discord.Embed(
            title=f"{user.display_name}",
            description=f"**{rating} Rank • {mmr} MMR**",
            colour=0x2EC4FF
        )

        if user.display_avatar:
            embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(
            name="🏆 Wins",
            value=str(wins),
            inline=True
        )

        embed.add_field(
            name="❌ Losses",
            value=str(losses),
            inline=True
        )

        embed.add_field(
            name="📊 Win Rate",
            value=f"{win_rate}%",
            inline=True
        )

        embed.add_field(
            name="🔷 Most Successful Club",
            value=f"{club} ({club_wins} wins)",
            inline=False
        )

        embed.add_field(
            name="🔥 Recent Form",
            value=form,
            inline=False
        )

        embed.set_footer(
            text="NTF Competitive Profile"
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Profile(bot))
