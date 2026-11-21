import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


CATALOG = {
    "잉글랜드 프리미어리그": ("en.1", "Europe/London", False),
    "잉글랜드 챔피언십": ("en.2", "Europe/London", False),
    "독일 분데스리가": ("de.1", "Europe/Berlin", False),
    "독일 분데스리가2": ("de.2", "Europe/Berlin", False),
    "프랑스 리그1": ("fr.1", "Europe/Paris", False),
    "프랑스 리그2": ("fr.2", "Europe/Paris", False),
    "스페인 라리가": ("es.1", "Europe/Madrid", False),
    "이탈리아 세리에A": ("it.1", "Europe/Rome", False),
    "네덜란드 에레디비시": ("nl.1", "Europe/Amsterdam", False),
    "포르투갈 프리메이라리가": ("pt.1", "Europe/Lisbon", False),
    "호주 A리그": ("au.1", "Australia/Sydney", False),
    "일본 J1리그": ("jp.1", "Asia/Tokyo", False),
    "일본 J2리그": ("jp.2", "Asia/Tokyo", False),
    "K리그1": ("kr.1", "Asia/Seoul", True),
    "K리그2": ("kr.2", "Asia/Seoul", True),
    "미국 메이저리그사커": ("us.1", "America/New_York", True),
}
ROOT = "https://raw.githubusercontent.com/openfootball/football.json/master"
SOURCE = "https://github.com/openfootball/football.json/blob/master"
OP_TIMEOUT = 7
_cache = {}
_lock = Lock()


def seasons(year, month, calendar_year):
    if calendar_year:
        return [str(year), str(year - 1)]
    first = year if month >= 7 else year - 1
    return [f"{y}-{(y + 1) % 100:02d}" for y in (first, first - 1, first - 2)]


def load_season(path):
    with _lock:
        cached = _cache.get(path)
    if cached and monotonic() < cached[0]:
        return cached[1]
    lifetime = 3600
    try:
        request = Request(f"{ROOT}/{path}", headers={"User-Agent": "MatchIndex/1.0"})
        with urlopen(request, timeout=OP_TIMEOUT) as response:
            payload = json.load(response)
        matches = payload["matches"]
    except HTTPError as error:
        matches = []
        if error.code != 404:
            lifetime = 600
    except (OSError, ValueError, KeyError, TypeError):
        matches = []
        lifetime = 600
    with _lock:
        if not matches and cached and cached[1]:
            matches = cached[1]
        _cache[path] = (monotonic() + lifetime, matches)
    return matches


def scores(value):
    return value if isinstance(value, list) and len(value) == 2 and all(type(n) is int and n >= 0 for n in value) else None


def fetch_events(fixtures):
    leagues = sorted({fixture["league"] for fixture in fixtures} & CATALOG.keys())
    tasks = []
    for league in leagues:
        code, zone, calendar_year = CATALOG[league]
        kickoff = datetime.fromisoformat(next(f["startsAt"] for f in fixtures if f["league"] == league))
        sets = seasons(kickoff.year, kickoff.month, calendar_year)
        tasks.extend((league, zone, f"{season}/{code}.json", league.startswith("미국")) for season in sets)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(load_season, (path for _, _, path, _ in tasks)))
    events = []
    coverage = {league: "no_data" for league in leagues}
    for (league, zone, path, date_only), rows in zip(tasks, results):
        for row in rows:
            if not all(row.get(key) for key in ("date", "team1", "team2")):
                continue
            raw_score = row.get("score")
            score = scores(raw_score.get("ft")) if isinstance(raw_score, dict) else scores(raw_score)
            half = scores(raw_score.get("ht")) if isinstance(raw_score, dict) else None
            if score is None:
                continue
            exact_time = row.get("time") if not date_only else None
            try:
                local = datetime.fromisoformat(row["date"] + "T" + (exact_time or "23:59")).replace(tzinfo=ZoneInfo(zone))
            except (ValueError, TypeError):
                continue
            events.append({
                "provider": "openfootball", "league": league, "id": f"{row['date']}|{row['team1']}|{row['team2']}",
                "start": local.astimezone(timezone.utc).isoformat(), "dateOnly": not bool(exact_time),
                "home": row["team1"], "away": row["team2"], "complete": True,
                "score": score, "half": half,
                "source": ["OpenFootball · 공개 경기 이력", f"{SOURCE}/{path}"],
            })
            coverage[league] = "verified"
    return {"events": events, "coverage": coverage}
