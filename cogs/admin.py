import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB_NAME = "ntf.db"

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- CAPTAINS ---------------- #

    @app_commands.command(name="captain_add", description="Add a player to the captain whitelist.")
    @app_commands.default_permissions(administrator=True)
    async def captain_add(self, interaction: discord.Interaction, member: discord.Member):

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT OR IGNORE INTO captains(user_id) VALUES(?)",
                (member.id,)
            )
            await db.commit()

        await interaction.response.send_message(
            f"👑 {member.mention} added to the captain whitelist.",
            ephemeral=True
        )

    @app_commands.command(name="captain_remove", description="Remove a player from the captain whitelist.")
    @app_commands.default_permissions(administrator=True)
    async def captain_remove(self, interaction: discord.Interaction, member: discord.Member):

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "DELETE FROM captains WHERE user_id=?",
                (member.id,)
            )
            await db.commit()

        await interaction.response.send_message(
            f"❌ {member.mention} removed from the captain whitelist.",
            ephemeral=True
        )

    @app_commands.command(name="captain_list", description="Show all eligible captains.")
    async def captain_list(self, interaction: discord.Interaction):

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT user_id FROM captains")
            rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message("No captains have been added.")
            return

        text = "\n".join(f"• <@{r[0]}>" for r in rows)

        embed = discord.Embed(
            title="👑 Captain Whitelist",
            description=text,
            colour=0x2EC4FF
        )

        await interaction.response.send_message(embed=embed)

    # ---------------- TEAMS ---------------- #

    @app_commands.command(name="team_add", description="Add a new team.")
    @app_commands.default_permissions(administrator=True)
    async def team_add(self, interaction: discord.Interaction, name: str):

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT OR IGNORE INTO teams(name) VALUES(?)",
                (name,)
            )
            await db.commit()

        await interaction.response.send_message(
            f"✅ **{name}** added.",
            ephemeral=True
        )

    @app_commands.command(name="team_remove", description="Remove a team.")
    @app_commands.default_permissions(administrator=True)
    async def team_remove(self, interaction: discord.Interaction, name: str):

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "DELETE FROM teams WHERE name=?",
                (name,)
            )
            await db.commit()

        await interaction.response.send_message(
            f"❌ **{name}** removed.",
            ephemeral=True
        )

    @app_commands.command(name="team_rename", description="Rename a team.")
    @app_commands.default_permissions(administrator=True)
    async def team_rename(self, interaction: discord.Interaction, old_name: str, new_name: str):

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE teams SET name=? WHERE name=?",
                (new_name, old_name)
            )
            await db.commit()

        await interaction.response.send_message(
            f"✏️ **{old_name}** renamed to **{new_name}**.",
            ephemeral=True
        )

    @app_commands.command(name="team_list", description="Show all available teams.")
    async def team_list(self, interaction: discord.Interaction):

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT name FROM teams ORDER BY name")
            rows = await cursor.fetchall()

        embed = discord.Embed(
            title="🏆 Team Pool",
            colour=0x2EC4FF
        )

        embed.description = "\n".join(f"• {r[0]}" for r in rows)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))
