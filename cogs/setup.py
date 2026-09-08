import discord
from discord.ext import commands
from discord import app_commands

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="setup",
        description="Create all NTF ranked channels."
    )
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):

        guild = interaction.guild

        text_channels = [
            "ntf-queue",
            "match-results",
            "leaderboard"
        ]

        for name in text_channels:
            if not discord.utils.get(guild.text_channels, name=name):
                await guild.create_text_channel(name)

        if not discord.utils.get(guild.categories, name="NTF Match"):
            category = await guild.create_category("NTF Match")

            await guild.create_voice_channel(
                "Waiting Room",
                category=category
            )

        await interaction.response.send_message(
            "✅ NTF Ranked setup completed.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Setup(bot))
