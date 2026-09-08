import aiosqlite

DB_NAME = "ntf.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        # -------------------------
        # Players
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS players(
            user_id INTEGER PRIMARY KEY,
            mmr INTEGER DEFAULT 100,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0
        )
        """)

        # -------------------------
        # Settings
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        await db.execute("""
        INSERT OR IGNORE INTO settings(key,value)
        VALUES('match_mode','4team')
        """)

        # -------------------------
        # Captain Whitelist
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS captains(
            user_id INTEGER PRIMARY KEY
        )
        """)

        # -------------------------
        # Teams
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS teams(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """)

        default_teams = [
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

        for team in default_teams:
            await db.execute(
                "INSERT OR IGNORE INTO teams(name) VALUES(?)",
                (team,)
            )

        # -------------------------
        # Sessions
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_code TEXT UNIQUE,
            mode TEXT,
            winner TEXT,
            status TEXT DEFAULT 'active',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # -------------------------
        # Matches
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS matches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            round INTEGER,
            team_a TEXT,
            team_b TEXT,
            winner TEXT,
            mmr_change INTEGER DEFAULT 0
        )
        """)

        # -------------------------
        # Club Legacy
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS club_stats(
            club_name TEXT PRIMARY KEY,
            championships INTEGER DEFAULT 0,
            session_wins INTEGER DEFAULT 0,
            highest_avg_mmr INTEGER DEFAULT 100,
            longest_win_streak INTEGER DEFAULT 0,
            current_win_streak INTEGER DEFAULT 0
        )
        """)

        for team in default_teams:
            await db.execute("""
            INSERT OR IGNORE INTO club_stats(club_name)
            VALUES(?)
            """, (team,))

        # -------------------------
        # Player Club History
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS club_history(
            user_id INTEGER,
            club_name TEXT,
            wins INTEGER DEFAULT 0,
            matches INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, club_name)
        )
        """)

        # -------------------------
        # Recent Form
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS recent_form(
            user_id INTEGER,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # -------------------------
        # Leaderboard Message
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard_message(
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            message_id INTEGER
        )
        """)

        # -------------------------
        # Hall of Fame Message
        # -------------------------
        await db.execute("""
        CREATE TABLE IF NOT EXISTS halloffame_message(
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            message_id INTEGER
        )
        """)

        await db.commit()
