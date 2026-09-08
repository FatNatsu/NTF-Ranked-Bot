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

    async def build_embed(self, guild, viewer_id=None):
        embed = discord.Embed(
            title="🏆 NTF Leaderboard",
            description="Live Rankings",
            colour=0x2EC4FF
        )

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT user_id, mmr FROM players ORDER BY mmr DESC LIMIT 10"
            )
            players = await cur.fetchall()

        medals = ["🥇", "🥈", "🥉"]

        if not players:
            embed.description = "No ranked players yet."
        else:
            text = ""
            for i, (uid, mmr) in enumerate(players):
                member = guild.get_member(uid)
                name = member.display_name if member else f"Player {uid}"
                place = medals[i] if i < 3 else f"{i+1}."
                text += f"{place} **{name}** — `{get_rating(mmr)}` • **{mmr} MMR**\n"
            embed.description = text

        return embed

    @app_commands.command(name="leaderboard", description="View the NTF leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction):
        embed = await self.build_embed(interaction.guild, interaction.user.id)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="leaderboard_setup",
        description="Create the permanent leaderboard message."
    )
    @app_commands.default_permissions(administrator=True)
    async def leaderboard_setup(self, interaction: discord.Interaction):
        embed = await self.build_embed(interaction.guild)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message(
            "✅ Leaderboard created.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
