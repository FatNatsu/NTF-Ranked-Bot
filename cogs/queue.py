import discord
from discord.ext import commands
from discord import app_commands

QUEUE = []

def queue_embed():
    embed = discord.Embed(
        title="⚽ NTF Ranked Queue",
        description="24-player matchmaking",
        colour=0xFF6A00
    )
    embed.add_field(
        name="Players Queued",
        value=f"**{len(QUEUE)}/24**",
        inline=False
    )
    embed.add_field(
        name="Teams",
        value="Fram Esports • The Fifth Pass • Warya Wonders • Delectable XI • Joyboi",
        inline=False
    )
    embed.set_footer(text="Queue starts automatically when 24 players join.")
    return embed

class QueueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.success, emoji="⚽")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in QUEUE:
            QUEUE.append(interaction.user.id)
        await interaction.response.edit_message(embed=queue_embed(), view=self)

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, emoji="❌")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in QUEUE:
            QUEUE.remove(interaction.user.id)
        await interaction.response.edit_message(embed=queue_embed(), view=self)

class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="queue", description="Post the NTF queue panel.")
    @app_commands.default_permissions(administrator=True)
    async def queue(self, interaction: discord.Interaction):
        await interaction.channel.send(embed=queue_embed(), view=QueueView())
        await interaction.response.send_message(
            "Queue panel posted.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Queue(bot))
