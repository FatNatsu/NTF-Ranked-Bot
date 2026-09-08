import discord
from discord.ext import commands
from discord import app_commands

QUEUE = []

class QueueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.success, emoji="✅")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in QUEUE:
            QUEUE.append(interaction.user.id)
        await interaction.response.edit_message(embed=create_embed(), view=self)

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, emoji="❌")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in QUEUE:
            QUEUE.remove(interaction.user.id)
        await interaction.response.edit_message(embed=create_embed(), view=self)

def create_embed():
    embed = discord.Embed(
        title="⚽ NTF Ranked Queue",
        description="24-player matchmaking",
        colour=0xFF6A00
    )
    embed.add_field(name="Players", value=f"**{len(QUEUE)}/24**", inline=False)
    embed.set_footer(text="Queue starts automatically at 24 players.")
    return embed

class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="queue", description="Post the NTF queue panel.")
    @app_commands.default_permissions(administrator=True)
    async def queue(self, interaction: discord.Interaction):
        await interaction.channel.send(embed=create_embed(), view=QueueView())
        await interaction.response.send_message("Queue panel created.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Queue(bot))
