import random
import aiosqlite
import discord
from discord.ext import commands

DB_NAME = "ntf.db"

CLUB_POOL = [
    "Fram Esports",
    "Joyboi",
    "Warya Wonders",
    "The Fifth Pass",
    "NTF Eclipse",
    "Aether FC",
    "Vanguard",
    "Nova XI",
    "Phantom",
    "Inferno"
]


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

    async def generate_session_code(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM sessions"
            )
            count = (await cur.fetchone())[0] + 1

        return f"NTF-{count:04d}"

    async def get_player_mmr(self, user_id):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT mmr FROM players WHERE user_id=?",
                (user_id,)
            )
            row = await cur.fetchone()

            if row:
                return row[0]

            await db.execute(
                "INSERT OR IGNORE INTO players(user_id) VALUES(?)",
                (user_id,)
            )
            await db.commit()

        return 100

    async def get_captain_whitelist(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT user_id FROM captains"
            )
            rows = await cur.fetchall()

        return [r[0] for r in rows]

    async def choose_captains(self, players, amount):
        whitelist = await self.get_captain_whitelist()

        available = [p for p in players if p in whitelist]

        if len(available) < amount:
            raise ValueError(
                "Not enough whitelisted captains."
            )

        return random.sample(available, amount)

    async def snake_balance(self, players, captain_ids, club_names):

        player_data = []

        for player in players:
            player_data.append({
                "id": player,
                "mmr": await self.get_player_mmr(player)
            })

        player_data.sort(
            key=lambda x: x["mmr"],
            reverse=True
        )

        teams = {}

        for club, captain in zip(club_names, captain_ids):

            captain_mmr = next(
                p["mmr"]
                for p in player_data
                if p["id"] == captain
            )

            teams[club] = {
                "captain": captain,
                "players": [captain],
                "total": captain_mmr
            }

        remaining = [
            p for p in player_data
            if p["id"] not in captain_ids
        ]

        order = list(club_names)

        while remaining:

            for club in order:
                if not remaining:
                    break

                player = remaining.pop(0)

                teams[club]["players"].append(player["id"])
                teams[club]["total"] += player["mmr"]

            order.reverse()

        return teams

    async def create_voice_channels(
        self,
        guild,
        session_code,
        teams,
        captain_ids
    ):

        category = await guild.create_category(
            f"In Progress - {session_code}"
        )

        voice_channels = []

        captain_role = None

        for role in guild.roles:
            if role.name == "Captain":
                captain_role = role
                break

        if captain_role is None:
            captain_role = await guild.create_role(
                name="Captain"
            )

        for member_id in captain_ids:
            member = guild.get_member(member_id)
            if member:
                await member.add_roles(captain_role)

        for club in teams:

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    connect=False
                ),
                captain_role: discord.PermissionOverwrite(
                    connect=True,
                    speak=True
                )
            }

            for member_id in teams[club]["players"]:
                member = guild.get_member(member_id)
                if member:
                    overwrites[member] = discord.PermissionOverwrite(
                        connect=True,
                        speak=True
                    )

            vc = await guild.create_voice_channel(
                club,
                category=category,
                overwrites=overwrites
            )

            voice_channels.append(vc)

        bench = await guild.create_voice_channel(
            "🪑 Bench",
            category=category
        )

        voice_channels.append(bench)

        progress = await guild.create_text_channel(
            "in-progress",
            category=category
        )

        control = await guild.create_text_channel(
            "session-control",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=False
                )
            }
        )

        return (
            category,
            progress,
            control,
            voice_channels
        )

    async def start_session(self, guild, queue):

        mode = await self.get_mode()

        captain_count = 4 if mode == "4team" else 2

        session_code = await self.generate_session_code()

        club_names = random.sample(
            CLUB_POOL,
            captain_count
        )

        captains = await self.choose_captains(
            queue,
            captain_count
        )

        teams = await self.snake_balance(
            queue,
            captains,
            club_names
        )

        (
            category,
            progress,
            control,
            voice_channels
        ) = await self.create_voice_channels(
            guild,
            session_code,
            teams,
            captains
        )

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
            INSERT INTO sessions
            (session_code,mode,status)
            VALUES(?,?,?)
            """, (
                session_code,
                "League" if mode == "4team" else "Rivals",
                "active"
            ))
            await db.commit()

        session_cog = self.bot.get_cog("Session")

        if session_cog:

            await session_cog.register_session(
                guild=guild,
                session_code=session_code,
                mode="League" if mode == "4team" else "Rivals",
                teams=teams,
                category=category,
                progress_channel=progress,
                control_channel=control,
                voice_channels=voice_channels
            )


async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
