"""Public league standings normalized for MatchIndex's fixture comparison.

Uses the table's published order, not inferred ranks from the betting schedule.
No credentials or third-party dependencies are required. Full-table checks protect
against empty seasons and upstream layout changes.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.fixture_matching import DISPLAY_NAMES, team_key
from scripts.provider_domestic import J_CLUBS
from scripts.provider_openliga import TEAM_NAMES as OPENLIGA_TEAMS


JST = timezone(timedelta(hours=9))
OPENLIGA = {
    "잉글랜드 프리미어리그": ("pl", 20),
    "독일 분데스리가": ("bl1", 18),
    "독일 분데스리가2": ("bl2", 18),
}
J_LEAGUE = {"일본 J1리그": "j1", "일본 J2리그": "j2"}
OPENLIGA_REFERENCE = {
    "잉글랜드 프리미어리그": ["프리미어리그 공식 순위표", "https://www.premierleague.com/en/tables/premier-league"],
    "독일 분데스리가": ["분데스리가 공식 순위표", "https://www.bundesliga.com/en/bundesliga/table"],
    "독일 분데스리가2": ["분데스리가2 공식 순위표", "https://www.bundesliga.com/en/2bundesliga/table"],
}
LALIGA = "스페인 라리가"
EREDIVISIE = "네덜란드 에레디비시"
WKBL = "WKBL"
WKBL_HOME = "https://www.wkbl.or.kr/game/team_rank.asp?gun=1"
WKBL_DATA = "https://www.wkbl.or.kr/game/ajax/ajax_team_rank.asp"


def get_text(url, params=None):
    data = urlencode(params).encode("utf-8") if params is not None else None
    request = Request(url, data=data, headers={"User-Agent": "Mozilla/5.0 (compatible; MatchIndex/1.0)", "Accept": "*/*"})
    with urlopen(request, timeout=10) as response:
        body = response.read(3_000_001)
    if len(body) > 3_000_000:
        raise ValueError("Unexpected table size")
    return body.decode("utf-8-sig")


def korean_name(name, fixture_names):
    key = team_key(name)
    return fixture_names.get(key) or DISPLAY_NAMES.get(key) or name


def checks_complete(rows, size, ties=False):
    if len(rows) != size or len({team_key(r["team"]) for r in rows}) != size:
        return False
    ranks = [r["rank"] for r in rows]
    if ranks[0] != 1 or ranks != sorted(ranks) or ranks[-1] > size:
        return False
    if not ties and ranks != list(range(1, size + 1)):
        return False
    return any(r["played"] for r in rows) and all(
        r["played"] == r["wins"] + r["draws"] + r["losses"] for r in rows
    )


def result(league, season, rows, label, url, checked_at):
    return {
        "league": league, "season": season,
        "source": [label, url], "updatedAt": checked_at,
        "groups": [{"name": "정규리그", "rows": rows}],
    }


def team_row(rank, team, played, wins, draws, losses, points, scored, conceded):
    return {
        "rank": rank, "team": team, "played": played, "wins": wins, "draws": draws,
        "losses": losses, "points": points, "for": scored, "against": conceded,
        "winPct": round(wins / played, 4) if played else None,
    }


def openliga_table(league, season, names, checked_at):
    code, size = OPENLIGA[league]
    link = f"https://api.openligadb.de/getbltable/{code}/{season[:4]}"
    raw = json.loads(get_text(link))
    if not isinstance(raw, list):
        return None
    rows = []
    for rank, entry in enumerate(raw, 1):
        name = entry["teamName"]
        if not isinstance(name, str) or not name.strip():
            return None
        name = OPENLIGA_TEAMS.get(name.strip().casefold(), name.strip())
        values = [entry[key] for key in ("matches", "won", "draw", "lost", "points", "goals", "opponentGoals")]
        if not all(type(n) is int and n >= 0 for n in values):
            return None
        rows.append(team_row(rank, korean_name(name, names), *values))
    if checks_complete(rows, size):
        table = result(league, season, rows, "OpenLigaDB · 리그 순위표 (ODbL 1.0)", link, checked_at)
        table["reference"] = OPENLIGA_REFERENCE[league]
        return table
    return None


class TableReader(HTMLParser):
    """Collect rows and team anchors from a selected table identified by its attributes."""

    def __init__(self, select_table):
        super().__init__()
        self.select_table = select_table
        self.active = False
        self.row = self.cell = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "table" and not self.active:
            self.active = self.select_table(props)
        elif self.active and tag == "tr":
            self.row = []
        elif self.row is not None and tag in ("td", "th"):
            self.cell = {"parts": [], "href": "", "alt": ""}
        elif self.cell is not None and tag == "a" and not self.cell["href"]:
            self.cell["href"] = props.get("href", "")
        elif self.cell is not None and tag == "img" and not self.cell["alt"]:
            self.cell["alt"] = props.get("alt", "")

    def handle_data(self, text):
        if self.cell is not None:
            self.cell["parts"].append(text)

    def handle_endtag(self, tag):
        if self.cell is not None and tag in ("td", "th"):
            parts = [part.strip() for part in self.cell.pop("parts") if part.strip()]
            self.cell["text"] = " ".join(parts)
            self.cell["primary"] = parts[0] if parts else ""
            self.row.append(self.cell)
            self.cell = None
        elif self.active and tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.active = False


def jleague_table(league, season, names, checked_at):
    code = J_LEAGUE[league]
    link = f"https://www.jleague.jp/{code}/standings/{season}/"
    page = get_text(link)
    table = TableReader(lambda props: "rt-TableRootTable" in props.get("class", "").split())
    table.feed(page)
    page_text = re.sub(r"<[^>]+>", "", page)
    updated = re.search(r"更新日\s*:\s*(\d{4}/\d\d/\d\d \d\d:\d\d)", page_text)
    if updated:
        checked_at = datetime.strptime(updated[1], "%Y/%m/%d %H:%M").replace(tzinfo=JST).isoformat(timespec="seconds")
    rows = []
    for cells in table.rows:
        if len(cells) < 10 or not cells[0]["text"].isdecimal():
            continue
        rank = int(cells[0]["text"])
        club = re.search(r"/club/([a-z0-9]+)(?:/|$)", cells[1]["href"])
        if club is None:
            return None
        name = J_CLUBS.get(club[1], cells[1]["primary"])
        points, played, wins, draws, losses, scored, conceded = [int(cell["text"]) for cell in cells[2:9]]
        rows.append(team_row(rank, korean_name(name, names), played, wins, draws, losses, points, scored, conceded))
    if checks_complete(rows, 20):
        return result(league, season, rows, "J리그 · 공식 순위표", link, checked_at)
    return None


def laliga_table(league, season, names, checked_at):
    link = "https://www.laliga.com/en-GB/laliga-easports/standing"
    page = get_text(link)
    hydrated = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', page, re.S)
    if not hydrated:
        return None
    props = json.loads(hydrated[1])["props"]["pageProps"]
    first_day = props["gameweekList"][0]["date"]
    if not first_day.startswith(season[:4] + "-"):
        return None
    rows = []
    for entry in props["standings"]:
        team = entry["team"]
        name = korean_name(team["nickname"], names)
        rank, played, wins, draws, losses, points, scored, conceded = [
            entry[key] for key in ("position", "played", "won", "drawn", "lost", "points", "goals_for", "goals_against")
        ]
        if not all(type(n) is int and n >= 0 for n in (rank, played, wins, draws, losses, points, scored, conceded)):
            return None
        rows.append(team_row(rank, name, played, wins, draws, losses, points, scored, conceded))
    if checks_complete(rows, 20):
        return result(league, season, rows, "라리가 · 공식 순위표", link, checked_at)
    return None


def wkbl_table(league, season, names, checked_at):
    page = get_text(WKBL_HOME)
    next_year = str(int(season[:4]) + 1)
    season_id = re.search(r'data-season="(\d+)"\s+data-season_name="' + re.escape(season[:4] + "-" + next_year) + '"', page)
    if not season_id:
        return None
    payload = get_text(WKBL_DATA, {"season_gu": season_id[1], "gun": "1"})
    table = TableReader(lambda _: True)
    table.feed("<table>" + payload + "</table>")
    rows = []
    for cells in table.rows:
        if len(cells) < 5 or not cells[0]["text"].isdecimal():
            continue
        rank = int(cells[0]["text"])
        name = korean_name(cells[1]["text"], names)
        played = int(cells[2]["text"])
        record = re.fullmatch(r"(\d+)\s*승\s*(\d+)\s*패", cells[3]["text"])
        if not record:
            return None
        wins, losses = map(int, record.groups())
        rows.append(team_row(rank, name, played, wins, 0, losses, None, None, None))
    if checks_complete(rows, 6, ties=True):
        return result(league, season, rows, "WKBL · 공식 정규리그 순위", WKBL_HOME, checked_at)
    return None


def eredivisie_table(league, season, names, checked_at):
    link = "https://eredivisie.com/competition/table/"
    table = TableReader(lambda props: "table" in props.get("class", "").split())
    table.feed(get_text(link))
    rows = []
    for cells in table.rows:
        if len(cells) != 7 or not cells[0]["text"].isdecimal():
            continue
        rank = int(cells[0]["text"])
        name = korean_name(cells[1]["text"], names)
        played = int(cells[2]["text"])
        wins, draws, losses = map(int, cells[3]["text"].split("|"))
        scored, conceded = map(int, cells[4]["text"].split("-"))
        points = int(cells[6]["text"])
        rows.append(team_row(rank, name, played, wins, draws, losses, points, scored, conceded))
    if checks_complete(rows, 18) and names.keys() <= {team_key(row["team"]) for row in rows}:
        return result(league, season, rows, "에레디비시 · 공식 순위표", link, checked_at)
    return None


def season_for(fixture):
    kickoff = datetime.fromisoformat(fixture["startsAt"])
    first = kickoff.year - int(kickoff.month < 7)
    return f"{first}-{(first + 1) % 100:02d}"


def get_standings(fixtures):
    """Return current-season standings by exact Betman league names."""
    jobs = {}
    for fixture in fixtures:
        league = fixture["league"]
        provider = PROVIDERS.get(league)
        if provider is None:
            continue
        season = season_for(fixture)
        _, names = jobs.setdefault((league, season), (provider, {}))
        for side in ("home", "away"):
            names[team_key(fixture[side])] = fixture[side]
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    output = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        requests = {
            (league, season): executor.submit(provider, league, season, names, checked_at)
            for (league, season), (provider, names) in jobs.items()
        }
        for (league, season), request in sorted(requests.items()):
            try:
                value = request.result()
                if value:
                    output[league] = value
            except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError):
                continue
    return output


PROVIDERS = {**dict.fromkeys(OPENLIGA, openliga_table), **dict.fromkeys(J_LEAGUE, jleague_table), LALIGA: laliga_table, WKBL: wkbl_table, EREDIVISIE: eredivisie_table}
