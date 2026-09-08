        cap, force, mode = await self.limits()

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
            value=f"**{force} Players**",
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
            "## ⚡ MATCH FOUND!\nAccept within **30 seconds**."
        )

        await asyncio.sleep(30)

        await channel.send(
            "🔥 Matchmaking starting..."
        )

        self.ready_check = False
        self.queue_open = False

    queue_group = app_commands.Group(
        name="queue",
        description="Manage the NTF Queue."
    )

    @queue_group.command(name="open", description="Open the queue.")
    @app_commands.default_permissions(administrator=True)
    async def open(self, interaction: discord.Interaction):

        if self.queue_open:
            await interaction.response.send_message(
                "Queue is already open.",
                ephemeral=True
            )
            return

    @queue_group.command(name="teststart", description="Start a test session with any number of queued players.")
    @app_commands.default_permissions(administrator=True)
    async def teststart(self, interaction: discord.Interaction, players: int):

        if players < 4:
            await interaction.response.send_message(
                "Minimum test size is **4** players.",
                ephemeral=True
            )
            return

        if players > len(self.queue):
            await interaction.response.send_message(
                f"Only **{len(self.queue)}** players are currently queued.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🧪 Starting a **{players}-player** test session.",
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

    @queue_group.command(name="status", description="View queued players.")
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

        cap, _, _ = await self.cog.limits()

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
