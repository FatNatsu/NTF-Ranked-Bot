import aiosqlite

DB_NAME = "ntf.db"

DEFAULT_TEAMS = [
    "Fram Esports",
    "The Fifth Pass",
    "Warya Wonders",
    "Delectable XI",
    "Joyboi"
]

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS captains(
            user_id INTEGER PRIMARY KEY
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS teams(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players(
            user_id INTEGER PRIMARY KEY,
            mmr INTEGER DEFAULT 1000,
            role TEXT DEFAULT 'ANY'
        )
        """)

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

        for team in DEFAULT_TEAMS:
