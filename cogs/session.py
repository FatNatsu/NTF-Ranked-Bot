from dataclasses import dataclass, field
from typing import Dict, List
import random
import discord
from discord.ext import commands

@dataclass
class SessionData:
    session_id: int
    mode: str
    teams: Dict[str, List[int]]
    captains: Dict[str, int]
    round: int = 1
    standings: Dict[str, int] = field(default_factory=dict)

class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_counter = 1
        self.active_session = None

    def create_session(
        self,
        mode,
        clubs,
        captains,
        players
    ):

        teams = {club: [] for club in clubs}

        for club, captain in zip(clubs, captains):
            teams[club].append(captain)

        remaining = [p for p in players if p not in captains]
        random.shuffle(remaining)

        i = 0
        while remaining:
            club = clubs[i % len(clubs)]
            teams[club].append(remaining.pop(0))
            i += 1

        standings = {club: 0 for club in clubs}

        self.active_session = SessionData(
            session_id=self.session_counter,
            mode=mode,
            teams=teams,
            captains=dict(zip(clubs, captains)),
            standings=standings
        )

        self.session_counter += 1

        return self.active_session

    async def announce_session(
        self,
        guild,
        channel
    ):

        session = self.active_session

        embed = discord.Embed(
            title=f"⚽ NTF Session #{session.session_id}",
            description=f"**{session.mode}**",
            colour=0x2EC4FF
        )

        for club, members in session.teams.items():

            text = ""

            for i, member_id in enumerate(members):

                member = guild.get_member(member_id)

                if not member:
                    continue

                if i == 0:
                    text += f"👑 {member.mention}\n"
                else:
                    text += f"• {member.mention}\n"

            embed.add_field(
                name=club,
                value=text or "No players",
                inline=False
            )

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Session(bot))
