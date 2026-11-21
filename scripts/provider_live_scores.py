"""Short-lived scoreboard lookups for unresolved Betman fixtures."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.client import HTTPException
import json
import re
from threading import Lock
from time import monotonic
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from scripts.fixture_matching import KST, pair, score_of, team_key, timestamp
from scripts.provider_domestic import J_LEAGUES, K_LEAGUES, jleague_for_season, kleague_for_month
from scripts.provider_wkbl import wkbl_for_month


ESPN_ORIGIN = "https://site.api.espn.com/apis/site/v2/sports"
MLB_SCHEDULE = "https://statsapi.mlb.com/api/v1/schedule"
KOVO_ORIGIN = "https://user-api.kovo.co.kr"
KOVO_TEAMS = {
    "1001": "대한항공 점보스", "1002": "삼성화재 블루팡스", "1004": "KB손해보험 스타즈",
    "1005": "현대캐피탈 스카이워커스", "1006": "한국전력 빅스톰", "1008": "OK저축은행 읏맨",
    "1009": "우리카드 우리WON", "2001": "현대건설 힐스테이트", "2002": "한국도로공사 하이패스",
    "2003": "정관장 레드스파크스", "2004": "흥국생명 핑크스파이더스", "2005": "GS칼텍스 서울KIXX",
    "2006": "IBK기업은행 알토스", "2008": "SOOP 수퍼스",
}
_FALLBACK_CACHE = {}
_FALLBACK_LOCK = Lock()
SOURCE_HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 MatchIndex"}
KICKOFF_TOLERANCE = timedelta(minutes=25)
SCOREBOARDS = {
    "NBA": "basketball/nba",
    "미국 메이저리그사커": "soccer/usa.1",
    "호주 A리그": "soccer/aus.1",
    "일본 J1리그": "soccer/jpn.1",
    "독일 분데스리가": "soccer/ger.1",
    "독일 분데스리가2": "soccer/ger.2",
    "잉글랜드 프리미어리그": "soccer/eng.1",
    "잉글랜드 챔피언십": "soccer/eng.2",
    "스페인 라리가": "soccer/esp.1",
    "스페인 세군다리가": "soccer/esp.2",
    "이탈리아 세리에A": "soccer/ita.1",
    "이탈리아 세리에B": "soccer/ita.2",
    "프랑스 리그1": "soccer/fra.1",
    "프랑스 리그2": "soccer/fra.2",
    "네덜란드 에레디비시": "soccer/ned.1",
    "포르투갈 프리메이라리가": "soccer/por.1",
    "UEFA 챔피언스리그": "soccer/uefa.champions",
    "UEFA 유로파리그": "soccer/uefa.europa",
    "UEFA 컨퍼런스리그": "soccer/uefa.europa.conf",
    "AFC 챔피언스리그 엘리트": "soccer/afc.champions",
}
try:
    EASTERN = ZoneInfo("America/New_York")
except ZoneInfoNotFoundError:
    EASTERN = timezone(timedelta(hours=-5))


def _fetch(url):
    with urlopen(Request(url, headers=SOURCE_HEADERS), timeout=7) as response:
        body = response.read(3_000_001)
    if len(body) > 3_000_000:
        raise ValueError("Oversized scoreboard")
    return json.loads(body)


def _number(value):
    if type(value) is int and 0 <= value <= 1000:
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{1,3}", value):
        return int(value)
    return None


def _pair_score(home, away):
    values = [_number(home), _number(away)]
    return values if None not in values else None


def _state(value):
    kind = str(value.get("name", "")).upper()
    description = str(value.get("description", "")).upper()
    label = f"{kind} {description}"
    if any(word in label for word in ("CANCEL", "ABANDON", "FORFEIT")):
        return None
    if "POSTPON" in label:
        return "postponed"
    if any(word in label for word in ("DELAY", "SUSPEND", "INTERRUPT")):
        return "delayed"
    if value.get("completed") is True and value.get("state") == "post":
        return "final"
    return {"in": "live", "pre": "scheduled"}.get(value.get("state"))


def _soccer_time(status):
    period = _number(status.get("period"))
    kind = status.get("type", {}).get("name", "")
    if kind == "STATUS_HALFTIME":
        return "전반 종료", None, 45
    if kind == "STATUS_SHOOTOUT":
        return "승부차기", None, None
    label = {1: "전반", 2: "후반", 3: "연장 전반", 4: "연장 후반"}.get(period)
    raw = str(status.get("displayClock", "")).strip()
    clock = re.fullmatch(r"(\d{1,3})(?::[0-5]\d)?\s*['′]?(?:\s*\+\s*(\d{1,2})\s*['′]?)?", raw)
    if not clock:
        return label, None, None
    elapsed = int(clock[1])
    if (not label and elapsed == 0) or elapsed > 150:
        return label, None, None
    added = int(clock[2]) if clock[2] else 0
    return label, f"{elapsed}+{added}분" if added else f"{elapsed}분", elapsed


def _basketball_time(status):
    quarter = _number(status.get("period"))
    kind = status.get("type", {}).get("name", "")
    if kind == "STATUS_HALFTIME":
        return "하프타임", None
    label = f"{quarter}쿼터" if quarter and quarter <= 4 else f"{quarter-4}차 연장" if quarter else None
    clock = str(status.get("displayClock", "")).strip()
    return label, clock if re.fullmatch(r"(?:\d{1,2}:[0-5]\d|\d{1,2}\.\d{1,2})", clock) else None


def _event(league, identifier, starts, home, away, state, score, source, *, period=None, clock=None,
           elapsed=None, priority=1):
    if not identifier or timestamp(starts) is None or not all((home, away, state)):
        return None
    if state in {"live", "final"} and score is None:
        return None
    return {
        "league": league, "id": identifier, "start": starts, "home": home, "away": away,
        "state": state, "score": score if state in {"live", "final", "delayed"} else None,
        "source": source, "period": period, "clock": clock, "elapsedMinutes": elapsed, "priority": priority,
    }


def _espn_event(raw, league, path):
    competitions = raw.get("competitions", [])
    if len(competitions) != 1:
        return None
    game = competitions[0]
    sides = {row.get("homeAway"): row for row in game["competitors"]}
    if set(sides) != {"home", "away"} or len(game["competitors"]) != 2:
        return None
    home, away = sides["home"], sides["away"]
    status = raw.get("status") or game["status"]
    state = _state(status["type"])
    identifier = str(raw["id"])
    if not re.fullmatch(r"\d{5,15}", identifier):
        return None
    source = (["ESPN · NBA 경기 점수", f"https://www.espn.com/nba/game/_/gameId/{identifier}"]
              if league == "NBA" else ["ESPN · 축구 경기 점수", f"https://www.espn.com/soccer/match/_/gameId/{identifier}"])
    elapsed = None
    clock = period = None
    if state == "live":
        if path.startswith("soccer/"):
            period, clock, elapsed = _soccer_time(status)
        else:
            period, clock = _basketball_time(status)
    return _event(league, identifier, game.get("date") or raw["date"], home["team"]["displayName"],
                  away["team"]["displayName"], state, _pair_score(home.get("score"), away.get("score")), source,
                  period=period, clock=clock, elapsed=elapsed)


def _parse(raw_events, normalize):
    rows = []
    for raw in raw_events:
        try:
            event = normalize(raw)
        except (AttributeError, KeyError, TypeError, ValueError, IndexError):
            continue
        if event:
            rows.append(event)
    return rows


def _espn(league, path, day):
    body = _fetch(f"{ESPN_ORIGIN}/{path}/scoreboard?dates={day:%Y%m%d}")
    return _parse(body["events"], lambda raw: _espn_event(raw, league, path))


def _mlb(league, day):
    url = f"{MLB_SCHEDULE}?" + urlencode({"sportId": 1, "date": day.isoformat(), "hydrate": "linescore"})
    body = _fetch(url)

    def record(game):
        home, away = game["teams"]["home"], game["teams"]["away"]
        status = game["status"]
        label = status["detailedState"].lower()
        phase = status["abstractGameState"]
        if "cancel" in label or "forfeit" in label:
            return None
        if "postpon" in label:
            state = "postponed"
        elif "delay" in label or "suspend" in label:
            state = "delayed"
        else:
            state = {"Live": "live", "Final": "final", "Preview": "scheduled"}.get(phase)
        innings = game.get("linescore", {})
        inning = _number(innings.get("currentInning"))
        side = {"Top": "초", "Bottom": "말", "Middle": "초 종료", "End": "말 종료"}.get(innings.get("inningState"))
        period = f"{inning}회{side}" if state == "live" and inning and side else None
        identifier = str(game["gamePk"])
        if not re.fullmatch(r"\d{5,12}", identifier) or game.get("gameType") not in {"R", "F", "D", "L", "W", "P"}:
            return None
        return _event(league, identifier, game["gameDate"], home["team"]["name"], away["team"]["name"],
                      state, _pair_score(home.get("score"), away.get("score")),
                      ["MLB · 공식 경기 점수", f"https://www.mlb.com/gameday/{identifier}"], period=period, priority=0)

    return _parse((game for day in body["dates"] for game in day["games"]), record)


def _cached_fallback(key, load, ttl=180):
    now = monotonic()
    with _FALLBACK_LOCK:
        saved = _FALLBACK_CACHE.get(key)
        if saved and saved[0] > now:
            return saved[1]
    result = load()
    with _FALLBACK_LOCK:
        for stale in [key for key, (expires, _) in _FALLBACK_CACHE.items() if expires <= now]:
            del _FALLBACK_CACHE[stale]
        _FALLBACK_CACHE[key] = (monotonic() + ttl, result)
    return result


def _domestic_results(provider, args):
    key = args if provider is not wkbl_for_month else (*args[:2], tuple(sorted(args[2].items())))
    records = _cached_fallback((provider, key), lambda: provider(*args))
    return [
        {**row, "state": "final", "priority": 0}
        for row in records
        if row.get("complete") and not row.get("dateOnly") and score_of(row.get("score")) is not None
    ]


def _kovo(dates):
    seasons = _cached_fallback("kovo-seasons", lambda: _fetch(f"{KOVO_ORIGIN}/matches/001/seasons")["payload"], 43200)
    season_ids = {
        row["season"] for row in seasons
        if re.fullmatch(r"\d{3}", row["season"])
        and any(row["openedAt"] <= day.isoformat() <= row["closedAt"] for day in dates)
    }

    def event(raw, season):
        starts = datetime.fromisoformat(f"{raw['gdate']}T{raw['gstime']}:00").replace(tzinfo=KST)
        league = {"1": "KOVO 남자", "2": "KOVO 여자"}.get(raw["gender"])
        score = _pair_score(raw.get("hspoint"), raw.get("aspoint"))
        if (starts.date() not in dates or not league or not score or max(score) != 3 or min(score) > 2
                or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", raw.get("getime", ""))
                or raw.get("result") not in {"W", "L"}):
            return None
        return _event(league, f"{season}-{raw['gnum']}", starts.isoformat(),
                      KOVO_TEAMS.get(raw["hcode"]), KOVO_TEAMS.get(raw["acode"]), "final", score,
                      ["KOVO · 공식 경기 결과", f"https://kovo.co.kr/games/v-league?category=schedule&season={season}"],
                      priority=0)

    rows = []
    for season in season_ids:
        url = f"{KOVO_ORIGIN}/stat/game-schedule?gcode=001&seasonCode={season}&leagueCode=201"
        matches = _cached_fallback(("kovo-schedule", season), lambda: _fetch(url)["payload"]["content"])
        rows.extend(_parse(matches, lambda raw: event(raw, season)))
    return rows


def _safe_fetch(job, args):
    try:
        return job(*args)
    except (OSError, HTTPException, ValueError, AttributeError, KeyError, TypeError, IndexError):
        return []


def _project(fixture, when, candidates):
    matching = [
        row for row in candidates
        if abs(timestamp(row["start"]) - when) <= KICKOFF_TOLERANCE
    ]
    if not matching:
        return None
    providers = defaultdict(set)
    for row in matching:
        providers[row["source"][0]].add(row["id"])
    if any(len(ids) > 1 for ids in providers.values()):
        return None
    endings = [row for row in matching if row["state"] == "final"]
    if endings and len({tuple(row["score"]) for row in endings}) != 1:
        return None
    matching = endings or matching
    order = {"final": 0, "live": 1, "delayed": 1, "postponed": 1, "scheduled": 2}
    matching.sort(key=lambda row: (order[row["state"]], row["priority"], abs(timestamp(row["start"]) - when)))
    best = matching[0]
    keys = ("state", "score", "source", "clock", "period", "elapsedMinutes")
    return {
        **{key: fixture[key] for key in ("home", "away", "startsAt")},
        **{key: best[key] for key in keys if best.get(key) is not None},
    }


def fetch_live_scores(fixtures):
    """Poll only eligible league/day feeds. Match league, oriented names and scheduled time."""
    candidates = []
    jobs = set()
    wkbl_months = set()
    kovo_dates = set()
    wkbl_current = defaultdict(list)
    now = datetime.now(timezone.utc)
    for fixture in fixtures:
        start = timestamp(fixture.get("startsAt"))
        league = fixture.get("league")
        home, away = pair(fixture)
        if (not start or start > now or not all((home, away)) or home == away
                or fixture.get("result") is not None or fixture.get("status") in {"cancelled", "finished"}):
            continue
        candidates.append((fixture, start, (league, home, away)))
        day = start.astimezone(EASTERN).date() if league in {"NBA", "미국 메이저리그사커"} else start.date()
        if league in SCOREBOARDS:
            jobs.add((_espn, (league, SCOREBOARDS[league], day)))
        if league in {"MLB", "미국 메이저리그"} and fixture.get("sport") == "야구":
            jobs.add((_mlb, (league, start.astimezone(EASTERN).date())))
        local = start.astimezone(KST)
        month = (local.year, local.month)
        if league in J_LEAGUES:
            season = local.year - int(local.year >= 2027 and local.month < 7)
            jobs.add((_domestic_results, (jleague_for_season, (league, season))))
        if league in K_LEAGUES.values():
            jobs.add((_domestic_results, (kleague_for_month, month)))
        if league in {"KOVO 남자", "KOVO 여자"}:
            kovo_dates.add(local.date())
        if league == "WKBL":
            wkbl_months.add(month)
            wkbl_current[(local.date().isoformat(), fixture["home"], fixture["away"])].append(fixture["startsAt"])

    if kovo_dates:
        jobs.add((_kovo, (tuple(sorted(kovo_dates)),)))
    if not jobs and not wkbl_months:
        return {}
    current = {key: values[0] for key, values in wkbl_current.items() if len(values) == 1}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_safe_fetch, job, args) for job, args in jobs]
        futures.extend(pool.submit(_safe_fetch, _domestic_results, (wkbl_for_month, (*month, current)))
                       for month in wkbl_months)
        index = defaultdict(list)
        for future in futures:
            for row in future.result():
                index[(row["league"], team_key(row["home"]), team_key(row["away"]))].append(row)
    return {
        fixture["number"]: result
        for fixture, when, key in candidates
        if (result := _project(fixture, when, index.get(key, []))) is not None
    }
