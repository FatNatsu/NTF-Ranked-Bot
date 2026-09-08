import math
import aiosqlite

DB_NAME = "ntf.db"


# -------------------------
# Rating helpers
# -------------------------

def get_rating(mmr: int):
    if mmr >= 2500:
        return "S+"
    if mmr >= 2200:
        return "S"
    if mmr >= 1900:
        return "A+"
    if mmr >= 1600:
        return "A"
    if mmr >= 1300:
        return "B+"
    if mmr >= 1000:
        return "B"
    if mmr >= 700:
        return "C+"
    if mmr >= 400:
        return "C"
    if mmr >= 200:
        return "D"
    return "E"


# -------------------------
# Base gain/loss values
# -------------------------

def get_base_values(avg_mmr):

    if avg_mmr >= 2500:
        return (12, 20)

    if avg_mmr >= 2200:
        return (14, 16)

    if avg_mmr >= 1900:
        return (16, 13)

    if avg_mmr >= 1600:
        return (18, 12)

    if avg_mmr >= 1300:
        return (20, 10)

    if avg_mmr >= 1000:
        return (22, 11)

    if avg_mmr >= 700:
        return (24, 12)

    if avg_mmr >= 400:
        return (28, 14)

    if avg_mmr >= 200:
        return (32, 16)

    return (36, 18)


# -------------------------
# Team average
# -------------------------

async def get_team_average(players):

    async with aiosqlite.connect(DB_NAME) as db:

        total = 0

        for player in players:

            cur = await db.execute(
                "SELECT mmr FROM players WHERE user_id=?",
                (player,)
            )

            row = await cur.fetchone()

            total += row[0] if row else 100

    return total / len(players)


# -------------------------
# Elo expectation
# -------------------------

def expected_score(a_avg, b_avg):

    return 1 / (1 + 10 ** ((b_avg - a_avg) / 400))


# -------------------------
# Calculate one match
# -------------------------

async def calculate_match(team_a, team_b, winner):

    avg_a = await get_team_average(team_a)
    avg_b = await get_team_average(team_b)

    win_gain, win_loss = get_base_values((avg_a + avg_b) / 2)

    expected_a = expected_score(avg_a, avg_b)
    expected_b = expected_score(avg_b, avg_a)

    if winner == "A":

        gain = round(win_gain + (1 - expected_a) * 10)
        loss = round(win_loss + expected_b * 4)

        return gain, -loss

    gain = round(win_gain + (1 - expected_b) * 10)
    loss = round(win_loss + expected_a * 4)

    return -loss, gain


# -------------------------
# Apply league session
# -------------------------

async def apply_league_session(session):

    changes = {}

    for match in session["results"]:

        team_a = session["teams"][match["team_a"]]["players"]
        team_b = session["teams"][match["team_b"]]["players"]

        a_change, b_change = await calculate_match(
            team_a,
            team_b,
            match["winner"]
        )

        for player in team_a:
            changes[player] = changes.get(player, 0) + a_change

        for player in team_b:
            changes[player] = changes.get(player, 0) + b_change

    async with aiosqlite.connect(DB_NAME) as db:

        for player, change in changes.items():

            change = max(-35, min(90, change))

            cur = await db.execute(
                "SELECT mmr,wins,losses,games_played FROM players WHERE user_id=?",
                (player,)
            )

            row = await cur.fetchone()

            if row:
                mmr, wins, losses, games = row
            else:
                mmr, wins, losses, games = (100, 0, 0, 0)

            new_mmr = max(100, mmr + change)

            result = "W" if change >= 0 else "L"

            if result == "W":
                wins += 1
            else:
                losses += 1

            games += 1

            await db.execute("""
            INSERT OR REPLACE INTO players
            (user_id,mmr,wins,losses,games_played)
            VALUES(?,?,?,?,?)
            """, (
                player,
                new_mmr,
                wins,
                losses,
                games
            ))

            await db.execute("""
            INSERT INTO recent_form(user_id,result)
            VALUES(?,?)
            """, (
                player,
                result
            ))

            await db.execute("""
            DELETE FROM recent_form
            WHERE rowid NOT IN(
                SELECT rowid
                FROM recent_form
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT 5
            )
            AND user_id=?
            """, (
                player,
                player
            ))

        await db.commit()

    return changes
