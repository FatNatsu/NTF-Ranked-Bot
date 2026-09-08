import asyncio
import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

DB_NAME = "ntf.db"


class QueueView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Join Queue", emoji="⚽", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button):

        if not self.cog.queue_open:
            await interaction.response.send_message(
                "Queue isn't open.",
                ephemeral=True
            )
            return

        cap = await self.cog.get_cap()

        if len(self.cog.queue) >= cap:
            await interaction.response.send_message(
                "Queue is full.",
                ephemeral=True
            )
            return

        if interaction.user.id in self.cog.queue:
            await interaction.response.send_message(
                "You're already queued.",
                ephemeral=True
            )
            return

        self.cog.queue.append(interaction.user.id)

        await self.cog.update_queue()

        await interaction.response.send_message(
            "Joined the queue.",
            ephemeral=True
        )

        if len(self.cog.queue) == cap:
            await self.cog.launch_session(interaction.guild)

    @discord.ui.button(label="Leave Queue", emoji="❌", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button):

        if interaction.user.id in self.cog.queue:
            self.cog.queue.remove(interaction.user.id)

        await self.cog.update_queue()

        await interaction.response.send_message(
            "Left the queue.",
            ephemeral=True
        )


class Queue(commands.GroupCog, group_name="queue"):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.queue_open = False
        self.queue_message = None
        self.timeout_task = None

    async def get_mode(self):

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT value FROM settings WHERE key='match_mode'"
            )
            row = await cur.fetchone()

        return row[0] if row else "4team"

    async def get_cap(self):
        return 24 if await self.get_mode() == "4team" else 12

    async def queue_embed(self):

        cap = await self.get_cap()
        mode = "League Mode" if cap == 24 else "Rivals Mode"

        embed = discord.Embed(
            title="⚽ NTF Queue",
            description=f"**{mode}**",
            colour=0x2EC4FF
        )

        embed.add_field(
            name="Players",
            value=f"{len(self.queue)}/{cap}",
            inline=True
        )

        embed.add_field(
            name="Force Start",
            value="Admin Only",
            inline=True
        )

        embed.add_field(
            name="Auto Close",
            value="30 Minutes",
            inline=True
        )

        return embed

    async def update_queue(self):

        if self.queue_message:
            await self.queue_message.edit(
                embed=await self.queue_embed(),
                view=QueueView(self)
            )

    async def auto_close(self):

        await asyncio.sleep(1800)

        if self.queue_open:
            self.queue_open = False
            self.queue.clear()

            if self.queue_message:
                await self.queue_message.edit(
                    content="⏰ Queue automatically closed after 30 minutes.",
                    embed=None,
                    view=None
                )

    async def launch_session(self, guild):

        self.queue_open = False

        matchmaking = self.bot.get_cog("Matchmaking")

        if matchmaking:
            await matchmaking.start_session(
                guild,
                self.queue.copy()
            )

        self.queue.clear()

    @app_commands.command(name="open")
    @app_commands.default_permissions(administrator=True)
    async def open(self, interaction: discord.Interaction):

        if self.queue_open:
            await interaction.response.send_message(
                "Queue already open.",
                ephemeral=True
            )
            return

        self.queue.clear()
        self.queue_open = True

        self.queue_message = await interaction.channel.send(
            embed=await self.queue_embed(),
            view=QueueView(self)
        )

        if self.timeout_task:
            self.timeout_task.cancel()

        self.timeout_task = asyncio.create_task(
            self.auto_close()
        )

        await interaction.response.send_message(
            "Queue opened.",
            ephemeral=True
        )

    @app_commands.command(name="forcestart")
    @app_commands.default_permissions(administrator=True)
    async def forcestart(self, interaction: discord.Interaction):

        if len(self.queue) < 1:
            await interaction.response.send_message(
                "At least one player is required.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🚀 Force starting with {len(self.queue)} players.",
            ephemeral=True
        )

        await self.launch_session(interaction.guild)

    @app_commands.command(name="close")
    @app_commands.default_permissions(administrator=True)
    async def close(self, interaction: discord.Interaction):

        self.queue_open = False
        self.queue.clear()

        if self.queue_message:
            await self.queue_message.edit(
                content="Queue closed.",
                embed=None,
                view=None
            )

        await interaction.response.send_message(
            "Queue closed.",
            ephemeral=True
        )

    @app_commands.command(name="status")
    async def status(self, interaction: discord.Interaction):

        if not self.queue:
            await interaction.response.send_message(
                "Nobody is queued."
            )
            return

        await interaction.response.send_message(
            "\n".join(
                f"• <@{p}>"
                for p in self.queue
            )
        )


async def setup(bot):
    await bot.add_cog(Queue(bot))
