import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands

DB_NAME = "ntf.db"

class Mode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    group = app_commands.Group(
        name="mode",
        description="Manage NTF match modes."
    )

    @group.command(name="4team", description="Switch to League Mode.")
    @app_commands.default_permissions(administrator=True)
    async def four_team(self, interaction: discord.Interaction):

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE settings SET value='4team' WHERE key='match_mode'"
            )
            await db.commit()

        await interaction.response.send_message(
            "⚽ Match mode set to **League Mode (4 Teams)**.",
            ephemeral=True
        )

    @group.command(name="2team", description="Switch to Rivals Mode.")
    @app_commands.default_permissions(administrator=True)
    async def two_team(self, interaction: discord.Interaction):

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE settings SET value='2team' WHERE key='match_mode'"
            )
            await db.commit()

        await interaction.response.send_message(
            "⚔️ Match mode set to **Rivals Mode (2 Teams)**.",
            ephemeral=True
        )

    @group.command(name="status", description="View the current match mode.")
    async def status(self, interaction: discord.Interaction):

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key='match_mode'"
            )
            row = await cursor.fetchone()

        mode = "League Mode (4 Teams)" if row[0] == "4team" else "Rivals Mode (2 Teams)"

        embed = discord.Embed(
            title="⚽ NTF Match Mode",
            description=f"Current mode: **{mode}**",
            colour=0x2EC4FF
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Mode(bot))
