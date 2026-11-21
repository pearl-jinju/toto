"""Read NBA game facts from SportsDataverse's published schedule CSV."""

import ast
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from http.client import HTTPException
import io
import re
from threading import Lock
from time import monotonic
from urllib.request import Request, urlopen

from scripts.player_names_ko import player_name_ko


RELEASE = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nba_schedules"
SOURCE_NAME = "SportsDataverse · NBA 일정 및 결과"
LEAGUE = "NBA"
TEAM_NAMES = {
    "ATL": "애틀랜타 호크스",
    "BOS": "보스턴 셀틱스",
    "BKN": "브루클린 네츠",
    "CHA": "샬럿 호네츠",
    "CHI": "시카고 불스",
    "CLE": "클리블랜드 캐벌리어스",
    "DAL": "댈러스 매버릭스",
    "DEN": "덴버 너게츠",
    "DET": "디트로이트 피스톤스",
    "GS": "골든스테이트 워리어스",
    "HOU": "휴스턴 로케츠",
    "IND": "인디애나 페이서스",
    "LAC": "LA 클리퍼스",
    "LAL": "LA 레이커스",
    "MEM": "멤피스 그리즐리스",
    "MIA": "마이애미 히트",
    "MIL": "밀워키 벅스",
    "MIN": "미네소타 팀버울브스",
    "NO": "뉴올리언스 펠리컨스",
    "NY": "뉴욕 닉스",
    "OKC": "오클라호마시티 썬더",
    "ORL": "올랜도 매직",
    "PHI": "필라델피아 76s",
    "PHX": "피닉스 선즈",
    "POR": "포틀랜드 트레일블레이저스",
    "SAC": "새크라멘토 킹스",
    "SA": "샌안토니오 스퍼스",
    "TOR": "토론토 랩터스",
    "UTAH": "유타 재즈",
    "WSH": "워싱턴 위저즈",
}
_REPORT_TEAM_NAMES = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GS", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL",
    "LA Lakers": "LAL", "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NO", "New York Knicks": "NY",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SA", "Toronto Raptors": "TOR", "Utah Jazz": "UTAH", "Washington Wizards": "WSH",
}
_CACHE = {}
_CACHE_LOCK = Lock()
_REPORT_CODES = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}
_STATUS = {"Out": "결장", "Doubtful": "출전 가능성 낮음", "Questionable": "출전 불투명", "Probable": "출전 가능성 높음"}
_EXTRAS = {
    "player": "espn_nba_player_boxscores/player_box_{season}.csv",
    "injury": "nba_stats_injury_report/injury_report_{season}.csv",
}


def _source(season):
    return f"{RELEASE}/nba_schedule_{season}.csv"


def _load(season, timeout):
    with _CACHE_LOCK:
        stored = _CACHE.get(season)
        if stored and monotonic() < stored[0]:
            return stored[1]
    request = Request(_source(season), headers={"Accept": "text/csv", "User-Agent": "MatchIndex/1.0"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read(14_000_001)
    if len(body) > 14_000_000:
        raise ValueError("Unexpected SportsDataverse response size")
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    required = {"id", "date", "home_display_name", "away_display_name", "status_type_completed"}
    if not required.issubset(reader.fieldnames or ()):
        raise ValueError("Unexpected SportsDataverse schedule")
    records = []
    for row in reader:
        event = _event(row, season)
        if event:
            records.append(event)
    if records:
        with _CACHE_LOCK:
            _CACHE[season] = monotonic() + 3600, records
    return records


def _points(value):
    try:
        points = float(value)
    except (TypeError, ValueError):
        return None
    return int(points) if points.is_integer() and 0 <= points <= 300 else None


def _quarters(value):
    if not value or len(value) > 2500:
        return []
    try:
        parsed = ast.literal_eval(re.sub(r"}\s+{", "}, {", value))
        return [_points(period["value"]) for period in parsed]
    except (KeyError, SyntaxError, TypeError, ValueError):
        return []


def _event(row, season):
    if row.get("season_type") not in {"2", "3"}:
        return None
    identifier = row.get("id", "")
    home_id = row.get("home_id", "")
    away_id = row.get("away_id", "")
    if not all(value.isdecimal() for value in (identifier, home_id, away_id)):
        return None
    home = TEAM_NAMES.get(row.get("home_abbreviation"), row.get("home_display_name"))
    away = TEAM_NAMES.get(row.get("away_abbreviation"), row.get("away_display_name"))
    if not home or not away or home == away or row.get("time_valid") != "true":
        return None
    try:
        start = datetime.fromisoformat(row.get("start_date") or row["date"])
    except (KeyError, TypeError, ValueError):
        return None
    if start.tzinfo is None:
        return None
    hpoints, apoints = _points(row.get("home_score")), _points(row.get("away_score"))
    complete = row.get("status_type_completed") == "true" and hpoints and apoints and hpoints != apoints
    half = None
    if complete:
        quarters = [_quarters(row.get(key)) for key in ("home_linescores", "away_linescores")]
        if all(len(periods) >= 4 and None not in periods[:2] for periods in quarters):
            half = [sum(periods[:2]) for periods in quarters]
    venue = {
        "name": row.get("venue_full_name"),
        "city": row.get("venue_address_city"),
        "region": row.get("venue_address_state"),
        "country": "US",
        "indoor": True if row.get("venue_indoor") == "true" else None,
    }
    return {
        "league": LEAGUE,
        "id": f"sportsdataverse:nba:{identifier}",
        "start": start.isoformat(),
        "home": home,
        "away": away,
        "home_id": f"sportsdataverse:nba:{home_id}",
        "away_id": f"sportsdataverse:nba:{away_id}",
        "complete": bool(complete),
        "score": [hpoints, apoints] if complete else None,
        "half": half,
        "venue": venue if venue["name"] else None,
        "source": [SOURCE_NAME, _source(season)],
        "_codes": [row.get("home_abbreviation"), row.get("away_abbreviation")],
        "_local_start": row.get("game_date_time"),
        "_season": season,
    }


def _extra_source(kind, season):
    tag_file = _EXTRAS[kind].format(season=season)
    return f"{RELEASE.rsplit('/', 1)[0]}/{tag_file}"


def _extra_csv(kind, season, timeout):
    key = (kind, season)
    with _CACHE_LOCK:
        stored = _CACHE.get(key)
        if stored and monotonic() < stored[0]:
            return csv.DictReader(io.StringIO(stored[1]))

    request = Request(_extra_source(kind, season), headers={"Accept": "text/csv", "User-Agent": "MatchIndex/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read(25_000_001)
        if len(content) > 25_000_000:
            return ()
        body = content.decode("utf-8-sig")
    except (HTTPException, OSError, UnicodeError, ValueError):
        return ()

    with _CACHE_LOCK:
        _CACHE[key] = monotonic() + 3600, body
    return csv.DictReader(io.StringIO(body))


def _box_index(season, timeout):
    index = {}
    for row in _extra_csv("player", season, timeout):
        if row.get("did_not_play") == "true" or row.get("season_type") not in {"2", "3"}:
            continue
        player = row.get("athlete_display_name")
        points, assists = _points(row.get("points")), _points(row.get("assists"))
        if not player or points is None or assists is None:
            continue
        index.setdefault((row["game_id"], row["team_id"]), []).append((player, points, assists))
    return index


def _report_index(season, timeout):
    index = {}
    for row in _extra_csv("injury", season, timeout):
        if not all(row.get(key) for key in ("home_team_abbr", "away_team_abbr", "report_datetime", "game_date", "team")):
            continue
        key = (row["game_date"], row["home_team_abbr"], row["away_team_abbr"])
        try:
            timestamp = datetime.fromisoformat(row["report_datetime"])
        except ValueError:
            continue
        if timestamp.tzinfo is not None:
            continue
        player = row.get("report_player_name", "")
        if "," in player:
            surname, given = player.split(",", 1)
            player = given.strip() + " " + surname.strip()
        by_team = index.setdefault(key, {}).setdefault(row["team"], {})
        by_team.setdefault(timestamp, []).append((player, row.get("current_status"), row.get("reason")))
    return index


def _injury_factors(event, reports, now):
    try:
        local = datetime.fromisoformat(event["_local_start"])
    except (TypeError, ValueError):
        return []
    if local.tzinfo is None:
        return []
    home, away = (_REPORT_CODES.get(code, code) for code in event["_codes"])
    key = (local.date().isoformat(), home, away)
    factors = []
    for team, releases in reports.get(key, {}).items():
        eligible = [
            ts for ts in releases
            if ts < local.replace(tzinfo=None) and ts.replace(tzinfo=local.tzinfo) <= now
        ]
        if not eligible:
            continue
        timestamp = max(eligible)
        latest = sorted(
            {(player, status) for player, status, _ in releases[timestamp] if player and status in _STATUS},
            key=lambda item: (list(_STATUS).index(item[1]), item[0]),
        )
        if not latest:
            continue
        shown = [(player, player_name_ko(player), status) for player, status in latest[:3]]
        value = " · ".join(f"{display} {_STATUS[status]}" for _, display, status in shown)
        original_names = [player for player, display, _ in shown if player != display]
        if len(latest) > 3:
            value += f" 외 {len(latest)-3}명"
        factors.append({
            "category": "players",
            "title": f"{TEAM_NAMES.get(_REPORT_TEAM_NAMES.get(team), team)} 출전 보고",
            **({"originalNames": original_names} if original_names else {}),
            "value": value,
            "text": "경기 전에 제출된 NBA 출전 상태입니다. 보고 시각 이후 선발은 바뀔 수 있습니다.",
            "date": timestamp.replace(tzinfo=local.tzinfo).isoformat(),
            "source": [
                "SportsDataverse · NBA 부상 보고 기록",
                _extra_source("injury", event["_season"]),
            ],
        })
    return factors


def _leader_factor(event, team, team_id, previous, boxes):
    recent = sorted(
        (
            row for row in previous if row["start"] < event["start"] and row["complete"]
            and team_id in (row["home_id"], row["away_id"])
        ),
        key=lambda row: row["start"],
        reverse=True,
    )[:5]
    stats = {}
    for row in recent:
        for player, points, assists in boxes.get((row["id"].rsplit(":", 1)[1], team_id.rsplit(":", 1)[1]), []):
            count, previous_points, previous_assists = stats.get(player, (0, 0, 0))
            stats[player] = count+1, previous_points+points, previous_assists+assists
    candidates = [(name, count, pts/count, ast/count) for name, (count, pts, ast) in stats.items() if count >= 3]
    if not candidates:
        return None
    name, count, points, assists = max(candidates, key=lambda candidate: (candidate[2], candidate[1], candidate[3]))
    display_name = player_name_ko(name)
    return {
        "category": "players",
        "title": f"{team} · {display_name}",
        **({"originalName": name} if name != display_name else {}),
        "value": f"평균 {points:.1f}득점 · {assists:.1f}도움",
        "text": f"이 경기 전 팀의 최근 {len(recent)}경기 중 실제 출전한 {count}경기 기준입니다.",
        "date": recent[0]["start"],
        "source": ["SportsDataverse · NBA 선수 경기 기록", _extra_source("player", event["_season"])],
    }


def _with_factors(events, fixtures, timeout):
    """Join dated injury snapshots and prior box scores to exact target fixtures."""
    keys = {
        (fixture["home"], fixture["away"], datetime.fromisoformat(fixture["startsAt"]))
        for fixture in fixtures if fixture.get("league") == LEAGUE and fixture.get("startsAt")
    }
    targets = [event for event in events if (
        event["home"], event["away"], datetime.fromisoformat(event["start"])
    ) in keys]
    seasons = {event["_season"] for event in targets}
    if not seasons:
        return events

    now = datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=4) as pool:
        reports = {season: pool.submit(_report_index, season, timeout) for season in seasons}
        boxes = {season: pool.submit(_box_index, season, timeout) for season in seasons}
        for event in targets:
            season = event["_season"]
            factors = _injury_factors(event, reports[season].result(), now)
            for side in ("home", "away"):
                factor = _leader_factor(event, event[side], event[f"{side}_id"], events, boxes[season].result())
                if factor:
                    factors.append(factor)
            if factors:
                event["factors"] = factors
    return events


def _season(day):
    return day.year + (day.month >= 9)


def fetch_events(fixtures, timeout=12):
    """Return regular-season and playoff games near the current official round."""
    dates = []
    for fixture in fixtures:
        if fixture.get("league") == LEAGUE:
            try:
                dates.append(date.fromisoformat(fixture["startsAt"][:10]))
            except (KeyError, TypeError, ValueError):
                continue
    if not dates:
        return {"events": [], "coverage": {}}

    first = min(dates) - timedelta(days=56)
    last = max(dates) + timedelta(days=2)
    events = []
    for season in range(_season(first), _season(last) + 1):
        try:
            available = _load(season, timeout)
        except (HTTPException, OSError, TypeError, ValueError):
            continue
        events.extend(event for event in available
                      if first <= date.fromisoformat(event["start"][:10]) <= last)
    # Copy cached rows before attaching fixture-specific context such as pregame reports.
    events = _with_factors([event.copy() for event in events], fixtures, timeout)
    for event in events:
        for key in ("_codes", "_local_start", "_season"):
            event.pop(key, None)
    status = "SportsDataverse 경기 기록 연결" if events else "SportsDataverse 응답 대기"
    return {"events": events, "coverage": {LEAGUE: status}}
