"""Official J.League and K League calendars as normalized historical fixtures."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


LOCAL_TIME = timezone(timedelta(hours=9))
J_DATA = "https://data.j-league.or.jp"
K_CALENDAR = "https://portal.kleague.com/view/schedule/list.do"
J_LEAGUES = {"일본 J1리그": "J1", "일본 J2리그": "J2"}
K_LEAGUES = {"하나은행 K리그1": "K리그1", "하나은행 K리그2": "K리그2"}
J_CLUBS = {
    "yokohamafm": "Yokohama F. Marinos", "kashima": "Kashima Antlers",
    "gosaka": "Gamba Osaka", "urawa": "Urawa Red Diamonds",
    "cosaka": "Cerezo Osaka", "okayama": "Fagiano Okayama", "nagoya": "Nagoya Grampus",
    "shimizu": "Shimizu S-Pulse", "fukuoka": "Avispa Fukuoka", "kobe": "Vissel Kobe",
    "kashiwa": "Kashiwa Reysol", "mito": "Mito HollyHock", "ftokyo": "FC Tokyo",
    "machida": "Machida Zelvia", "hiroshima": "Sanfrecce Hiroshima",
    "chiba": "JEF United Chiba", "tokyov": "Tokyo Verdy", "kawasakif": "Kawasaki Frontale",
    "nagasaki": "V-Varen Nagasaki", "kyoto": "Kyoto Sanga",
    "akita": "Blaublitz Akita", "yamagata": "Montedio Yamagata", "tochigic": "Tochigi City", "tochigicity": "Tochigi City",
    "niigata": "Albirex Niigata", "yokohamafc": "Yokohama FC",
    "sapporo": "Hokkaido Consadole Sapporo", "kofu": "Ventforet Kofu",
    "hachinohe": "Vanraure Hachinohe", "toyama": "Kataller Toyama", "oita": "Oita Trinita",
    "iwata": "Jubilo Iwata", "omiya": "RB Omiya Ardija", "fujieda": "Fujieda MYFC",
    "imabari": "FC Imabari", "tosu": "Sagan Tosu", "sendai": "Vegalta Sendai",
    "miyazaki": "Tegevajaro Miyazaki", "iwaki": "Iwaki FC", "tokushima": "Tokushima Vortis",
    "shonan": "Shonan Bellmare",
}
K_CLUBS = {
    "서울": "FC서울", "안양": "FC안양", "강원": "강원FC", "광주": "광주FC",
    "김천": "김천상무 프로축구단", "대전": "대전 하나시티즌", "부천": "부천FC 1995",
    "울산": "울산 HDFC", "인천": "인천 유나이티드", "전북": "전북 현대모터스",
    "제주": "제주 SKFC", "포항": "포항 스틸러스", "경남": "경남FC", "김포": "김포FC",
    "김해": "김해FC 2008", "대구": "대구FC", "부산": "부산 아이파크",
    "서울E": "서울 이랜드", "성남": "성남FC", "수원": "수원 삼성블루윙즈",
    "수원FC": "수원FC", "안산": "안산 그리너스", "용인": "용인FC", "전남": "전남 드래곤즈",
    "천안": "천안 시티FC", "충남아산": "충남아산 프로축구단",
    "충북청주": "충북청주 프로축구단", "파주": "파주 프런티어",
    "화성": "화성FC",
}


def get_html(url, data=None):
    request = Request(
        url, data=data,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
    )
    with urlopen(request, timeout=12) as response:
        return response.read(4_000_000).decode("utf-8", errors="replace")


class JLeagueTable(HTMLParser):
    """Read only the public standings site result table and its official links."""
    def __init__(self):
        super().__init__()
        self.rows = []
        self.in_table = False
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and "search-table" in attrs.get("class", "").split():
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.row = []
        elif self.row is not None and tag == "td":
            self.cell = ["", ""]
        elif self.cell is not None and tag == "a":
            self.cell[1] = attrs.get("href", "")

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.row.append((self.cell[0].strip(), self.cell[1]))
            self.cell = None
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[0] += data


def parse_jleague_table(html, league, url):
    table = JLeagueTable()
    table.feed(html)
    events = []
    for row in table.rows:
        if len(row) != 11 or row[1][0].translate(str.maketrans("Ｊ１２", "J12")) != J_LEAGUES[league]:
            continue
        date = re.match(r"(\d{2})/(\d{2})/(\d{2})", row[3][0])
        clock = re.fullmatch(r"(\d{1,2}):(\d{2})", row[4][0])
        home = re.search(r"/club/([a-z0-9]+)/(?:profile|day)", row[5][1])
        away = re.search(r"/club/([a-z0-9]+)/(?:profile|day)", row[7][1])
        if not (date and clock and home and away):
            continue
        y, m, d = (int(value) for value in date.groups())
        h, minute = (int(value) for value in clock.groups())
        if h > 23:
            continue
        start = datetime(2000 + y, m, d, h, minute, tzinfo=LOCAL_TIME)
        result = re.fullmatch(r"(\d+)\s*-\s*(\d+)", row[6][0])
        result_url = row[6][1]
        match = re.search(r"match_card_id=(\d+)", result_url)
        reference = urljoin(J_DATA, result_url) if match and result_url.startswith("/SFMS02/") else url
        events.append({
            "league": league, "id": "jleague-" + (match[1] if match else f"{start.isoformat()}-{home[1]}-{away[1]}"),
            "start": start.isoformat(), "complete": bool(result),
            "home": J_CLUBS.get(home[1], row[5][0]), "away": J_CLUBS.get(away[1], row[7][0]),
            "home_id": home[1], "away_id": away[1],
            "score": [int(result[1]), int(result[2])] if result else None,
            "venue": {"name": row[8][0]},
            "attendance": int(row[9][0].replace(",", "")) if re.fullmatch(r"[\d,]+", row[9][0]) else None,
            "source": ["J리그 공식 경기 기록", reference],
        })
    return events


K_ROW = re.compile(r'<div class="full-calendar-data-k([12])(?:\s[^"]*)?">(.*?)</div>', re.S)
K_TIP = re.compile(
    r"ddrivetip\('([^']+)','(\d+)','([^']+)','([^']+)','(\d{4}/\d{2}/\d{2})','(\d{1,2}:\d{2})','([^']*)'"
)
K_SCORE = re.compile(r'<span class="flR pr5">\s*\((\d+):(\d+)\)\s*</span>')


def parse_kleague_calendar(html, url):
    events = []
    for item in K_ROW.finditer(html):
        text = unescape(item[2])
        details = K_TIP.search(text)
        if not details:
            continue
        tournament, match_id, home, away, date, clock, stadium = details.groups()
        league = K_LEAGUES.get(tournament.rsplit(" ",1)[0])
        if league is None:
            continue
        start = datetime.strptime(f"{date} {clock}", "%Y/%m/%d %H:%M").replace(tzinfo=LOCAL_TIME)
        score = K_SCORE.search(text)
        events.append({
            "league": league, "id": f"kleague-{start.year}-{league}-{match_id}",
            "start": start.isoformat(),
            "home": K_CLUBS.get(home, home), "away": K_CLUBS.get(away, away),
            "complete": score is not None, "score": [int(score[1]), int(score[2])] if score else None,
            "venue": {"name": stadium.strip()},
            "source": ["K리그 공식 경기 일정·결과", url],
        })
    return events


def jleague_for_season(league, year):
    group = J_LEAGUES[league][-1]
    url = f"{J_DATA}/SFMS01/search?" + urlencode({"competition_frame_ids": group, "competition_years": year})
    return parse_jleague_table(get_html(url), league, url)


def kleague_for_month(year, month):
    query = urlencode({"selectYear": year, "selectMonth": f"{month:02d}"})
    url = f"{K_CALENDAR}?{query}"
    return [
        row for row in parse_kleague_calendar(get_html(url), url)
        if row["start"].startswith(f"{year}-{month:02d}-")
    ]


def fetch_events(fixtures):
    """Collect official league results independently so one source can go down."""
    tasks = set()
    for fixture in fixtures:
        league = fixture.get("league")
        if league not in J_LEAGUES and league not in K_LEAGUES.values():
            continue
        kickoff = datetime.fromisoformat(fixture["startsAt"]).astimezone(LOCAL_TIME)
        y, m = kickoff.year, kickoff.month
        if league in J_LEAGUES:
            season = y - (1 if y >= 2027 and m < 7 else 0)
            tasks.add((jleague_for_season, (league, season)))
            tasks.add((jleague_for_season, (league, season - 1)))
        else:
            month = kickoff.date().replace(day=1)
            for _ in range(3):
                tasks.add((kleague_for_month, (month.year, month.month)))
                month = (month - timedelta(days=1)).replace(day=1)
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fn, *args) for fn, args in tasks]
        for future in futures:
            try:
                for result in future.result():
                    results[result["id"]] = result
            except (OSError, ValueError):
                continue
    return list(results.values())
