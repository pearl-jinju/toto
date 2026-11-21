"""Export historical Premier League scores as a Postgres import transaction."""

import argparse
import hashlib
import json
import re
from datetime import date
from urllib.request import urlopen


COMPLETE_SEASONS = ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26")
SOURCE = "https://raw.githubusercontent.com/openfootball/football.json/master"


def sql_text(value):
    return "'" + value.replace("'", "''") + "'"


def score_pair(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("Expected two scores")
    if any(type(goals) is not int or goals < 0 for goals in value):
        raise ValueError("Expected nonnegative integer scores")
    return value


def read_season(season):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", season):
        raise ValueError(f"Invalid season: {season}")
    url = f"{SOURCE}/{season}/en.1.json"
    with urlopen(url, timeout=30) as response:
        payload = response.read()

    fixtures = json.loads(payload)["matches"]
    rows = []
    for fixture in fixtures:
        score = fixture["score"]
        if isinstance(score, dict):
            full = score_pair(score["ft"])
            half = score.get("ht")
        else:
            full = score_pair(score)
            half = None
        # A goalless full-time result also establishes a goalless first half.
        if half is None and full == [0, 0]:
            half = full
        if half is not None:
            half = score_pair(half)
            if any(before > after for before, after in zip(half, full)):
                raise ValueError(f"Inconsistent score: {fixture}")

        match_date = date.fromisoformat(fixture["date"]).isoformat()
        home, away = fixture["team1"], fixture["team2"]
        rows.append([match_date, home, away, *(half or [None, None]), *full])

    pairings = {(row[1], row[2]) for row in rows}
    if len(rows) != 380 or len(pairings) != len(rows):
        raise ValueError(f"{season} is not a complete 380-match Premier League season")
    return url, hashlib.sha256(payload).hexdigest(), rows


def season_sql(season):
    url, digest, rows = read_season(season)
    values = sql_text(json.dumps(rows, ensure_ascii=True, separators=(",", ":")))
    league_code = "'EPL'"
    season_value = sql_text(season)
    return f"""
INSERT INTO historical_football_season (league_code, season, source_url, source_sha256)
VALUES ({league_code}, {season_value}, {sql_text(url)}, {sql_text(digest)})
ON CONFLICT (league_code, season) DO UPDATE
SET source_url = excluded.source_url,
    source_sha256 = excluded.source_sha256,
    imported_at = now()
WHERE historical_football_season.source_sha256 <> excluded.source_sha256
   OR historical_football_season.source_url <> excluded.source_url;

INSERT INTO historical_football_match
    (league_code, season, match_date, home_team, away_team, ht_home, ht_away, ft_home, ft_away)
SELECT {league_code}, {season_value}, (item->>0)::date, item->>1, item->>2,
       (item->>3)::smallint, (item->>4)::smallint, (item->>5)::smallint, (item->>6)::smallint
FROM jsonb_array_elements({values}::jsonb) AS item
ON CONFLICT (league_code, season, home_team, away_team) DO UPDATE
SET match_date = excluded.match_date,
    ht_home = excluded.ht_home,
    ht_away = excluded.ht_away,
    ft_home = excluded.ft_home,
    ft_away = excluded.ft_away;
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seasons", nargs="*", default=COMPLETE_SEASONS,
                        help="Completed EPL seasons, e.g. 2025-26. Defaults to 2021-22 through 2025-26.")
    args = parser.parse_args()
    statements = [season_sql(season) for season in args.seasons]
    print("-- OpenFootball public-domain scores: https://github.com/openfootball/football.json")
    print("BEGIN;")
    print("\n".join(statements))
    print("COMMIT;")
