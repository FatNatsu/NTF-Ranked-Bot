import random
import aiosqlite
import discord
from discord.ext import commands

from utils.team_balancer import TeamBalancer

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

    async def get_players(self, user_ids):
        players = []

        async with aiosqlite.connect(DB_NAME) as db:
            for uid in user_ids:

                cur = await db.execute(
                    "SELECT mmr, role FROM players WHERE user_id=?",
                    (uid,)
                )

                row = await cur.fetchone()

                if row:
                    mmr, role = row
                else:
                    mmr = 1000
                    role = "ANY"

                players.append({
                    "id": uid,
                    "mmr": mmr,
                    "role": role
                })

        return players

    async def get_captains(self):

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT user_id FROM captains"
            )

            rows = await cur.fetchall()

        return [r[0] for r in rows]

    async def get_clubs(self, amount):

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT name FROM teams ORDER BY RANDOM()"
            )

            rows = await cur.fetchall()

        clubs = [r[0] for r in rows]

        return clubs[:amount]

    async def ensure_text_channel(self, guild, name):

        existing = discord.utils.get(
            guild.text_channels,
            name=name
        )

        if existing:
            return existing

        return await guild.create_text_channel(name)

    async def start_session(self, guild, queue_ids):

        mode = await self.get_mode()
        team_count = 4 if mode == "4team" else 2

        clubs = await self.get_clubs(team_count)
        players = await self.get_players(queue_ids)

        whitelist = await self.get_captains()

        eligible = [
            p["id"]
            for p in players
            if p["id"] in whitelist
        ]

        if len(eligible) >= team_count:
            captains = random.sample(eligible, team_count)
        else:
            captains = random.sample(
                queue_ids,
                min(team_count, len(queue_ids))
            )

        teams = TeamBalancer.balance(
            players,
            captains,
            clubs
        )

        category = discord.utils.get(
            guild.categories,
            name="In Progress"
        )

        if category is None:
            category = await guild.create_category(
                "In Progress"
            )
        else:
            for vc in category.voice_channels:
                await vc.delete()

        captain_role = discord.utils.get(
            guild.roles,
            name="👑 Captain"
        )

        if captain_role is None:
            captain_role = await guild.create_role(
                name="👑 Captain",
                colour=discord.Colour.gold()
            )

        bench_vc = await guild.create_voice_channel(
            "🪑 Bench",
            category=category
        )

        voice_channels = {}

        for team in teams:

            vc = await guild.create_voice_channel(
                team["club"],
                category=category
            )

            voice_channels[team["club"]] = vc

        for team in teams:

            vc = voice_channels[team["club"]]

            for i, player in enumerate(team["players"]):

                member = guild.get_member(
                    player["id"]
                )

                if member is None:
                    continue

                await vc.set_permissions(
                    member,
                    connect=True,
                    speak=True,
                    view_channel=True
                )

                if i == 0:
                    await member.add_roles(
                        captain_role
                    )

                if member.voice:
                    try:
                        await member.move_to(vc)
                    except Exception:
                        pass

        in_progress = await self.ensure_text_channel(
            guild,
            "in-progress"
        )

        control = discord.utils.get(
            guild.text_channels,
            name="session-control"
        )

        if control is None:

            overwrites = {
                guild.default_role:
                    discord.PermissionOverwrite(
                        view_channel=False
                    )
            }

            for role in guild.roles:

                if role.permissions.administrator:
                    overwrites[role] = (
                        discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=True
                        )
                    )

            control = await guild.create_text_channel(
                "session-control",
                overwrites=overwrites
            )

        session = self.bot.get_cog("Session")

        if session:

            session.create(teams)

            await session.create_live_hub(
                in_progress
            )

        await control.send(
            "⚙️ Session created.\nUse the winner buttons below."
        )

        return {
            "teams": teams,
            "voice_channels": voice_channels,
            "bench": bench_vc
        }


async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
