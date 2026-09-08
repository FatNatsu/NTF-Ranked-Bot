class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_top_players(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("""
                SELECT user_id, mmr
                FROM players
                ORDER BY mmr DESC
                LIMIT 10
            """)
            return await cur.fetchall()

    async def get_player_position(self, user_id):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("""
                SELECT user_id
                FROM players
                ORDER BY mmr DESC
            """)
            players = await cur.fetchall()

        for index, (pid,) in enumerate(players, start=1):
            if pid == user_id:
                return index

        return None

    async def build_embed(self, guild, viewer_id=None):
        top = await self.get_top_players()

        embed = discord.Embed(
            title="🏆 NTF Leaderboard",
            description="**Live Rankings**",
            colour=0x2EC4FF
        )

        medals = ["🥇", "🥈", "🥉"]

        if not top:
            embed.description = "No ranked players yet."

        else:
            text = ""

            for i, (user_id, mmr) in enumerate(top):
                member = guild.get_member(user_id)

                if member:
                    name = member.display_name
                else:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        name = user.name
                    except:
                        name = f"Player {user_id}"

                rank = medals[i] if i < 3 else f"{i+1}."

                text += f"{rank} **{name}**\n"
                text += f"`{get_rating(mmr)}` • **{mmr} MMR**\n\n"

            embed.description = text

        if viewer_id:
            position = await self.get_player_position(viewer_id)

            if position:
                async with aiosqlite.connect(DB_NAME) as db:
                    cur = await db.execute("""
                        SELECT mmr
                        FROM players
                        WHERE user_id=?
                    """, (viewer_id,))
                    row = await cur.fetchone()

                if row:
                    mmr = row[0]
                    embed.add_field(
                        name="Your Position",
                        value=f"**#{position} • {get_rating(mmr)} • {mmr} MMR**",
                        inline=False
                    )

        embed.set_footer(text="Updates automatically after every session.")

        return embed

    async def update_leaderboard(self, guild):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("""
                SELECT channel_id,message_id
                FROM leaderboard_message
                WHERE guild_id=?
            """, (guild.id,))
            row = await cur.fetchone()

        if not row:
            return

        channel = guild.get_channel(row[0])

        if not channel:
            return

        try:
            message = await channel.fetch_message(row[1])
            await message.edit(embed=await self.build_embed(guild))
        except:
            pass

    @app_commands.command(
        name="leaderboard",
        description="Show the NTF leaderboard."
    )
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=await self.build_embed(
                interaction.guild,
                interaction.user.id
            )
        )

    @app_commands.command(
        name="leaderboard_setup",
        description="Create the live leaderboard message."
    )
    @app_commands.default_permissions(administrator=True)
    async def leaderboard_setup(self, interaction: discord.Interaction):

        message = await interaction.channel.send(
            embed=await self.build_embed(interaction.guild)
        )

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT OR REPLACE INTO leaderboard_message
                VALUES(?,?,?)
            """, (
                interaction.guild.id,
                interaction.channel.id,
                message.id
            ))
            await db.commit()

        await interaction.response.send_message(
            "Live leaderboard created.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
