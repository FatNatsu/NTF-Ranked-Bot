import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

DB_NAME = "ntf.db"

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            f"✅ {member.mention} has been added to the Captain Whitelist."
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
            f"❌ {member.mention} has been removed from the Captain Whitelist."
        )

    @app_commands.command(name="captain_list", description="View the captain whitelist.")
    async def captain_list(self, interaction: discord.Interaction):

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("SELECT user_id FROM captains")
            rows = await cur.fetchall()

        if not rows:
            await interaction.response.send_message("No captains have been whitelisted yet.")
            return

        mentions = []
        for (user_id,) in rows:
            mentions.append(f"<@{user_id}>")

        await interaction.response.send_message(
            "**Captain Whitelist**\n" + "\n".join(mentions)
        )

async def setup(bot):
    await bot.add_cog(Admin(bot))
