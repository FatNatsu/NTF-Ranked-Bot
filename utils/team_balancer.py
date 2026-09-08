from collections import defaultdict

class TeamBalancer:
    @staticmethod
    def balance(players, captains, clubs):
        """
        players = [
            {"id":123,"mmr":1000,"role":"ANY"},
            ...
        ]

        captains = [123,456,...]
        clubs = ["Fram Esports", ...]
        """

        teams = []

        # Build captain teams first
        for club, captain_id in zip(clubs, captains):
            captain = next(p for p in players if p["id"] == captain_id)

            teams.append({
                "club": club,
                "captain": captain,
                "players": [captain],
                "mmr": captain["mmr"]
            })

        remaining = [
            p for p in players
            if p["id"] not in captains
        ]

        # Highest MMR first
        remaining.sort(
            key=lambda x: x["mmr"],
            reverse=True
        )

        for player in remaining:

            lowest = min(
                teams,
                key=lambda t: (
                    len(t["players"]),
                    t["mmr"]
                )
            )

            lowest["players"].append(player)
            lowest["mmr"] += player["mmr"]

        return teams

    @staticmethod
    def average(team):

        if not team["players"]:
            return 0

        return round(
            team["mmr"] / len(team["players"])
        )
