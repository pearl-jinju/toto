"""Verified match-day records kept separate from pre-match historical analysis."""

from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta, timezone
from html import unescape
from http.client import HTTPException
import io
import math
import re
from threading import Lock
from time import monotonic
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from scripts.provider_wkbl import TEAMS as WKBL_TEAMS


NBA_TEAM_BOX = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
    "espn_nba_team_boxscores/team_box_{season}.csv"
)
NBA_FIELDS = [
    ("field_goal_pct", "야투 성공률", "%"),
    ("three_point_field_goal_pct", "3점슛 성공률", "%"),
    ("free_throw_pct", "자유투 성공률", "%"),
    ("total_rebounds", "리바운드", None),
    ("offensive_rebounds", "공격 리바운드", None),
    ("assists", "어시스트", None),
    ("steals", "스틸", None),
    ("blocks", "블록", None),
    ("total_turnovers", "턴오버", None),
    ("points_in_paint", "페인트존 득점", "점"),
    ("fast_break_points", "속공 득점", "점"),
    ("largest_lead", "최대 리드", "점"),
]
_CACHED_BOX = {}
_CACHED_RECORDS = {}
_KST = timezone(timedelta(hours=9))
_J_METRICS = {"SH": "슈팅", "CK": "코너킥", "FK": "프리킥"}
_WKBL_METRICS = ["리바운드", "어시스트", "스틸", "블록", "턴오버", "파울"]
_CACHE_LOCK = Lock()
_UPSTREAM_ERRORS = (OSError, HTTPException, UnicodeError, ValueError, TypeError, KeyError)


def _date(value):
    return datetime.fromisoformat(value)


def _score(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,3}:\d{1,3}", value):
        return None
    return [int(part) for part in value.split(":")]


def _fetch(url, max_bytes, accept):
    req = Request(url, headers={"Accept": accept, "User-Agent": "MatchIndex/1.0"})
    with urlopen(req, timeout=8) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("Unexpected match record response size")
    return raw.decode("utf-8-sig")


def _metric(value, unit):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0 or (unit == "%" and number > 100):
        return None
    if unit != "%" and not number.is_integer():
        return None
    return int(number) if number.is_integer() else number


def _nba_box(season):
    with _CACHE_LOCK:
        found = _CACHED_BOX.get(season)
        if found and found[0] > monotonic():
            return found[1]

    source = NBA_TEAM_BOX.format(season=season)
    data = csv.DictReader(io.StringIO(_fetch(source, 3_000_000, "text/csv")))
    if not {"game_id", "team_home_away", "team_id", "team_score", "game_date_time"}.issubset(data.fieldnames or ()):
        raise ValueError("Unexpected NBA data fields")
    games = {}
    for row in data:
        identifier, side = row["game_id"], row["team_home_away"]
        if not identifier.isdecimal() or side not in {"home", "away"}:
            continue
        games.setdefault(identifier, {}).setdefault(side, []).append(row)
    if games:
        with _CACHE_LOCK:
            _CACHED_BOX[season] = monotonic() + 1800, games
            while len(_CACHED_BOX) > 3:
                _CACHED_BOX.pop(next(iter(_CACHED_BOX)))
    return games


def _nba_stats(fixture, event, games, season):
    identifier = str(event.get("id", "")).removeprefix("sportsdataverse:nba:")
    sides = games.get(identifier, {})
    if any(len(sides.get(side, ())) != 1 for side in ("home", "away")):
        return None
    rows = [sides[side][0] for side in ("home", "away")]
    official = _score(fixture.get("result"))
    if not official or event.get("score") != official:
        return None
    for index, (side, row) in enumerate(zip(("home", "away"), rows)):
        expected_team = str(event.get(f"{side}_id", "")).removeprefix("sportsdataverse:nba:")
        opponent = rows[1-index]["team_id"]
        if (row["team_id"] != expected_team or row.get("opponent_team_id") != opponent
                or _metric(row["team_score"], None) != official[index]
                or _metric(row.get("opponent_team_score"), None) != official[1-index]):
            return None
        if abs((_date(row["game_date_time"]) - _date(fixture["startsAt"])).total_seconds()) > 1800:
            return None

    metrics = []
    for field, label, unit in NBA_FIELDS:
        home, away = [_metric(row.get(field), unit) for row in rows]
        if None not in (home, away):
            metrics.append({"label": label, "home": home, "away": away, **({"unit": unit} if unit else {})})
    if not metrics:
        return None
    return {
        "state": "finished",
        "source": ["SportsDataverse · NBA 팀 기록", NBA_TEAM_BOX.format(season=season)],
        "reference": ["ESPN · 해당 경기 박스스코어", f"https://www.espn.com/nba/boxscore/_/gameId/{identifier}"],
        "metrics": metrics,
    }


def _text(value):
    return " ".join(unescape(re.sub(r"<[^>]+>", "", value)).split())


def _section(html, area):
    item = re.search(rf"<!--\s+{area}\s+[^>]+Start\s*-->(.*?)<!--\s+{area}\s+[^>]+End\s*-->", html, re.S)
    return item[1] if item else ""


def _cells(html, tag="td"):
    return [_text(cell) for cell in re.findall(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, re.S)]


def _jleague_record(html, event, official):
    main = _section(html, "A1")
    teams = re.findall(r'id="team-name-[lr]"[^>]*>\s*<a[^>]+/club/([^/]+)/', main)
    scores = re.findall(r'<td\s+class="score"[^>]*>\s*(\d+)\s*</td>', main)
    if teams != [event.get("home_id"), event.get("away_id")] or list(map(int, scores)) != official:
        return {}
    periods = []
    for home, label, away in re.findall(
        r'<dd class="left-area">\s*(\d+)\s*</dd>\s*<dt[^>]*>(前半|後半)</dt>\s*'
        r'<dd class="right-area">\s*(\d+)\s*</dd>', main,
    ):
        periods.append({"label": {"前半": "전반", "後半": "후반"}[label], "home": int(home), "away": int(away)})
    if len(periods) != 2 or [sum(p[s] for p in periods) for s in ("home", "away")] != official:
        periods = []
    metrics = []
    for segment in re.findall(r'<dl class="score-board-base">(.*?)</dl>', _section(html, "A4"), re.S):
        numbers = re.findall(r'<div class="(?:left|right)-score">\s*(\d+)\s*</div>', segment)
        labels = _cells(segment, "dt")
        if len(numbers) == 2 and len(labels) == 1 and labels[0] in _J_METRICS:
            metrics.append({"label": _J_METRICS[labels[0]], "home": int(numbers[0]), "away": int(numbers[1])})

    events = []
    goal_area = _section(html, "A2")
    for idx, (area, side) in enumerate((("left", "home"), ("right", "away"))):
        selected = re.search(rf'<td class="{area}-area">\s*<table[^>]*>(.*?)</table>', goal_area, re.S)
        if not selected:
            if official[idx]:
                events = []
                break
            continue
        rows = [_cells(row) for row in re.findall(r"<tr[^>]*>(.*?)</tr>", selected[1], re.S)]
        valid = [
            (cells[0], cells[1].removesuffix("'")) for cells in rows
            if len(cells) == 2 and cells[0] and re.fullmatch(r"\d{1,3}(?:\+\d{1,2})?'", cells[1])
        ]
        if len(valid) != official[idx]:
            events = []
            break
        events.extend({"minute": clock, "label": f"{name} 득점", "side": side} for name, clock in valid)
    events.sort(key=lambda event: tuple(map(int, event["minute"].split("+"))))
    return {key: value for key, value in (("periods", periods), ("metrics", metrics), ("events", events)) if value}


def _wkbl_record(html, fixture, official):
    parts = html.split('<div class="game_body">', 1)
    if len(parts) != 2:
        return {}
    header, body = parts
    stamp = re.search(r'<strong class="txt_time">(.+?)</strong>', header, re.S)
    start = _date(fixture["startsAt"]).astimezone(_KST)
    if not stamp or any(start.strftime(part) not in _text(stamp[1]) for part in ("%Y.%m.%d", "%H:%M")):
        return {}
    rows = re.findall(r'<div class="info_team (home|away)">.*?alt="([^"]+)".*?<em>(\d+)</em>', header, re.S)
    if len(rows) != 2 or [item[0] for item in rows] != ["home", "away"]:
        return {}
    if [WKBL_TEAMS.get(name.strip(), name.strip()) for _, name, _ in rows] != [fixture["home"], fixture["away"]]:
        return {}
    if [int(points) for _, _, points in rows] != official:
        return {}
    table = re.search(r"<caption>점수 상세 정보</caption>(.*?)</table>", body, re.S)
    if not table:
        return {}
    periods = []
    for home, label, away in re.findall(r"<td>\s*(\d+)\s*</td>\s*<th>([1-4]Q|EQ)</th>\s*<td>\s*(\d+)\s*</td>", table[1]):
        home, away = int(home), int(away)
        if label != "EQ" or home or away:
            periods.append({"label": "연장" if label == "EQ" else f"{label[0]}쿼터", "home": home, "away": away})
    if len(periods) < 4 or [sum(p[s] for p in periods) for s in ("home", "away")] != official:
        periods = []

    totals = {}
    for foot in re.findall(r"<tfoot>(.*?)</tfoot>", body, re.S):
        cells = _cells(foot)
        if len(cells) != 8 or not re.fullmatch(r"\d{2,3}:\d{2}", cells[0]):
            continue
        numbers = [_metric(cell, None) for cell in cells[1:]]
        if None not in numbers:
            totals[numbers[0]] = numbers[1:]
    a, b = (totals.get(points) for points in official)
    metrics = [{"label": label, "home": home, "away": away}
               for label, home, away in zip(_WKBL_METRICS, a or (), b or ())]
    return {key: value for key, value in (("periods", periods), ("metrics", metrics)) if value}


def _official_record(fixture, event):
    official = _score(fixture.get("result"))
    if not official or event.get("score") != official:
        return None
    label, url = event.get("source", ("", ""))
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        return None
    params = parse_qs(parsed.query)
    target = str(event.get("id", ""))
    league = fixture["league"]
    jleague = (league in {"일본 J1리그", "일본 J2리그"}
               and parsed.netloc == "data.j-league.or.jp" and parsed.path == "/SFMS02/"
               and params.get("match_card_id") == [target.removeprefix("jleague-")])
    wkbl = (league == "WKBL" and parsed.netloc == "www.wkbl.or.kr" and parsed.path == "/m/game/result.asp"
            and params.get("game_type") == ["01"]
            and target == f"wkbl-{params.get('season_gu', [''])[0]}-{params.get('game_no', [''])[0]}")

    if not jleague and not wkbl:
        return None

    with _CACHE_LOCK:
        stored = _CACHED_RECORDS.get(url)
        if stored and stored[0] > monotonic():
            html = stored[1]
        else:
            html = None
    if html is None:
        html = _fetch(url, 500_000, "text/html")
        with _CACHE_LOCK:
            _CACHED_RECORDS[url] = monotonic() + 86400, html
            while len(_CACHED_RECORDS) > 100:
                _CACHED_RECORDS.pop(next(iter(_CACHED_RECORDS)))
    stats = _jleague_record(html, event, official) if jleague else _wkbl_record(html, fixture, official)
    return {"state": "finished", "source": [label, url], **stats} if stats else None


def get_match_stats(fixtures, matched):
    """Return only source-verified records for fixtures already linked to that provider."""
    nba = {}
    official_records = []
    for fixture in fixtures:
        event = matched.get(fixture["number"])
        if not event or fixture.get("status") != "finished" or not event.get("complete"):
            continue
        if fixture["league"] == "NBA" and str(event.get("id", "")).startswith("sportsdataverse:nba:"):
            tip = _date(fixture["startsAt"])
            season = tip.year + (tip.month >= 9)
            nba.setdefault(season, []).append((fixture, event))
        elif fixture["league"] in {"일본 J1리그", "일본 J2리그", "WKBL"}:
            official_records.append((fixture, event))

    def league_box(season, entries):
        try:
            games = _nba_box(season)
        except _UPSTREAM_ERRORS:
            return {}
        output = {}
        for fixture, event in entries:
            try:
                stats = _nba_stats(fixture, event, games, season)
            except _UPSTREAM_ERRORS:
                continue
            if stats:
                output[fixture["number"]] = stats
        return output

    def official_box(fixture, event):
        try:
            record = _official_record(fixture, event)
        except _UPSTREAM_ERRORS:
            return {}
        return {fixture["number"]: record} if record else {}

    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(league_box, season, entries) for season, entries in nba.items()]
        jobs.extend(pool.submit(official_box, fixture, event) for fixture, event in official_records)
        return {number: stats for job in jobs for number, stats in job.result().items()}
