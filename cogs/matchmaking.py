import random
import discord
import aiosqlite
from discord.ext import commands

DB_NAME = "ntf.db"

class Matchmaking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_mode(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT value FROM settings WHERE key='match_mode'"
            )
            row = await cur.fetchone()

        return row[0] if row else "4team"

    async def get_team_pool(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT name FROM teams ORDER BY RANDOM()"
            )
            rows = await cur.fetchall()

        return [r[0] for r in rows]

    async def get_captains(self, queue_ids):

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT user_id FROM captains"
            )
            rows = await cur.fetchall()

        whitelist = [r[0] for r in rows if r[0] in queue_ids]

        return whitelist

    async def create_session(self, guild, queue_ids):

        mode = await self.get_mode()

        if mode == "4team":
            team_count = 4
        else:
            team_count = 2

        clubs = (await self.get_team_pool())[:team_count]

        captain_pool = await self.get_captains(queue_ids)

        if len(captain_pool) >= team_count:
            captains = random.sample(captain_pool, team_count)
        else:
            captains = random.sample(queue_ids, team_count)

        players = [p for p in queue_ids if p not in captains]
        random.shuffle(players)

        teams = {}

        for i in range(team_count):
            teams[clubs[i]] = [captains[i]]

        index = 0

        while players:
            teams[clubs[index % team_count]].append(players.pop(0))
            index += 1

        # ---------- Discord Category ----------

        category = discord.utils.get(
            guild.categories,
            name="In Progress"
        )

        if category is None:
            category = await guild.create_category(
                "In Progress"
            )

        # ---------- Captain Role ----------

        captain_role = discord.utils.get(
            guild.roles,
            name="👑 Captain"
        )

        if captain_role is None:
            captain_role = await guild.create_role(
                name="👑 Captain",
                colour=discord.Colour.gold()
            )

        # ---------- Team Voice Channels ----------

        voice_channels = {}

        for team in teams:

            vc = await guild.create_voice_channel(
                team,
                category=category
            )

            voice_channels[team] = vc

        # ---------- Give Captain Permissions ----------

        for captain in captains:

            member = guild.get_member(captain)

            if member:
                await member.add_roles(captain_role)

        # ---------- Move Players ----------

        for team, members in teams.items():

            vc = voice_channels[team]

            for member_id in members:

                member = guild.get_member(member_id)

                if member and member.voice:
                    try:
                        await member.move_to(vc)
                    except:
                        pass

        # ---------- Session Channels ----------

        async def ensure_text(name):

            channel = discord.utils.get(
                guild.text_channels,
                name=name
            )

            if channel:
                return channel

            return await guild.create_text_channel(name)

        session_live = await ensure_text("session-live")
        next_round = await ensure_text("next-round")

        control = discord.utils.get(
            guild.text_channels,
            name="session-control"
        )

        if control is None:

            overwrites = {
                guild.default_role:
                    discord.PermissionOverwrite(view_channel=False)
            }

            for role in guild.roles:

                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True
                    )

            control = await guild.create_text_channel(
                "session-control",
                overwrites=overwrites
            )

        # ---------- Team Reveal ----------

        embed = discord.Embed(
            title="⚽ NTF Session",
            description="Teams have entered the pitch.",
            colour=0x2EC4FF
        )

        for team, members in teams.items():

            captain = guild.get_member(members[0])

            text = f"👑 {captain.mention}\n"

            for player in members[1:]:

                member = guild.get_member(player)

                if member:
                    text += f"• {member.mention}\n"

            embed.add_field(
                name=team,
                value=text,
                inline=False
            )

        await session_live.send(embed=embed)

        if team_count == 4:

            fixtures = [
                f"**Round 1**\n{clubs[0]} vs {clubs[1]}\n{clubs[2]} vs {clubs[3]}",
                f"**Round 2**\n{clubs[0]} vs {clubs[2]}\n{clubs[1]} vs {clubs[3]}",
                f"**Round 3**\n{clubs[0]} vs {clubs[3]}\n{clubs[1]} vs {clubs[2]}"
            ]

            await next_round.send(fixtures[0])

        else:

            await next_round.send(
                f"**{clubs[0]} vs {clubs[1]}**"
            )

async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
