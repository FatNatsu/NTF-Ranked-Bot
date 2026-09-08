import random
import discord
import aiosqlite
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

    async def get_players(self, ids):

        players = []

        async with aiosqlite.connect(DB_NAME) as db:

            for user_id in ids:

                cur = await db.execute(
                    "SELECT mmr, role FROM players WHERE user_id=?",
                    (user_id,)
                )

                row = await cur.fetchone()

                if row:
                    mmr, role = row
                else:
                    mmr = 1000
                    role = "ANY"

                players.append({
                    "id": user_id,
                    "mmr": mmr,
                    "role": role
                })

        return players

    async def get_whitelist(self):

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

        return [r[0] for r in rows][:amount]

    async def start_session(self, guild, channel, queue_ids):

        mode = await self.get_mode()
        team_count = 4 if mode == "4team" else 2

        clubs = await self.get_clubs(team_count)
        players = await self.get_players(queue_ids)

        whitelist = await self.get_whitelist()
        eligible = [p["id"] for p in players if p["id"] in whitelist]

        if len(eligible) >= team_count:
            captains = random.sample(eligible, team_count)
        else:
            captains = random.sample(queue_ids, min(team_count, len(queue_ids)))

        teams = TeamBalancer.balance(players, captains, clubs)

        category = discord.utils.get(guild.categories, name="In Progress")

        if category:
            for vc in category.voice_channels:
                await vc.delete()
        else:
            category = await guild.create_category("In Progress")

        captain_role = discord.utils.get(guild.roles, name="👑 Captain")

        if captain_role is None:
            captain_role = await guild.create_role(
                name="👑 Captain",
                colour=discord.Colour.gold()
            )

        voice_channels = {}

        for team in teams:

            vc = await guild.create_voice_channel(
                team["club"],
                category=category
            )

            voice_channels[team["club"]] = vc

        # Text channels

        async def ensure(name):

            existing = discord.utils.get(
                guild.text_channels,
                name=name
            )

            if existing:
                return existing

            return await guild.create_text_channel(name)

        live = await ensure("in-progress")

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

        # Give permissions

        for team in teams:

            vc = voice_channels[team["club"]]

            for i, player in enumerate(team["players"]):

                member = guild.get_member(player["id"])

                if member is None:
                    continue

                await vc.set_permissions(
                    member,
                    connect=True,
                    speak=True,
                    view_channel=True
                )

                if i == 0:
                    await member.add_roles(captain_role)

                if member.voice:
                    try:
                        await member.move_to(vc)
                    except:
                        pass

        # Fixtures

        if mode == "4team":

            fixtures = [
                (clubs[0], clubs[1]),
                (clubs[2], clubs[3])
            ]

        else:

            fixtures = [
                (clubs[0], clubs[1])
            ]

        # Live Hub

        embed = discord.Embed(
            title="⚽ NTF Session",
            description=f"**{'League Mode' if mode=='4team' else 'Rivals Mode'}**",
            colour=0x2EC4FF
        )

        for team in teams:

            text = ""

            for i, player in enumerate(team["players"]):

                member = guild.get_member(player["id"])

                if member is None:
                    continue

                if i == 0:
                    text += f"👑 {member.display_name}\n"
                else:
                    text += f"• {member.display_name}\n"

            embed.add_field(
                name=f"{team['club']} • {len(team['players'])}/6",
                value=text,
                inline=False
            )

        fixture_text = "\n".join(
            f"⚽ {a} vs {b}"
            for a, b in fixtures
        )

        embed.add_field(
            name="Current Fixtures",
            value=fixture_text,
            inline=False
        )

        standing_text = "\n".join(
            f"{club} — 0"
            for club in clubs
        )

        embed.add_field(
            name="Standings",
            value=standing_text,
            inline=False
        )

        embed.add_field(
            name="🪑 Bench",
            value="0/4 Slots Used",
            inline=False
        )

        await live.send(embed=embed)

        await control.send(
            "⚙️ Session created.\nWinner buttons arrive in the next update."
        )

async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
