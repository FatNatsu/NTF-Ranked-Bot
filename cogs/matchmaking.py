            number = (await cur.fetchone())[0] + 1

        return f"NTF-{number:04d}"

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

    async def get_whitelist(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT user_id FROM captains"
            )
            rows = await cur.fetchall()

        return [r[0] for r in rows]

    async def choose_captains(self, players, amount):
        whitelist = await self.get_whitelist()

        captains = [p for p in players if p in whitelist][:amount]

        for player in players:
            if len(captains) >= amount:
                break
            if player not in captains:
                captains.append(player)

        while len(captains) < amount:
            captains.append(None)

        return captains

    async def build_teams(self, players, captains, clubs):

        data = []

        for p in players:
            data.append({
                "id": p,
                "mmr": await self.get_player_mmr(p)
            })

        data.sort(key=lambda x: x["mmr"], reverse=True)

        teams = {}

        for club, captain in zip(clubs, captains):

            teams[club] = {
                "captain": captain,
                "players": []
            }

            if captain is not None:
                teams[club]["players"].append(captain)

        remaining = [
            p for p in data
            if p["id"] not in [c for c in captains if c]
        ]

        order = clubs[:]

        while remaining:

            for club in order:

                if not remaining:
                    break

                if len(teams[club]["players"]) >= 6:
                    continue

                teams[club]["players"].append(
                    remaining.pop(0)["id"]
                )

            order.reverse()

        return teams

    async def create_channels(
        self,
        guild,
        session_code,
        teams,
        captains
    ):

        category = await guild.create_category(
            f"In Progress - {session_code}"
        )

        voice_channels = []

        for club in teams:

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    connect=False
                )
            }

            for uid in teams[club]["players"]:

                member = guild.get_member(uid)
        team_count = 4 if mode == "4team" else 2

        clubs = random.sample(
            CLUB_POOL,
            team_count
        )

        captains = await self.choose_captains(
            queue,
            team_count
        )

        teams = await self.build_teams(
            queue,
            captains,
            clubs
        )

        session_code = await self.generate_session_code()

        (
            category,
            progress,
            control,
            vcs
        ) = await self.create_channels(
            guild,
            session_code,
            teams,
            captains
        )

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
            INSERT INTO sessions(session_code,mode,status)
            VALUES(?,?,?)
            """, (
                session_code,
                "League" if team_count == 4 else "Rivals",
                "active"
            ))
            await db.commit()

        session = self.bot.get_cog("Session")

        if session:

            await session.register_session(
                guild=guild,
                session_code=session_code,
                mode="League" if team_count == 4 else "Rivals",
                teams=teams,
                category=category,
                progress_channel=progress,
                control_channel=control,
                voice_channels=vcs
            )


async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
