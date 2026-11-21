"""Aggregate half-time patterns from an OpenFootball season JSON file."""

import argparse
import json
from pathlib import Path


def aggregate(season):
    scores = []
    for fixture in season["matches"]:
        score = fixture["score"]
        full_time = tuple(score["ft"] if isinstance(score, dict) else score)
        half_time = score.get("ht") if isinstance(score, dict) else None
        if half_time is None and full_time == (0, 0):
            half_time = (0, 0)
        if half_time is None or any(half > full for half, full in zip(half_time, full_time)):
            raise ValueError(f"Invalid half-time score: {fixture}")
        scores.append((tuple(half_time), full_time))

    def totals(group):
        return {"matches": len(group), "under": [sum(sum(full) < line for _, full in group)
                                                 for line in (2.5, 3.5, 4.5)]}

    def lead(group):
        wins = sum((half[0] - half[1]) * (full[0] - full[1]) > 0 for half, full in group)
        draws = sum(full[0] == full[1] for _, full in group)
        return {"matches": len(group), "wins": wins, "draws": draws, "losses": len(group) - wins - draws}

    return {
        "all": totals(scores),
        "half_total_two": totals([(half, full) for half, full in scores if sum(half) == 2]),
        "half_one_team_two": totals([(half, full) for half, full in scores if 2 in half]),
        "half_two_splits": {
            f"{home}-{away}": totals([(half, full) for half, full in scores if half == (home, away)])
            for home, away in ((2, 0), (1, 1), (0, 2))
        },
        "half_goal_lead": {
            str(margin): lead([(half, full) for half, full in scores if abs(half[0] - half[1]) == margin])
            for margin in (1, 2)
        },
        "half_goalless": {
            "matches": sum(half == (0, 0) for half, _ in scores),
            "goalless": sum(full == (0, 0) for _, full in scores),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("season", type=Path, help="OpenFootball season JSON")
    args = parser.parse_args()
    season_data = json.loads(args.season.read_text(encoding="utf-8-sig"))
    print(json.dumps(aggregate(season_data), indent=2))
