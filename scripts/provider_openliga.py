"""OpenLigaDB match data (ODbL 1.0; https://www.openligadb.de/lizenz)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from http.client import HTTPException
import json
from threading import Lock
from time import monotonic
from urllib.request import Request, urlopen


ORIGIN = "https://api.openligadb.de"
SOURCE_NAME = "OpenLigaDB · ODbL 1.0"
LEAGUE_CODES = {
    "독일 분데스리가": "bl1",
    "독일 분데스리가2": "bl2",
    "잉글랜드 프리미어리그": "pl",
    "네덜란드 에레디비시": "ERE",
}
TEAM_NAMES = {
    "fc bayern münchen": "바이에른 뮌헨",
    "1. fc köln": "쾰른",
    "bayer 04 leverkusen": "바이어04 레버쿠젠",
    "sc paderborn 07": "파더보른07",
    "eintracht frankfurt": "프랑크푸르트",
    "tsg 1899 hoffenheim": "TSG1899 호펜하임",
    "tsg hoffenheim": "TSG1899 호펜하임",
    "1. fc union berlin": "우니온 베를린",
    "rb leipzig": "RB라이프치히",
    "borussia mönchengladbach": "묀헨글라트바흐",
    "borussia dortmund": "도르트문트",
    "sv elversberg": "엘버스베르크",
    "sv 07 elversberg": "엘버스베르크",
    "sc freiburg": "SC프라이부르크",
    "fc schalke 04": "샬케04",
    "vfb stuttgart": "VfB슈투트가르트",
    "fc augsburg": "아우크스부르크",
    "1. fsv mainz 05": "FSV마인츠05",
    "sv werder bremen": "베르더 브레멘",
    "hamburger sv": "함부르크",
    "vfl wolfsburg": "볼프스부르크",
    "fc st. pauli": "장크트파울리",
    "1. fc heidenheim 1846": "하이덴하임",
    "1. fc kaiserslautern": "카이저슬라우테른",
    "hertha bsc": "헤르타 BSC",
    "fortuna düsseldorf": "뒤셀도르프",
    "hannover 96": "하노버96",
    "holstein kiel": "홀슈타인 킬",
    "manchester city": "맨체스터 시티",
    "fulham fc": "풀럼",
    "afc bournemouth": "AFC본머스",
    "nottingham forest": "노팅엄 포리스트",
    "aston villa": "애스턴 빌라",
    "sunderland": "선덜랜드",
    "chelsea fc": "첼시",
    "leeds united": "리즈 유나이티드",
    "coventry city": "코번트리 시티",
    "crystal palace fc": "크리스털 팰리스",
    "tottenham hotspur fc": "토트넘 홋스퍼",
    "ipswich town": "입스위치 타운",
    "newcastle united fc": "뉴캐슬 유나이티드",
    "fc arsenal": "아스널",
    "hull city": "헐 시티",
    "brighton & hove albion": "브라이턴&호브 앨비언",
    "fc liverpool": "리버풀",
    "manchester united fc": "맨체스터 유나이티드",
    "brentford f.c.": "브렌트퍼드",
    "everton fc": "에버턴",
    "nec nijmegen": "NEC네이메헌",
    "psv eindhoven": "PSV에인트호번",
    "fc utrecht": "위트레흐트",
    "sc cambuur": "SC캄뷔르",
    "feyenoord rotterdam": "페예노르트",
    "excelsior rotterdam": "엑셀시오르 로테르담",
    "fc groningen": "흐로닝언",
    "sc heerenveen": "SC헤이렌베인",
    "sc telstar": "텔스타",
    "pec zwolle": "PEC즈볼러",
    "fc twente enschede": "트벤테",
    "willem ii": "빌럼II",
    "afc ajax": "AFC아약스",
    "ado den haag": "ADO덴하흐",
    "sparta rotterdam": "스파르타 로테르담",
    "az alkmaar": "AZ알크마르",
    "go ahead eagles": "고어헤드 이글스",
    "fortuna sittard": "포르튀나 시타르트",
}
_CACHE = {}
_CACHE_LOCK = Lock()


def _load(code, season, timeout):
    source = f"{ORIGIN}/getmatchdata/{code}/{season}"
    with _CACHE_LOCK:
        stored = _CACHE.get((code, season))
        if stored and monotonic() < stored[0]:
            return stored[1], source

    request = Request(source, headers={"Accept": "application/json", "User-Agent": "MatchIndex/1.0"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read(1_500_001)
    if len(body) > 1_500_000:
        raise ValueError("Unexpected OpenLigaDB response size")
    records = json.loads(body)
    if not isinstance(records, list):
        raise ValueError("Unexpected OpenLigaDB payload")
    if records:
        with _CACHE_LOCK:
            _CACHE[(code, season)] = monotonic() + 1800, records
    return records, source


def _score(record):
    first = record.get("pointsTeam1")
    second = record.get("pointsTeam2")
    return [first, second] if type(first) is int and type(second) is int and min(first, second) >= 0 else None


def _normalize(record, league, source):
    home = record["team1"]
    away = record["team2"]
    started = record["matchDateTimeUTC"]
    home_name = home["teamName"]
    away_name = away["teamName"]
    if not (started and home_name and away_name and home.get("teamId") and away.get("teamId")):
        return None
    complete = record.get("matchIsFinished") is True
    scores = record.get("matchResults") or []
    final = next((_score(score) for score in scores
                  if score.get("resultTypeKind") == "After90Minutes"
                  or score.get("resultTypeID") == 2), None) if complete else None
    half = next((_score(score) for score in scores
                 if score.get("resultTypeKind") == "HalfTime"
                 or score.get("resultTypeID") == 1), None) if complete else None
    location = record.get("location") or {}
    venue = {"name": location.get("locationStadium"), "city": location.get("locationCity")}
    return {
        "league": league,
        "id": f"openliga:{record['matchID']}",
        "start": started,
        "home": TEAM_NAMES.get(home_name.strip().casefold(), home_name),
        "away": TEAM_NAMES.get(away_name.strip().casefold(), away_name),
        "home_id": f"openliga:{home['teamId']}",
        "away_id": f"openliga:{away['teamId']}",
        "complete": complete and final is not None,
        "score": final,
        "half": half,
        "venue": venue if any(venue.values()) else None,
        "source": [SOURCE_NAME, source],
    }


def _season(day):
    return day.year if day.month >= 7 else day.year - 1


def fetch_events(fixtures, timeout=8):
    """Fetch each supported season once, leaving upcoming goals out of completed results."""
    league_days = {}
    for fixture in fixtures:
        league = fixture.get("league")
        if league not in LEAGUE_CODES:
            continue
        try:
            day = date.fromisoformat(fixture["startsAt"][:10])
        except (KeyError, TypeError, ValueError):
            continue
        league_days.setdefault(league, []).append(day)
    if not league_days:
        return {"events": [], "coverage": {}}

    # Retain the prior season at season boundaries so recent form is still available.
    jobs = []
    for league, days in league_days.items():
        earliest = _season(min(days) - timedelta(days=56))
        latest = _season(max(days))
        jobs.extend((league, season) for season in range(earliest, latest + 1))

    def load(job):
        league, season = job
        try:
            records, source = _load(LEAGUE_CODES[league], season, timeout)
        except (HTTPException, OSError, TypeError, ValueError):
            return league, None
        events = []
        for record in records:
            try:
                event = _normalize(record, league, source)
            except (AttributeError, KeyError, TypeError):
                continue
            if event:
                events.append(event)
        return league, events

    events = []
    coverage = {league: "자료원 확인 중" for league in league_days}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for league, result in pool.map(load, jobs):
            if result:
                events.extend(result)
                if any(event["complete"] for event in result):
                    coverage[league] = "OpenLigaDB 경기 기록 연결"
                elif coverage[league] != "OpenLigaDB 경기 기록 연결":
                    coverage[league] = "OpenLigaDB 경기 일정 연결"
            elif result is None and coverage[league] == "자료원 확인 중":
                coverage[league] = "OpenLigaDB 응답 대기"
    return {"events": events, "coverage": coverage}
