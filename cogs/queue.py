import asyncio
import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

DB_NAME = "ntf.db"

class Queue(commands.GroupCog, group_name="queue"):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.queue_message = None
        self.queue_open = False
        self.ready_check = False

    async def get_mode(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT value FROM settings WHERE key='match_mode'"
            )
            row = await cur.fetchone()
            return row[0] if row else "4team"

    async def limits(self):
        mode = await self.get_mode()

        if mode == "4team":
            return 24, "League Mode"

        return 12, "Rivals Mode"

    async def queue_embed(self):
        cap, mode = await self.limits()

        embed = discord.Embed(
            title="⚽ NTF Queue",
            description=f"**{mode}**",
            colour=0x2EC4FF
        )

        embed.add_field(
            name="Players Queued",
            value=f"**{len(self.queue)}/{cap}**",
            inline=True
        )

        embed.add_field(
            name="Force Start",
            value="**Available (Testing)**",
    @app_commands.command(name="open", description="Open the NTF queue.")
    @app_commands.default_permissions(administrator=True)
    async def open(self, interaction: discord.Interaction):

        if self.queue_open:
            await interaction.response.send_message(
                "Queue is already open.",
                ephemeral=True
            )
            return

        self.queue.clear()
        self.queue_open = True

        self.queue_message = await interaction.channel.send(
            embed=await self.queue_embed(),
            view=QueueView(self)
        )

        await interaction.response.send_message(
            "Queue opened.",
            ephemeral=True
        )

    @app_commands.command(name="forcestart", description="Force start the queue.")
    @app_commands.default_permissions(administrator=True)
    async def forcestart(self, interaction: discord.Interaction):

        if len(self.queue) < 1:
            await interaction.response.send_message(
                "At least **1 player** must be queued.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🚀 Force starting with **{len(self.queue)}** player(s).",
            ephemeral=True
        )

        await self.start_ready(interaction.channel)

    @app_commands.command(name="teststart", description="Start a test session with queued players.")
    @app_commands.default_permissions(administrator=True)
    async def teststart(self, interaction: discord.Interaction, players: int):

        if players < 1:
            await interaction.response.send_message(
                "Minimum is **1** player.",
                ephemeral=True
            )
            return

        if players > len(self.queue):
            await interaction.response.send_message(
                f"Only **{len(self.queue)}** players are queued.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🧪 Starting a **{players}-player** test session.",
            ephemeral=True
        )

        await self.start_ready(interaction.channel)

    @app_commands.command(name="close", description="Close the queue.")
    @app_commands.default_permissions(administrator=True)
    async def close(self, interaction: discord.Interaction):

        self.queue.clear()
        self.queue_open = False

        await self.refresh()

        await interaction.response.send_message(
            "Queue closed.",
            ephemeral=True
        )

    @app_commands.command(name="status", description="View queued players.")
    async def status(self, interaction: discord.Interaction):

        if not self.queue:
            await interaction.response.send_message(
                "Nobody is queued."
            )
            return

        players = "\n".join(
            f"• <@{player}>"
            for player in self.queue
        )

        embed = discord.Embed(
            title="Queued Players",
            description=players,
            colour=0x2EC4FF
        )

        await interaction.response.send_message(embed=embed)


class QueueView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Join Queue",
        style=discord.ButtonStyle.success,
        emoji="⚽"
    )
    async def join(self, interaction: discord.Interaction, button):

        cap, _ = await self.cog.limits()

        if not self.cog.queue_open:
            await interaction.response.send_message(
                "Queue isn't open.",
                ephemeral=True
            )
            return

        if interaction.user.id in self.cog.queue:
            await interaction.response.send_message(
                "You're already in the queue.",
                ephemeral=True
            )
            return

        if len(self.cog.queue) >= cap:
            await interaction.response.send_message(
                "Queue is full.",
                ephemeral=True
            )
            return

        self.cog.queue.append(interaction.user.id)

        await self.cog.refresh()

        await interaction.response.send_message(
            "Joined the queue.",
            ephemeral=True
        )

        if len(self.cog.queue) == cap:
            await self.cog.start_ready(interaction.channel)

    @discord.ui.button(
        label="Leave Queue",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    )
    async def leave(self, interaction: discord.Interaction, button):

        if interaction.user.id in self.cog.queue:
            self.cog.queue.remove(interaction.user.id)

        await self.cog.refresh()

        await interaction.response.send_message(
            "Left the queue.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Queue(bot))
