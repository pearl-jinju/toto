"""Source-backed stadium notes and kickoff-hour city forecasts from MET Norway."""

import json
from gzip import GzipFile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError
from urllib.request import Request, urlopen


MET_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
MET_AGENT = "MatchIndex/1.0 https://github.com/pearl-jinju/toto"
KST = timezone(timedelta(hours=9))
MIN_MET_INTERVAL = timedelta(hours=3)
WEATHER_HORIZON = timedelta(days=9)
TIMEOUT = 6
_CACHE = {}
_CACHE_LOCK = Lock()
_MET_PAUSE_UNTIL = datetime.min.replace(tzinfo=timezone.utc)


# The coordinates are approximate city centers. They are never displayed as
# stadium measurements or used to infer a roof position.
_CITY_ROWS = """Inter.Co스타디움|올랜도|28.54|-81.38
루멘필드|시애틀|47.61|-122.33
컴뱅크스타디움|파라마타|-33.81|151.00
메루카리스타디움|가시마|35.97|140.64
산쿄프론티어가시와스타디움|가시와|35.87|139.98
노에비아스타디움고베|고베|34.69|135.20
알리안츠아레나|뮌헨|48.14|11.58
로브스타디움|트루아|48.30|4.08
산마메스스타디움|빌바오|43.26|-2.93
고미디어스타디움|오클랜드|-36.85|174.76
아지노모토스타디움|조후|35.65|139.54
마치다기온스타디움|마치다|35.55|139.45
상가스타디움바이교세라|가메오카|35.02|135.57
에디온피스윙히로시마|히로시마|34.39|132.46
소유스타디움|아키타|39.72|140.10
시티풋볼스테이션|도치기|36.38|139.73
닛파쓰미쓰자와경기장|요코하마|35.44|139.64
JIT리사이클잉크스타디움|고후|35.66|138.57
도야마현종합운동공원육상경기장|도야마|36.70|137.21
야마하스타디움|이와타|34.72|137.85
후지에다사커스타디움|후지에다|34.87|138.26
에키마에부동산스타디움|도스|33.38|130.51
이치고미야자키신토미풋볼스타디움|신토미|32.07|131.49
전주월드컵경기장|전주|35.82|127.15
포항스틸야드|포항|36.02|129.34
수원월드컵경기장|수원|37.26|127.03
부산구덕운동장|부산|35.10|129.01
폴리텍스타디움|고스퍼드|-33.43|151.34
유밴스도도로키스타디움바이후지쯔|가와사키|35.58|139.66
얀마하나사카스타디움|오사카|34.67|135.50
파나소닉스타디움스이타|스이타|34.77|135.52
강릉하이원아레나|강릉|37.75|128.88
인천축구전용경기장|인천|37.47|126.63
김포솔터축구장|김포|37.62|126.71
탄천종합운동장|성남|37.42|127.13
카요스타디움|레드클리프|-27.23|153.11
더덴스타디움|런던|51.51|-0.13
캐로로드|노리치|52.63|1.30
세인트메리즈스타디움|사우샘프턴|50.91|-1.40
에티하드스타디움|맨체스터|53.48|-2.24
멘디소르로사|비토리아가스테이스|42.85|-2.67
주세페시니갈리아스타디움|코모|45.81|9.09
올림피코로마스타디움|로마|41.90|12.50
바이아레나|레버쿠젠|51.05|6.99
도이체방크파크|프랑크푸르트|50.11|8.68
안데어알텐푀르스테라이|베를린|52.52|13.41
이스타보루시아파크|묀헨글라트바흐|51.18|6.44
우르사팜아레나|슈피젠엘버스베르크|49.32|7.13
터프시트커뮤니티스타디움|호리치|53.60|-2.54
프로앰팩스타디움|링컨|53.23|-0.54
리버사이드스타디움|미들즈브러|54.57|-1.23
브라몰레인|셰필드|53.38|-1.47
bet365스타디움|스토크온트렌트|53.01|-2.18
스완지닷컴스타디움|스완지|51.62|-3.94
런던스타디움|런던|51.51|-0.13
몰리뉴스타디움|울버햄프턴|52.59|-2.13
빌라파크|버밍엄|52.48|-1.90
바이탈리티스타디움|본머스|50.72|-1.88
스탬포드브릿지|런던|51.51|-0.13
코번트리빌딩소사이어티아레나|코번트리|52.41|-1.51
토트넘홋스퍼스타디움|런던|51.51|-0.13
바예카스스타디움|마드리드|40.42|-3.70
호페르트스타디움|네이메헌|51.84|5.86
알리안츠리비에라|니스|43.70|7.27
엔니오타르디니스타디움|파르마|44.80|10.33
세인트제임스파크|뉴캐슬|54.98|-1.61
라몬산체스피스후안|세비야|37.39|-5.98
펠틴스아레나|겔젠키르헨|51.51|7.08
페예노르트스타디움|로테르담|51.92|4.48
할겐바르트스타디움|위트레흐트|52.09|5.12
질레트스타디움|폭스버러|42.07|-71.25
디에고아르만도마라도나스타디움|나폴리|40.85|14.27
볼라르트들렐리스스타디움|랑스|50.43|2.83
데카트론아레나피에르모루아스타디움|빌뇌브다스크|50.62|3.13
루이2세스타디움|모나코|43.73|7.42
라메노스타디움|스트라스부르|48.58|7.75
베르나베우스타디움|마드리드|40.42|-3.70
BUKO스타디움|펠선자위트|52.46|4.66
유로보그|흐로닝언|53.22|6.57
도요타스타디움텍사스|프리스코|33.15|-96.82
Nu스타디움|마이애미|25.76|-80.19
헨리스타디움|웰링턴|-41.29|174.78
나루토오츠카스포츠파크포카리스웨트스타디움|나루토|34.17|134.61
김천종합운동장|김천|36.14|128.11
광주월드컵경기장|광주|35.16|126.85
대구iM뱅크PARK|대구|35.87|128.60
광양축구전용구장|광양|34.94|127.70
파주스타디움|파주|37.76|126.78
목동종합운동장|서울|37.57|126.98
데그롤슈베스테|엔스헤데|52.22|6.89
알리안츠스타디움토리노|토리노|45.07|7.69
터프무어|번리|53.79|-2.24
스포티파이캄노우|바르셀로나|41.39|2.17
요한크루이프아레나|암스테르담|52.37|4.89
스파르타스타디움헷카스틸|로테르담|51.92|4.48
MKM스타디움|헐|53.75|-0.34
레나토달라라스타디움|볼로냐|44.50|11.34
마페이스타디움|레조에밀리아|44.70|10.63
장부앵스타디움파리|파리|48.86|2.35
WWK아레나|아우크스부르크|48.37|10.90
엘사르디네로|산탄데르|43.46|-3.81
데아델라르스호르스트|데벤터르|52.26|6.16
이브알랑마스타디움|로리앙|47.75|-3.37
안필드|리버풀|53.41|-2.98
베저스타디움|브레멘|53.08|8.80
주세페메아차스타디움|밀라노|45.46|9.19
엘사다르스타디움|팜플로나|42.82|-1.64
뉴발란스아레나|베르가모|45.70|9.67
CEPAC벨로드롬|마르세유|43.30|5.37
콜리세움|헤타페|40.31|-3.73
지오디스파크|내슈빌|36.16|-86.78
시트긱스타디움|브리지뷰|41.75|-87.81
BC플레이스|밴쿠버|49.28|-123.12
이스티클롤스타디움|페르가나|40.39|71.79
잠실야구장|서울|37.57|126.98
사직야구장|부산|35.18|129.07
수원KT위즈파크|수원|37.26|127.03
광주기아챔피언스필드|광주|35.16|126.85
대구삼성라이온즈파크|대구|35.87|128.60
인천SSG랜더스필드|인천|37.47|126.63
창원NC파크|창원|35.23|128.68
대전한화생명볼파크|대전|36.35|127.38"""
_CITIES = {}
for row in _CITY_ROWS.splitlines():
    name, city, lat, lon = row.split("|")
    _CITIES[name.casefold()] = (city, float(lat), float(lon))


_ROOFS = {
    "노에비아스타디움고베": ("비셀 고베 · 구장 안내", "https://www.vissel-kobe.co.jp/news/article/24973.html"),
    "펠틴스아레나": ("펠틴스 아레나 · 시설", "https://en.veltins-arena.de/veltins-arena/zahlen-und-fakten/"),
    "베르나베우스타디움": ("레알 마드리드 · 베르나베우", "https://bernabeu.realmadrid.com/en-US/corporate-events/terreno-de-juego"),
    "데카트론아레나피에르모루아스타디움": ("피에르 모루아 · 시설", "https://www.stade-pierre-mauroy.com/presentation/le-stade"),
    "요한크루이프아레나": ("요한 크루이프 아레나 · 지붕 안내", "https://www.johancruijffarena.nl/en/news/johan-cruijff-arena/werkzaamheden-aan-het-arena-dak-in-september/"),
    "bc플레이스": ("BC 플레이스 · 지붕 안내", "https://www.bcplace.com/faqs/"),
}
_FIXED_DOME = {
    "고척스카이돔": ("서울시설공단 · 고척스카이돔", "https://www.sisul.or.kr/open_content/skydome/"),
    "도쿄돔": ("도쿄돔 · 시설 개요", "https://www.tokyo-dome.co.jp/en/dome/about/"),
}

_INDOOR = (
    ("NBA", ("NBA · 경기장 목록", "https://www.nba.com/news/all-30-nba-arenas-by-team")),
    ("WKBL", ("WKBL · 일정과 경기장", "https://www.wkbl.or.kr/m/game/schedule.asp")),
    ("KOVO", ("KOVO · 공식 리그", "https://www.kovo.co.kr/")),
    ("KBL", ("KBL · 공식 리그", "https://www.kbl.or.kr/")),
)


def venue_key(venue):
    return "".join((venue or "").casefold().split())


def load_venue_profiles():
    path = Path(__file__).resolve().parents[1] / "data" / "venue_profiles.json"
    with path.open(encoding="utf-8") as source:
        profiles = json.load(source)
    return {venue_key(alias): profile for profile in profiles for alias in profile["aliases"]}


_VENUE_PROFILES = load_venue_profiles()


def venue_feature(name, facts, watch, source, references=()):
    return {
        "category": "venue", "title": "경기장 특징", "value": name,
        "venueFacts": facts, "text": watch, "source": source, "venueReferences": list(references),
    }


def event_time(starts_at):
    try:
        date = datetime.fromisoformat(starts_at)
        return date.astimezone(timezone.utc) if date.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def header_date(header):
    try:
        value = parsedate_to_datetime(header)
        return value.astimezone(timezone.utc) if value.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def forecast_url(lat, lon):
    return f"{MET_URL}?lat={lat:.2f}&lon={lon:.2f}"


def forecast(lat, lon):
    global _MET_PAUSE_UNTIL
    now = datetime.now(timezone.utc)
    key = (lat, lon)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now < cached[0]:
            return cached[2]
        if now < _MET_PAUSE_UNTIL:
            return None
    headers = {"User-Agent": MET_AGENT, "Accept": "application/json", "Accept-Encoding": "gzip"}
    if cached and cached[1]:
        headers["If-Modified-Since"] = cached[1]
    default_expiry = now + MIN_MET_INTERVAL
    try:
        with urlopen(Request(forecast_url(lat, lon), headers=headers), timeout=TIMEOUT) as response:
            if response.headers.get("Content-Encoding") == "gzip":
                with GzipFile(fileobj=response) as compressed:
                    payload = json.load(compressed)["properties"]
            else:
                payload = json.load(response)["properties"]
            if not isinstance(payload.get("timeseries"), list):
                raise ValueError("Missing MET forecast series")
            expiry = max(default_expiry, header_date(response.headers.get("Expires")) or default_expiry)
            modified = response.headers.get("Last-Modified")
    except HTTPError as error:
        if error.code == 304 and cached:
            payload = cached[2]
            expiry = max(default_expiry, header_date(error.headers.get("Expires")) or default_expiry)
            modified = cached[1]
        else:
            if error.code in (403, 429):
                raw = error.headers.get("Retry-After", "")
                delay = timedelta(seconds=min(int(raw), 86400)) if raw.isascii() and raw.isdecimal() and len(raw) <= 8 else timedelta(hours=1)
                with _CACHE_LOCK:
                    _MET_PAUSE_UNTIL = max(_MET_PAUSE_UNTIL, now + delay, header_date(raw) or now)
            payload, modified, expiry = None, None, default_expiry
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        payload, modified, expiry = None, None, default_expiry
    with _CACHE_LOCK:
        _CACHE[key] = (expiry, modified, payload)
    return payload


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def weather_flags(temp, wind, rain, symbol):
    wet = (numeric(rain) and rain > 0) or any(word in symbol for word in ("rain", "sleet", "snow"))
    return wet, "fog" in symbol, numeric(wind) and wind >= 8, numeric(temp) and temp <= 0, numeric(temp) and temp >= 29


def conditions(sport, temp, wind, rain, symbol):
    wet, fog, windy, freezing, hot = weather_flags(temp, wind, rain, symbol)
    if sport == "야구":
        if fog and freezing:
            return "안개와 영하 · 외야 시야와 발밑 확인", "뜬공을 읽기 어렵고 실제로 얼어붙은 지면에서는 발이 밀릴 수 있습니다. 두 조건만으로 득점 방향은 알기 어렵습니다."
        if fog:
            return "안개가 끼면 뜬공이 관건", "외야수가 공을 끝까지 따라가는지 보세요. 안개만으로 득점 방향을 판단하기는 어렵습니다."
        if wet:
            return "비가 오면 공을 쥐는 감각과 수비 발밑 확인", "젖은 공은 투수의 그립과 제구에 영향을 줄 수 있습니다. 수비 땅볼 처리와 경기 중단 여부도 확인하세요."
        if windy:
            return "뜨는 타구가 바람을 탈 수 있음", "바람이 외야로 불면 뜬공이 더 뻗고 반대면 줄 수 있습니다. 도시 풍속만으로 타구 방향은 판단하기 어렵습니다."
        if freezing:
            return "낮은 기온이면 워밍업과 구장 운영 확인", "공이 차가워지거나 발밑이 얼 수 있습니다. 실제 그라운드 상태와 경기 운영 공지를 확인하세요."
        if hot:
            return "더위 속 투수 체력과 교체 시점 확인", "투구 수가 쌓인 뒤에도 구위와 제구가 유지되는지 보세요."
        if not (numeric(temp) and numeric(wind) and numeric(rain)):
            return "도시 예보 항목 일부 확인", "표시된 수치를 참고해 경기 시간대 조건을 확인하세요."
        return "도시 예보에서 두드러진 날씨 신호 없음", "선발과 불펜 상태, 타선 구성을 먼저 보세요."

    if fog and freezing:
        return "안개와 영하 · 긴 공과 수비 발밑 주목", "수비와 골키퍼가 높은 공을 늦게 볼 수 있고, 잔디가 실제로 얼면 방향을 틀 때 발이 밀릴 수 있습니다. 두 조건만으로 득점 방향은 판단하기 어렵습니다."
    if fog:
        return "안개가 끼면 높은 공을 놓치기 쉬움", "수비와 골키퍼가 긴 패스와 크로스를 얼마나 빨리 읽는지 보세요. 안개만으로 득점 방향을 정하기는 어렵습니다."
    if freezing:
        return "영하라면 발밑 상태부터 확인", "잔디가 실제로 얼면 급정지하거나 방향을 틀 때 발이 밀릴 수 있습니다. 지중 난방이나 관리에 따라 달라져 기온만으로 득점 방향은 판단하기 어렵습니다."
    if wet:
        return "비가 오면 패스 길이와 첫 터치에 주목", "잔디가 젖으면 땅볼이 미끄러져 지나갈 수 있고 물이 고인 곳에서는 공이 멈출 수 있습니다. 짧은 패스를 받는 선수와 골키퍼의 첫 처리를 보세요."
    if windy:
        return "바람이 강하면 높은 패스의 오차가 커질 수 있음", "크로스나 긴 패스가 휘면 바닥으로 공을 보내는 쪽이 변수의 영향을 덜 받을 수 있습니다. 실제 구장 바람을 함께 보세요."
    if hot:
        return "더우면 전방 압박이 끝까지 유지되는지 확인", "공을 빼앗으려 달려드는 빈도와 후반 교체 시점을 보세요. 기온만으로 유리한 팀을 고르기는 어렵습니다."
    if not (numeric(temp) and numeric(wind) and numeric(rain)):
        return "도시 예보 항목 일부 확인", "표시된 수치를 참고해 경기 시간대 조건을 확인하세요."
    return "도시 예보에서 두드러진 날씨 신호 없음", "팀의 선발과 경기 스타일을 먼저 보세요. 구장 잔디와 바람은 현장에서 달라질 수 있습니다."


def weather_visual(sport, temp, wind, rain, symbol, has_roof):
    readings = [
        {"label": label, "value": value}
        for label, value in (
            ("기온", f"{temp:g}°C" if numeric(temp) else None),
            ("바람", f"{wind * 3.6:.0f}km/h" if numeric(wind) else None),
            ("시간당 강수량", f"{rain:g}mm" if numeric(rain) else None),
        )
        if value is not None
    ]
    if has_roof:
        return {"condition": "roof", "impact": "unknown", "label": "지붕 개폐 미확인", "readings": readings}

    wet, fog, windy, freezing, hot = weather_flags(temp, wind, rain, symbol)
    if sport == "야구":
        candidates = (("fog", fog), ("rain", wet), ("wind", windy), ("frost", freezing), ("heat", hot))
    else:
        candidates = (("fog", fog), ("frost", freezing), ("rain", wet), ("wind", windy), ("heat", hot))
    condition = next((name for name, active in candidates if active), None)
    severe = (
        "thunder" in symbol
        or "heavyrain" in symbol
        or (numeric(rain) and rain >= 10)
        or (numeric(wind) and wind >= 12)
    )
    if condition is None:
        condition = "calm" if len(readings) == 3 else "unknown"
        impact = "low" if condition == "calm" else "unknown"
    else:
        impact = "high" if severe else "watch"
    labels = {
        "calm": "뚜렷한 날씨 변수 없음",
        "rain": "비 예보",
        "wind": "바람 강함",
        "fog": "안개 예보",
        "frost": "영하권",
        "heat": "더운 날씨",
        "unknown": "예보 자료 부족",
    }
    label = labels[condition]
    if condition == "fog" and freezing:
        label = "안개 · 영하권"
    return {"condition": condition, "impact": impact, "label": label, "readings": readings}


def make_weather(sport, city_data, start, data, has_roof):
    if data is None:
        return None
    city, lat, lon = city_data
    hour = start.replace(minute=0, second=0, microsecond=0)
    sample = next((row for row in data["timeseries"] if event_time(row.get("time")) == hour), None)
    if not sample:
        return None
    readings = sample.get("data", {})
    current = readings.get("instant", {}).get("details", {})
    interval = readings.get("next_1_hours", {})
    temp = current.get("air_temperature")
    wind = current.get("wind_speed")
    rain = interval.get("details", {}).get("precipitation_amount")
    symbol = interval.get("summary", {}).get("symbol_code", "") or ""
    measures = []
    if numeric(temp):
        measures.append(f"{temp:g}°C")
    if numeric(wind):
        measures.append(f"바람 {wind * 3.6:.0f}km/h")
    if numeric(rain):
        measures.append(f"1시간 강수량 {rain:g}mm")
    if not measures:
        return None
    value, tip = conditions(sport, temp, wind, rain, symbol)
    if has_roof:
        value = "지붕이 열리는지 먼저 확인"
        tip = "개폐식 지붕이 닫히면 실외 강수와 바람의 영향이 줄어듭니다. 이 경기의 개폐 상태는 확인되지 않았습니다."
    reference = None
    if not has_roof and sport == "축구":
        if value.startswith("더우면"):
            reference = ["2014 월드컵 · 더위와 스프린트 연구", "https://doi.org/10.1136/BJSPORTS-2014-094449"]
        elif value.startswith("바람이 강하면"):
            reference = ["바람을 반영한 축구공 궤적 연구", "https://doi.org/10.1155/jama/7425581"]
        elif value.startswith("비가 오면"):
            reference = ["FIFA · 젖은 구장과 공 반응 시험 지침", "https://www.uefa.com/newsfiles/38018.pdf"]
    issued = data.get("meta", {}).get("updated_at")
    issued_at = event_time(issued)
    model_hour = f"{hour.astimezone(KST):%m/%d %H:%M} KST"
    model = f" · 발표 {issued_at.astimezone(KST):%m/%d %H:%M} KST" if issued_at else ""
    tag = None
    if not has_roof:
        if "fog" in symbol:
            tag = "fog"
        elif numeric(temp) and temp <= 0:
            tag = "frost"
        elif numeric(wind) and wind >= 8:
            tag = "wind"
        elif numeric(rain) and rain > 0:
            tag = "rain"
        elif numeric(temp) and temp >= 29:
            tag = "heat"
    return {
        "forecastTag": tag,
        "visual": weather_visual(sport, temp, wind, rain, symbol, has_roof),
        "forecastBasis": {
            "city": city, "latitude": lat, "longitude": lon, "validAt": hour.isoformat(),
            "issuedAt": issued_at.isoformat() if issued_at else None,
        },
        "category": "weather", "title": f"{city} 도심 경기 시간대 예보", "value": value,
        "text": f"{tip} {model_hour} · {' · '.join(measures)}{model}. 도심 예보입니다.",
        "source": ["MET Norway · Locationforecast (CC BY 4.0)", forecast_url(lat, lon)], "date": hour.isoformat(),
        **({"reference": reference} if reference else {}),
    }


def enrich_fixtures(fixtures, *, round_source=None):
    """Return sourced factors for every fixture, with forecasts only before kickoff."""
    now = datetime.now(timezone.utc)
    output = {}
    scheduled_forecasts = {}
    cities = {}
    for fixture in fixtures:
        number = fixture["number"]
        key = venue_key(fixture.get("venue"))
        start = event_time(fixture.get("startsAt"))
        league = fixture.get("league", "")
        sport = fixture.get("sport", "")
        factors = output.setdefault(number, [])
        profile = _VENUE_PROFILES.get(key)
        if profile:
            primary, *references = profile["sources"]
            factors.append(venue_feature(profile["name"], profile["facts"], profile["watch"], primary, references))
        indoor = next((source for name, source in _INDOOR if league == name or league.startswith(f"{name} ")), None)
        if indoor:
            if not profile and fixture.get("venue"):
                watch = ("실내 바닥에서 멈췄다가 다시 뛸 때, 선수의 발이 미끄러지지 않는지 보세요."
                         if sport == "농구" else "서브를 받으려고 발을 옮길 때 바닥이 잘 잡히는지, 리시브 자세를 제때 잡는지 보세요.")
                factors.append(venue_feature(fixture["venue"], [["환경", "실내 코트"]], watch, list(indoor)))
            action = ("실외 바람과 비는 코트에 직접 닿지 않습니다. 후반 슛이 짧아지거나 수비 복귀가 늦는지 보려면 직전 경기와 휴식 간격을 함께 보세요."
                if sport == "농구" else "실외 바람이 서브 궤도에 직접 영향을 주지 않습니다. 서브 리시브가 흔들리는지와 공격수가 높은 공을 처리하는지 보세요.")
            factors.append({"category":"weather","title":"실내 경기 환경","value":"바람·비의 직접 영향이 작은 실내 코트","text":action,"source":list(indoor),"visual":{"condition":"indoor","impact":"low","label":"실내 코트"}})
            continue
        if key in _FIXED_DOME:
            if not profile:
                factors.append(venue_feature(fixture["venue"], [["구조", "고정식 지붕의 돔"]],
                                             "외부 바람보다 실내 표면에서 공이 어떻게 움직이는지 보세요.", list(_FIXED_DOME[key])))
            factors.append({"category":"weather","title":"돔 구장 환경","value":"강수와 바람의 직접 영향이 작은 돔","text":"외부 비·바람 대신 실제 실내 온도와 경기장 같은 조건에서의 선수 기록을 확인할 만합니다.","source":list(_FIXED_DOME[key]),"visual":{"condition":"indoor","impact":"low","label":"실내 돔"}})
            continue
        if key in _ROOFS:
            factors.append({"category":"venue","title":"경기장 지붕","value":"개폐식 지붕","text":"지붕 개폐에 따라 바람과 비의 영향이 달라집니다. 이 경기의 개폐 상태는 공지에서 확인해야 합니다.","source":list(_ROOFS[key]),"visual":{"condition":"roof","impact":"unknown","label":"지붕 개폐 미확인"}})
        city_data = _CITIES.get(key)
        if not city_data:
            continue
        city, lat, lon = city_data
        if round_source and key not in _ROOFS and not profile:
            factors.append({"category":"venue","title":"개최 도시","value":city,"text":f"베트맨에 등록된 경기장은 {fixture['venue']}입니다.","source":["베트맨 · 회차 경기장",round_source]})
        if fixture.get("status") in {"cancelled", "finished"} or not start or not now < start <= now + WEATHER_HORIZON:
            continue
        cities[(lat,lon)] = None
        scheduled_forecasts[number] = (sport, city_data, start, key in _ROOFS)

    if cities:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for key, payload in zip(cities, pool.map(lambda point: forecast(*point), cities), strict=True):
                cities[key] = payload
        for number,(sport, city_data, start, has_roof) in scheduled_forecasts.items():
            factor = make_weather(sport, city_data, start, cities[city_data[1:]], has_roof)
            if factor:
                output[number].append(factor)
    return output
