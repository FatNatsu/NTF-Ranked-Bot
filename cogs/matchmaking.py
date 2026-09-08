import random
import aiosqlite
import discord
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

    async def get_clubs(self, amount):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT name FROM teams ORDER BY RANDOM()"
            )
            rows = await cur.fetchall()

        return [r[0] for r in rows][:amount]

    async def get_whitelist(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT user_id FROM captains"
            )
            rows = await cur.fetchall()

        return [r[0] for r in rows]

    async def start_session(self, guild, channel, queued_players):

        mode = await self.get_mode()
        team_count = 4 if mode == "4team" else 2

        clubs = await self.get_clubs(team_count)

        whitelist = await self.get_whitelist()
        eligible = [p for p in queued_players if p in whitelist]

        if len(eligible) >= team_count:
            captains = random.sample(eligible, team_count)
        else:
            captains = random.sample(
                queued_players,
                min(team_count, len(queued_players))
            )

        teams = {club: [] for club in clubs}

        for club, captain in zip(clubs, captains):
            teams[club].append(captain)

        remaining = [p for p in queued_players if p not in captains]
        random.shuffle(remaining)

        index = 0
        while remaining:
            club = clubs[index % team_count]
            teams[club].append(remaining.pop(0))
            index += 1

        category = discord.utils.get(
            guild.categories,
            name="In Progress"
        )

        if category:
            for vc in category.voice_channels:
                await vc.delete()
        else:
            category = await guild.create_category("In Progress")

        captain_role = discord.utils.get(
            guild.roles,
            name="👑 Captain"
        )

        if captain_role is None:
            captain_role = await guild.create_role(
                name="👑 Captain",
                colour=discord.Colour.gold()
            )

        vcs = {}

        for club in clubs:

            overwrites = {
                guild.default_role:
                    discord.PermissionOverwrite(connect=False)
            }

            overwrites[captain_role] = discord.PermissionOverwrite(
                connect=True,
                speak=True,
                view_channel=True
            )

            vc = await guild.create_voice_channel(
                club,
                category=category,
                overwrites=overwrites
            )

            vcs[club] = vc

        for club, members in teams.items():

            vc = vcs[club]

            for member_id in members:

                member = guild.get_member(member_id)

                if member is None:
                    continue

                await vc.set_permissions(
                    member,
                    connect=True,
                    speak=True,
                    view_channel=True
                )

                if member_id in captains:
                    await member.add_roles(captain_role)

                if member.voice:
                    try:
                        await member.move_to(vc)
                    except:
                        pass

        def ensure_channel(name):
            existing = discord.utils.get(
                guild.text_channels,
                name=name
            )
            return existing

        session_live = ensure_channel("session-live")
        next_round = ensure_channel("next-round")
        control = ensure_channel("session-control")

        if session_live is None:
            session_live = await guild.create_text_channel("session-live")

        if next_round is None:
            next_round = await guild.create_text_channel("next-round")

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

        embed = discord.Embed(
            title="⚽ NTF Session",
            description="Teams have entered the pitch.",
            colour=0x2EC4FF
        )

        for club, members in teams.items():

            text = ""

            for i, member_id in enumerate(members):

                member = guild.get_member(member_id)

                if member is None:
                    continue

                if i == 0:
                    text += f"👑 {member.mention}\n"
                else:
                    text += f"• {member.mention}\n"

            embed.add_field(
                name=club,
                value=text,
                inline=False
            )

        await session_live.send(embed=embed)

        if mode == "4team":

            fixtures = (
                f"## Round 1\n"
                f"🔷 {clubs[0]} vs {clubs[1]}\n"
                f"🟢 {clubs[2]} vs {clubs[3]}"
            )

        else:

            fixtures = (
                f"## Rivals Match\n"
                f"{clubs[0]} vs {clubs[1]}"
            )

        await next_round.send(fixtures)

        await control.send(
            "⚙️ Session Control\n"
            "Winner buttons arrive in V3.3."
        )

async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
