import asyncio
import discord
from discord.ext import commands
from discord import app_commands

QUEUE = []
READY = set()
QUEUE_SIZE = 24
READY_TIMEOUT = 30
READY_ACTIVE = False

def queue_embed():
    e = discord.Embed(
        title="⚽ NTF Ranked Queue",
        description="FACEIT-style 24 player matchmaking",
        colour=0xFF6A00
    )

    e.add_field(
        name="Players",
        value=f"**{len(QUEUE)}/{QUEUE_SIZE}**",
        inline=False
    )

    e.add_field(
        name="Teams",
        value="Fram Esports\nThe Fifth Pass\nWarya Wonders\nDelectable XI\nJoyboi",
        inline=False
    )

    e.set_footer(text="Queue starts automatically at 24 players.")

    return e

class ReadyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=READY_TIMEOUT)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in QUEUE:
            READY.add(interaction.user.id)
        await interaction.response.send_message("Accepted.", ephemeral=True)

class QueueView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.success, emoji="⚽")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id not in QUEUE:
            QUEUE.append(interaction.user.id)

        await interaction.response.edit_message(
            embed=queue_embed(),
            view=self
        )

        if len(QUEUE) == QUEUE_SIZE:
            await self.cog.start_ready_check(interaction.channel)

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, emoji="❌")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id in QUEUE:
            QUEUE.remove(interaction.user.id)

        await interaction.response.edit_message(
            embed=queue_embed(),
            view=self
        )

class Queue(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="queue", description="Post the NTF queue panel.")
    @app_commands.default_permissions(administrator=True)
    async def queue(self, interaction: discord.Interaction):

        await interaction.channel.send(
            embed=queue_embed(),
            view=QueueView(self)
        )

        await interaction.response.send_message(
            "Queue panel posted.",
            ephemeral=True
        )

    async def start_ready_check(self, channel):

        global READY_ACTIVE

        if READY_ACTIVE:
            return

        READY_ACTIVE = True
        READY.clear()

        view = ReadyView()

        await channel.send(
            "**MATCH FOUND!**\n\nAccept within 30 seconds.",
            view=view
        )

        await asyncio.sleep(READY_TIMEOUT)

        failed = [p for p in QUEUE if p not in READY]

        for p in failed:
            QUEUE.remove(p)

        READY_ACTIVE = False

        if failed:
            mentions = " ".join(f"<@{i}>" for i in failed)

            await channel.send(
                f"{mentions} failed to ready. Queue is now **{len(QUEUE)}/{QUEUE_SIZE}**."
            )
        else:
            await channel.send(
                "Everyone accepted. Building teams..."
            )

async def setup(bot):
    await bot.add_cog(Queue(bot))
