import aiosqlite
import math

DB_NAME = "ntf.db"

# ---------- Database ----------

async def get_player_mmr(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT mmr FROM players WHERE user_id=?",
            (user_id,)
        )
        row = await cur.fetchone()

        if row:
            return row[0]

        await db.execute(
            "INSERT OR IGNORE INTO players(user_id, mmr) VALUES(?,?)",
            (user_id, 100)
        )
        await db.commit()

        return 100


async def update_player_mmr(user_id, change):
    current = await get_player_mmr(user_id)
    new = max(100, round(current + change))

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE players SET mmr=? WHERE user_id=?",
            (new, user_id)
        )
        await db.commit()

    return new


# ---------- Team Helpers ----------

async def get_team_average(team):
    players = team["players"]

    # Prevent crashes while testing with empty teams
    if not players:
        return 100

    total = 0

    for player in players:
        total += await get_player_mmr(player)

    return total / len(players)


def expected_score(a, b):
    return 1 / (1 + math.pow(10, (b - a) / 400))


def get_win_gain(avg):
    if avg >= 2200:
        return 20
    if avg >= 1600:
        return 22
    return 24


def get_loss_penalty(avg):
    if avg >= 2500:
        return -20
    if avg >= 2200:
        return -16
    if avg >= 1600:
        return -12
    if avg >= 1000:
        return -10
    return -8


# ---------- Match Calculation ----------

async def calculate_match(team_a, team_b, winner):

    avg_a = await get_team_average(team_a)
    avg_b = await get_team_average(team_b)

    expected_a = expected_score(avg_a, avg_b)
    expected_b = expected_score(avg_b, avg_a)

    gain_a = get_win_gain(avg_a)
    gain_b = get_win_gain(avg_b)

    loss_a = get_loss_penalty(avg_a)
    loss_b = get_loss_penalty(avg_b)

    if winner == "A":
        a_change = round(gain_a * (1 - expected_a))
        b_change = round(loss_b * expected_b)
    else:
        b_change = round(gain_b * (1 - expected_b))
        a_change = round(loss_a * expected_a)

    return a_change, b_change


# ---------- League Session ----------

async def apply_league_session(session):

    teams = session["teams"]

    changes = {}

    for team in teams.values():
        for player in team["players"]:
            changes[player] = 0

    for result in session["results"]:

        team_a = teams[result["team_a"]]
        team_b = teams[result["team_b"]]

        a_change, b_change = await calculate_match(
            team_a,
            team_b,
            result["winner"]
        )

        for player in team_a["players"]:
            changes[player] += a_change

        for player in team_b["players"]:
            changes[player] += b_change

    for player, change in changes.items():
        await update_player_mmr(player, change)

    return changes
