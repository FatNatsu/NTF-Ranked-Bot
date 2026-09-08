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
    embed = discord.Embed(
        title="⚽ NTF Queue",
        description="**The next kick-off begins when 24 players step onto the pitch.**",
        colour=0x2EC4FF
    )

    embed.add_field(
        name="🏟️ Players on the Pitch",
        value=f"**{len(QUEUE)}/{QUEUE_SIZE}**",
        inline=True
    )

    embed.add_field(
        name="⚡ Status",
        value="Open" if len(QUEUE) < QUEUE_SIZE else "Ready Check",
        inline=True
    )

    embed.add_field(
        name="🏆 Club Rotation",
        value=(
            "🔷 Fram Esports\n"
            "🟣 The Fifth Pass\n"
            "🟢 Warya Wonders\n"
            "🟡 Delectable XI\n"
            "🔵 Joyboi"
        ),
        inline=False
    )

    embed.set_footer(text="NTF • Enter the Pitch")

    return embed


class ReadyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=READY_TIMEOUT)

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id in QUEUE:
            READY.add(interaction.user.id)

        await interaction.response.send_message(
            "You're locked in.",
            ephemeral=True
            "NTF Queue panel created.",
            ephemeral=True
        )

    async def start_ready_check(self, channel):

        global READY_ACTIVE

        if READY_ACTIVE:
            return

        READY_ACTIVE = True
        READY.clear()

        await channel.send(
            "**⚽ MATCH FOUND!**\n\nEvery player has **30 seconds** to accept.",
            view=ReadyView()
        )

        await asyncio.sleep(READY_TIMEOUT)

        failed = [player for player in QUEUE if player not in READY]

        for player in failed:
            QUEUE.remove(player)

        READY_ACTIVE = False

        if failed:
            mentions = " ".join(f"<@{player}>" for player in failed)

            await channel.send(
                f"{mentions} didn't accept.\n\nQueue reset to **{len(QUEUE)}/{QUEUE_SIZE}**."
            )
        else:
            await channel.send(
                "🔥 Everyone accepted. Building teams..."
            )


async def setup(bot):
    await bot.add_cog(Queue(bot))
