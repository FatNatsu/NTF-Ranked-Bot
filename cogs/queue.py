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
            await interaction.response.send_message(
                "Queue is closed.",
                ephemeral=True
            )
            return

        if interaction.user.id in self.cog.queue:
            await interaction.response.send_message(
                "You're already queued.",
                ephemeral=True
            )
            return

        limit = 24 if self.cog.mode == "4team" else 12

        if len(self.cog.queue) >= limit:
            await interaction.response.send_message(
                "Queue is full.",
                ephemeral=True
            )
            return

        self.cog.queue.append(interaction.user.id)

        await self.cog.update_queue_message()

        await interaction.response.send_message(
            "Joined the queue.",
            ephemeral=True
        )

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id not in self.cog.queue:
            await interaction.response.send_message(
                "You're not queued.",
                ephemeral=True
            )
            return

        self.cog.queue.remove(interaction.user.id)

        await self.cog.update_queue_message()

        await interaction.response.send_message(
            "Left the queue.",
            ephemeral=True
        )


class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.queue = []
        self.queue_open = False
        self.queue_message = None
        self.mode = "4team"

    # -------------------------
    # Queue embed
    # -------------------------

    async def build_embed(self, guild):

        limit = 24 if self.mode == "4team" else 12

        embed = discord.Embed(
            title="NTF Ranked Queue",
            description=f"**{len(self.queue)}/{limit} Players**",
            colour=0x2EC4FF
        )

        if self.queue:

            text = ""

            for i, uid in enumerate(self.queue, start=1):

                member = guild.get_member(uid)

                if member:
                    text += f"{i}. {member.mention}\n"

            embed.add_field(
                name="Queue",
                value=text,
                inline=False
            )

        else:

            embed.add_field(
                name="Queue",
                value="Nobody queued.",
                inline=False
            )

        return embed

    async def update_queue_message(self):

        if self.queue_message:

            embed = await self.build_embed(self.queue_message.guild)

            await self.queue_message.edit(
                embed=embed,
                view=QueueView(self)
            )

    # -------------------------
    # Auto close
    # -------------------------

    async def auto_close(self):

        await asyncio.sleep(1800)

        if self.queue_open:

            self.queue_open = False

            await self.update_queue_message()

    # -------------------------
    # Launch session
    # -------------------------

    async def launch_session(
        self,
        interaction,
        guild
    ):

        matchmaking = self.bot.get_cog("Matchmaking")

        if matchmaking is None:
            await interaction.followup.send(
                "Matchmaking isn't loaded.",
                ephemeral=True
            )
            return

        if len(self.queue) == 0:
            await interaction.followup.send(
                "Nobody is queued.",
                ephemeral=True
            )
            return

        try:

            await matchmaking.start_session(
                guild=guild,
                queue=self.queue.copy()
            )

            self.queue.clear()
            self.queue_open = False

            await self.update_queue_message()

            await interaction.followup.send(
                "Session started.",
                ephemeral=True
            )

        except Exception as e:

            await interaction.followup.send(
                f"Failed to start session.\n`{e}`",
                ephemeral=True
            )

            raise

    # -------------------------
    # Slash commands
    # -------------------------

    queue_group = app_commands.Group(
        name="queue",
        description="NTF Queue commands."
    )

    @queue_group.command(name="open", description="Open the queue.")
    @app_commands.default_permissions(administrator=True)
    async def open(self, interaction: discord.Interaction):

        self.queue_open = True

        self.queue.clear()

        embed = await self.build_embed(interaction.guild)

        self.queue_message = await interaction.channel.send(
            embed=embed,
            view=QueueView(self)
        )

        await interaction.response.send_message(
            "Queue opened.",
            ephemeral=True
        )

        self.bot.loop.create_task(
            self.auto_close()
        )

    @queue_group.command(name="close", description="Close the queue.")
    @app_commands.default_permissions(administrator=True)
    async def close(self, interaction: discord.Interaction):

        self.queue_open = False

        await self.update_queue_message()

        await interaction.response.send_message(
            "Queue closed.",
            ephemeral=True
        )

    @queue_group.command(name="forcestart", description="Force start the session.")
    @app_commands.default_permissions(administrator=True)
    async def forcestart(self, interaction: discord.Interaction):

        await interaction.response.defer(
            ephemeral=True
        )

        await self.launch_session(
            interaction,
            interaction.guild
        )

    @queue_group.command(name="mode", description="Switch between League and Rivals.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(mode="league or rivals")
    async def mode_command(self, interaction: discord.Interaction, mode: str):

        mode = mode.lower()

        if mode == "league":
            self.mode = "4team"

        elif mode == "rivals":
            self.mode = "2team"

        else:
            await interaction.response.send_message(
                "Use 'league' or 'rivals'.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Mode changed to {mode.title()}.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Queue(bot))
