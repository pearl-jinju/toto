"""Official WKBL monthly list adapter (regular-season matches)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from html import unescape
import re
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, urlopen


KST = timezone(timedelta(hours=9))
SCHEDULE = "https://www.wkbl.or.kr/m/game/schedule.asp"
TEAMS = {
    "KB스타즈": "KB 스타즈", "BNK 썸": "BNK 썸", "하나은행": "하나은행",
    "삼성생명": "삼성생명 블루밍스", "신한은행": "신한은행 에스버드", "우리은행": "우리은행 우리WON",
}
MONTH = re.compile(r'<strong class="date">(\d{4})\.(\d{2})</strong>')
RESULT = re.compile(r'<a href="(/m/game/result\.asp\?[^"]+)" class="link_detail">(.*?)</a>', re.S)
DAY = re.compile(r'<span class="date">(\d{1,2})\.(\d{1,2})</span>')
TEAM = re.compile(r'<strong class="team_name">\s*([^<]+?)\s*</strong>\s*<em>\s*(\d+)\s*</em>')


def parse_wkbl_month(html, year, month, current):
    match = MONTH.search(html)
    if not match or tuple(map(int, match.groups())) != (year, month):
        return []
    events = []
    for item in RESULT.finditer(html):
        params = parse_qs(urlsplit(unescape(item[1])).query)
        if params.get("game_type") != ["01"] or not params.get("season_gu") or not params.get("game_no"):
            continue
        found = DAY.search(item[2])
        teams = TEAM.findall(item[2])
        if found is None or len(teams) != 2 or int(found[1]) != month:
            continue
        day = date(year, month, int(found[2]))
        home, away = [TEAMS.get(team.strip()) for team, _ in teams]
        points = [int(score) for _, score in teams]
        if home is None or away is None or points[0] == points[1]:
            continue
        official_kickoff = current.get((day.isoformat(), home, away))
        events.append({
            "league": "WKBL", "id": "wkbl-" + params["season_gu"][0] + "-" + params["game_no"][0],
            "start": official_kickoff or datetime(year, month, day.day, tzinfo=KST).isoformat(),
            "dateOnly": official_kickoff is None,
            "home": home, "away": away, "complete": True, "score": points,
            "source": ["WKBL 공식 경기 기록", urljoin(SCHEDULE, unescape(item[1]))],
        })
    return events


def wkbl_for_month(year, month, current):
    url = f"{SCHEDULE}?sch_ym={year}{month:02d}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    with urlopen(request, timeout=12) as response:
        return parse_wkbl_month(response.read(1_000_000).decode("utf-8"), year, month, current)


def fetch_events(fixtures):
    current = {}
    months = set()
    for fixture in fixtures:
        if fixture.get("league") != "WKBL":
            continue
        kickoff = datetime.fromisoformat(fixture["startsAt"]).astimezone(KST)
        current[(kickoff.date().isoformat(), fixture["home"], fixture["away"])] = fixture["startsAt"]
        month = kickoff.date().replace(day=1)
        for _ in range(3):
            months.add((month.year, month.month))
            month = (month - timedelta(days=1)).replace(day=1)

    rows = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(wkbl_for_month, y, m, current) for y, m in months]
        for future in futures:
            try:
                for row in future.result():
                    rows[row["id"]] = row
            except (OSError, ValueError):
                continue
    return list(rows.values())
