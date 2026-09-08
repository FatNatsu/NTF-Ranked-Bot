import discord
from discord.ext import commands
from discord import app_commands
import asyncio


class QueueView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.queue_open:
            return await interaction.response.send_message("Queue is closed.", ephemeral=True)

        if interaction.user.id in self.cog.queue:
            return await interaction.response.send_message("You're already queued.", ephemeral=True)

        limit = 24 if self.cog.mode == "4team" else 12

        if len(self.cog.queue) >= limit:
            return await interaction.response.send_message("Queue is full.", ephemeral=True)

        self.cog.queue.append(interaction.user.id)
        await self.cog.update_queue_message()
        await interaction.response.send_message("Joined the queue.", ephemeral=True)

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.cog.queue:
            return await interaction.response.send_message("You're not queued.", ephemeral=True)

        self.cog.queue.remove(interaction.user.id)
        await self.cog.update_queue_message()
        await interaction.response.send_message("Left the queue.", ephemeral=True)


class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.queue_open = False
        self.queue_message = None
        self.mode = "4team"

    async def build_embed(self, guild):
        limit = 24 if self.mode == "4team" else 12

        embed = discord.Embed(
            title="⚽ NTF Ranked Queue",
            description=f"**{len(self.queue)}/{limit} Players**",
            colour=0x2EC4FF
        )

        if self.queue:
            players = "\n".join(
                f"{i+1}. {guild.get_member(uid).mention if guild.get_member(uid) else uid}"
                for i, uid in enumerate(self.queue)
            )
        else:
            players = "Nobody queued."

        embed.add_field(name="Queue", value=players, inline=False)
        return embed

    async def update_queue_message(self):
        if self.queue_message:
            await self.queue_message.edit(
                embed=await self.build_embed(self.queue_message.guild),
                view=QueueView(self)
            )

    async def auto_close(self):
        await asyncio.sleep(1800)

        if self.queue_open:
            self.queue_open = False
            await self.update_queue_message()

    async def launch_session(self, interaction):
        matchmaking = self.bot.get_cog("Matchmaking")

        if matchmaking is None:
            return await interaction.followup.send(
                "❌ Matchmaking isn't loaded.",
                ephemeral=True
            )

        await matchmaking.start_session(
            guild=interaction.guild,
            queue=self.queue.copy()
        )

        self.queue.clear()
        self.queue_open = False

        await self.update_queue_message()

    queue_group = app_commands.Group(
        name="queue",
        description="Queue commands."
    )

    @queue_group.command(name="open")
    @app_commands.default_permissions(administrator=True)
    async def open(self, interaction: discord.Interaction):
        self.queue_open = True
        self.queue.clear()

        self.queue_message = await interaction.channel.send(
            embed=await self.build_embed(interaction.guild),
            view=QueueView(self)
        )

        self.bot.loop.create_task(self.auto_close())

        await interaction.response.send_message(
            "Queue opened.",
            ephemeral=True
        )

    @queue_group.command(name="close")
    @app_commands.default_permissions(administrator=True)
    async def close(self, interaction: discord.Interaction):
        self.queue_open = False
        await self.update_queue_message()

        await interaction.response.send_message(
            "Queue closed.",
            ephemeral=True
        )

    @queue_group.command(name="forcestart")
    @app_commands.default_permissions(administrator=True)
    async def forcestart(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.launch_session(interaction)

        await interaction.followup.send(
            "🚀 NTF session launched.",
            ephemeral=True
        )

    @queue_group.command(name="mode")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(mode="league or rivals")
    async def mode(self, interaction: discord.Interaction, mode: str):
        mode = mode.lower()

        if mode == "league":
            self.mode = "4team"
        elif mode == "rivals":
            self.mode = "2team"
        else:
            return await interaction.response.send_message(
                "Use `league` or `rivals`.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"Mode set to **{mode.title()}**.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Queue(bot))
