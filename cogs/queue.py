import asyncio
import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

DB_NAME = "ntf.db"

class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.queue_message = None
        self.queue_open = False
        self.ready_check = False

    async def get_mode(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("SELECT value FROM settings WHERE key='match_mode'")
            row = await cur.fetchone()
            return row[0] if row else "4team"

    async def limits(self):
        mode = await self.get_mode()
        if mode == "4team":
            return 24, 20, "League Mode"
        return 12, 10, "Rivals Mode"

    async def queue_embed(self):
        cap, force, name = await self.limits()

        embed = discord.Embed(
            title="⚽ NTF Queue",
            description=f"**{name}**",
            colour=0x2EC4FF
        )

        embed.add_field(
            name="Players Queued",
            value=f"**{len(self.queue)}/{cap}**",
            inline=True
        )

        embed.add_field(
            name="Force Start",
            value=f"**{force} players**",
            inline=True
        )

        embed.add_field(
            name="Status",
            value="Open" if self.queue_open else "Closed",
            inline=True
        )

        embed.set_footer(text="NTF • Enter the Pitch")

        return embed

    async def refresh(self):
        if self.queue_message:
            await self.queue_message.edit(
                embed=await self.queue_embed(),
                view=QueueView(self)
            )

    async def start_ready(self, channel):
        if self.ready_check:
            return

        self.ready_check = True

        await channel.send(
            "## ⚡ MATCH FOUND!\nAccepting automatically in **30 seconds**."
        )

        await asyncio.sleep(30)

        await channel.send("Building teams...")

        self.queue_open = False
        self.ready_check = False

    queue_group = app_commands.Group(
        name="queue",
        description="Manage the NTF queue."
    )

    @queue_group.command(name="open", description="Open the NTF queue.")
    @app_commands.default_permissions(administrator=True)
    async def open(self, interaction: discord.Interaction):

        if self.queue_open:
            await interaction.response.send_message(
                "Queue already exists.",
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

    @queue_group.command(name="forcestart", description="Force start the queue.")
    @app_commands.default_permissions(administrator=True)
    async def forcestart(self, interaction: discord.Interaction):

        _, force, _ = await self.limits()

        if len(self.queue) != force:
            await interaction.response.send_message(
                f"Force Start requires exactly **{force}** players.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Force Start initiated.",
            ephemeral=True
        )

        await self.start_ready(interaction.channel)

    @queue_group.command(name="close", description="Close the queue.")
    @app_commands.default_permissions(administrator=True)
    async def close(self, interaction: discord.Interaction):

        self.queue.clear()
        self.queue_open = False

        await self.refresh()

        await interaction.response.send_message(
            "Queue closed.",
            ephemeral=True
        )

    @queue_group.command(name="status", description="Show queued players.")
    async def status(self, interaction: discord.Interaction):

        if not self.queue:
            await interaction.response.send_message(
                "Nobody is queued."
            )
            return

        names = "\n".join(
            f"• <@{i}>"
            for i in self.queue
        )

        embed = discord.Embed(
            title="Queued Players",
            description=names,
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

        cap, _, _ = await self.cog.limits()

        if not self.cog.queue_open:
            await interaction.response.send_message(
                "Queue isn't open.",
                ephemeral=True
            )
            return

        if interaction.user.id in self.cog.queue:
            await interaction.response.send_message(
                "You're already queued.",
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
