"""Match league feeds to official Betman fixtures and analyze pre-match results."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import re
import unicodedata
from urllib.parse import urlsplit


KST = timezone(timedelta(hours=9))
KICKOFF_TOLERANCE = timedelta(hours=3)
ALIAS_ROWS = """Arsenal|아스널|Arsenal FC
Aston Villa|애스턴 빌라|아스톤 빌라|Aston Villa FC
Bournemouth|AFC본머스|본머스|AFC Bournemouth
Brentford|브렌트퍼드|브렌트포드|Brentford FC
Brighton & Hove Albion|브라이턴&호브 앨비언|브라이튼 앤 호브 알비온|브라이턴|브라이튼|Brighton and Hove Albion|Brighton & Hove Albion FC|Brighton
Burnley|번리|Burnley FC
Chelsea|첼시|Chelsea FC
Coventry City|코번트리 시티|Coventry City FC|Coventry
Crystal Palace|크리스털 팰리스|크리스탈 팰리스|Crystal Palace FC
Everton|에버턴|에버튼|Everton FC
Fulham|풀럼|Fulham FC
Hull City|헐 시티|Hull City AFC|Hull
Ipswich Town|입스위치 타운|Ipswich Town FC|Ipswich
Leeds United|리즈 유나이티드|리즈|Leeds United FC|Leeds
Leicester City|레스터 시티|Leicester City FC|Leicester
Liverpool|리버풀|Liverpool FC
Manchester City|맨체스터 시티|맨시티|Manchester City FC|Man City
Manchester United|맨체스터 유나이티드|맨유|Manchester United FC|Man United|Man Utd
Newcastle United|뉴캐슬 유나이티드|뉴캐슬|Newcastle United FC|Newcastle
Nottingham Forest|노팅엄 포리스트|노팅엄 포레스트|노팅엄|Nottingham Forest FC|Nott'm Forest
Sunderland|선덜랜드|Sunderland AFC
Tottenham Hotspur|토트넘 홋스퍼|토트넘|Tottenham Hotspur FC|Tottenham|Spurs
West Ham United|웨스트햄 유나이티드|웨스트햄|West Ham United FC|West Ham
Wolverhampton Wanderers|울버햄튼 원더러스|울버햄튼|울버햄프턴|Wolverhampton Wanderers FC|Wolves
Norwich City|노리치 시티|Norwich City FC|Norwich
Derby County|더비 카운티|Derby County FC|Derby
Wrexham|렉섬|Wrexham AFC|Wrexham FC
Lincoln City|링컨 시티|Lincoln City FC
Middlesbrough|미들즈브러|Middlesbrough FC
Millwall|밀월|Millwall FC
Birmingham City|버밍엄 시티|Birmingham City FC|Birmingham
Bolton Wanderers|볼턴 원더러스|볼턴|Bolton Wanderers FC|Bolton
Bristol City|브리스틀 시티|브리스톨 시티|Bristol City FC
Blackburn Rovers|블랙번 로버스|Blackburn Rovers FC|Blackburn
Southampton|사우샘프턴|사우스햄프턴|Southampton FC
Sheffield United|셰필드 유나이티드|Sheffield United FC|Sheff Utd
Sheffield Wednesday|셰필드 웬즈데이|Sheffield Wednesday FC|Sheff Wed
Swansea City|스완지 시티|Swansea City AFC|Swansea
Stoke City|스토크 시티|Stoke City FC|Stoke
Watford|왓포드|Watford FC
West Bromwich Albion|웨스트브로미치 앨비언|웨스트 브롬위치 앨비언|West Bromwich Albion FC|West Brom
Charlton Athletic|찰턴 애슬레틱|찰튼 애슬레틱|Charlton Athletic FC|Charlton
Cardiff City|카디프 시티|Cardiff City FC|Cardiff
Queens Park Rangers|퀸즈파크 레인저스|Queens Park Rangers FC|QPR
Portsmouth|포츠머스|Portsmouth FC
Preston North End|프레스턴 노스엔드|Preston North End FC|Preston
Oxford United|옥스퍼드 유나이티드|Oxford United FC
Wigan Athletic|위건 애슬레틱|Wigan Athletic FC
Huddersfield Town|허더즈필드 타운|Huddersfield Town FC
Blackpool|블랙풀|Blackpool FC
Reading|레딩|Reading FC
Plymouth Argyle|플리머스 아가일|Plymouth Argyle FC
Bayern Munich|바이에른 뮌헨|Bayern München|FC Bayern München|FC Bayern Munich|Bayern
Borussia Dortmund|도르트문트|보루시아 도르트문트|BVB
Borussia Mönchengladbach|묀헨글라트바흐|보루시아 묀헨글라트바흐|Borussia Monchengladbach|Gladbach
Bayer Leverkusen|바이어04 레버쿠젠|레버쿠젠|Bayer 04 Leverkusen|Bayer 04
RB Leipzig|RB라이프치히|라이프치히|RasenBallsport Leipzig
SC Freiburg|SC프라이부르크|프라이부르크|Freiburg
TSG Hoffenheim|TSG1899 호펜하임|호펜하임|TSG 1899 Hoffenheim|1899 Hoffenheim|Hoffenheim
Mainz 05|FSV마인츠05|마인츠|1. FSV Mainz 05|FSV Mainz 05|Mainz
VfB Stuttgart|VfB슈투트가르트|슈투트가르트|Stuttgart
Werder Bremen|베르더 브레멘|SV Werder Bremen|Bremen
Schalke 04|샬케04|FC Schalke 04|Schalke
FC Augsburg|아우크스부르크|Augsburg
SV Elversberg|엘버스베르크|SV 07 Elversberg|Elversberg
Union Berlin|우니온 베를린|1. FC Union Berlin|FC Union Berlin
FC Cologne|쾰른|FC쾰른|1. FC Köln|FC Köln|1. FC Koln|Cologne|FC Koln
SC Paderborn|파더보른07|파더보른|SC Paderborn 07|Paderborn
Eintracht Frankfurt|프랑크푸르트|아인트라흐트 프랑크푸르트|Frankfurt
Hamburger SV|함부르크|Hamburg SV|Hamburg
VfL Wolfsburg|볼프스부르크|Wolfsburg
1. FC Heidenheim|하이덴하임|Heidenheim
St. Pauli|장크트 파울리|FC St. Pauli
FC Barcelona|바르셀로나|FC바르셀로나|Barcelona
Real Madrid|레알 마드리드|Real Madrid CF
Real Betis|레알 베티스|Real Betis Balompié|Betis
Real Sociedad|레알 소시에다드|Real Sociedad de Fútbol
Atletico Madrid|아틀레티코 마드리드|Atlético de Madrid|Atlético Madrid|Atletico de Madrid|Atl Madrid
Athletic Club|아틀레틱 빌바오|Athletic Bilbao|Athletic Club Bilbao
RCD Espanyol|RCD에스파뇰|에스파뇰|Espanyol|RCD Espanyol de Barcelona
Celta Vigo|RC셀타데비고|셀타 비고|RC Celta de Vigo|Celta de Vigo|RC Celta
Deportivo La Coruña|데포르티보 아코루냐|Deportivo de La Coruña|Deportivo La Coruna|RC Deportivo|Deportivo
Racing Santander|라싱 산탄데르|Real Racing Club|Real Racing Club de Santander
Rayo Vallecano|라요 바예카노|Rayo Vallecano de Madrid
Malaga|말라가|Málaga CF|Malaga CF
Valencia|발렌시아|Valencia CF
Villarreal|비야레알|Villarreal CF
Sevilla|세비야|Sevilla FC
Alaves|알라베스|Deportivo Alavés
Osasuna|오사수나|CA Osasuna
Getafe|헤타페|Getafe CF
Mallorca|마요르카|RCD Mallorca
Girona|지로나|Girona FC
Elche|엘체|Elche CF
Real Oviedo|레알 오비에도|Oviedo
Levante|레반테|Levante UD
Las Palmas|라스팔마스|UD Las Palmas
Leganes|레가네스|CD Leganés
Real Valladolid|레알 바야돌리드|Valladolid
Granada|그라나다|Granada CF
AC Milan|AC밀란|AC 밀란|밀란|Milan
Inter Milan|인테르나치오날레 밀라노|인터 밀란|인테르|FC Internazionale Milano|Internazionale|Inter
AS Roma|AS로마|로마|Roma
Napoli|SSC나폴리|나폴리|SSC Napoli
Lazio|SS라치오|라치오|SS Lazio
Lecce|US레체|레체|US Lecce
Sassuolo|US사수올로|사수올로|US Sassuolo|US Sassuolo Calcio
Venezia|베네치아|Venezia FC
Bologna|볼로냐|Bologna FC 1909
Atalanta|아탈란타BC|아탈란타|Atalanta BC
Udinese|우디네세|Udinese Calcio
Juventus|유벤투스|Juventus FC
Genoa|제노아|Genoa CFC
Cagliari|칼리아리|Cagliari Calcio
Como|코모1907|코모|Como 1907
Torino|토리노|Torino FC
Parma|파르마|Parma Calcio 1913
Frosinone|프로시노네|Frosinone Calcio
Fiorentina|피오렌티나|ACF Fiorentina
Cremonese|크레모네세|US Cremonese
Pisa|피사|Pisa SC
Brescia|브레시아|Brescia Calcio
Monza|몬차|AC Monza
Hellas Verona|엘라스 베로나|베로나|Verona
Empoli|엠폴리|Empoli FC
Spezia|스페치아|Spezia Calcio
Lorient|로리앙|FC Lorient
Le Mans|르망FC|르망|Le Mans FC
Le Havre|르아브르AC|르아브르|Le Havre AC
Lille|릴OSC|릴|LOSC Lille|Lille OSC
Rennes|스타드 렌|렌|Stade Rennais|Stade Rennais FC
Brest|스타드 브레스투아29|브레스트|Stade Brestois 29|Stade Brestois
Angers|앙제SCO|앙제|Angers SCO
Lyon|올랭피크 리옹|리옹|Olympique Lyonnais
Marseille|올랭피크드 마르세유|올랭피크 마르세유|마르세유|Olympique de Marseille
Toulouse|툴루즈|Toulouse FC
Troyes|트루아AC|트루아|ESTAC Troyes|ES Troyes AC
Paris Saint-Germain|파리 생제르맹|PSG|Paris Saint Germain|Paris SG
Paris FC|파리FC
Auxerre|AJ오세르|오세르|AJ Auxerre
AS Monaco|AS모나코|모나코|Monaco
Nice|OGC니스|니스|OGC Nice
Lens|RC랑스|랑스|RC Lens
Strasbourg|RC스트라스부르|스트라스부르|RC Strasbourg Alsace|RC Strasbourg
Nantes|낭트|FC Nantes
Metz|메스|FC Metz
Reims|랭스|Stade de Reims
Montpellier|몽펠리에|Montpellier HSC
Saint-Etienne|생테티엔|AS Saint-Étienne
Ajax Amsterdam|AFC아약스|아약스|AFC Ajax|Ajax
ADO Den Haag|ADO덴하흐|덴하흐
AZ Alkmaar|AZ알크마르|알크마르|AZ
NEC Nijmegen|NEC네이메헌|NEC 네이메헌|NEC|N.E.C. Nijmegen
PEC Zwolle|PEC즈볼러|즈볼러|Zwolle
PSV Eindhoven|PSV에인트호번|에인트호번|PSV
SC Cambuur|SC캄뷔르|캄뷔르|Cambuur
SC Heerenveen|SC헤이렌베인|헤이렌베인|Heerenveen
Go Ahead Eagles|고어헤드 이글스|고 어헤드 이글스
Willem II|빌럼II|빌렘 II|Willem II Tilburg
Sparta Rotterdam|스파르타 로테르담
Excelsior|엑셀시오르 로테르담|엑셀시오르|Excelsior Rotterdam|SBV Excelsior
FC Utrecht|위트레흐트|Utrecht
Telstar|텔스타|SC Telstar
FC Twente|트벤테|Twente
Feyenoord|페예노르트|Feyenoord Rotterdam
Fortuna Sittard|포르튀나 시타르트|포르투나 시타르트
FC Groningen|흐로닝언|Groningen
NAC Breda|NAC브레다|브레다
Heracles Almelo|헤라클레스 알멜로
FC Volendam|폴렌담|Volendam
RKC Waalwijk|발베이크|RKC발베이크
Atlanta Hawks|애틀랜타 호크스|Hawks
Boston Celtics|보스턴 셀틱스|Celtics
Brooklyn Nets|브루클린 네츠|Nets
Charlotte Hornets|샬럿 호네츠|Hornets
Chicago Bulls|시카고 불스|Bulls
Cleveland Cavaliers|클리블랜드 캐벌리어스|클리블랜드 캐벌리어즈|Cavaliers
Dallas Mavericks|댈러스 매버릭스|Mavericks
Denver Nuggets|덴버 너게츠|Nuggets
Detroit Pistons|디트로이트 피스톤스|Pistons
Golden State Warriors|골든스테이트 워리어스|골든스테이트 워리어즈|Warriors
Houston Rockets|휴스턴 로케츠|Rockets
Indiana Pacers|인디애나 페이서스|Pacers
LA Clippers|LA 클리퍼스|로스앤젤레스 클리퍼스|Los Angeles Clippers|Clippers
Los Angeles Lakers|LA 레이커스|로스앤젤레스 레이커스|LA Lakers|Lakers
Memphis Grizzlies|멤피스 그리즐리스|Grizzlies
Miami Heat|마이애미 히트|Heat
Milwaukee Bucks|밀워키 벅스|Bucks
Minnesota Timberwolves|미네소타 팀버울브스|Timberwolves
New Orleans Pelicans|뉴올리언스 펠리컨스|뉴올리언스 펠리컨즈|Pelicans
New York Knicks|뉴욕 닉스|Knicks
Oklahoma City Thunder|오클라호마시티 썬더|Oklahoma City|Thunder
Orlando Magic|올랜도 매직|Magic
Philadelphia 76ers|필라델피아 76s|필라델피아 세븐티식서스|Philadelphia 76s|76ers
Phoenix Suns|피닉스 선즈|Suns
Portland Trail Blazers|포틀랜드 트레일블레이저스|포틀랜드 트레일 블레이저스|Trail Blazers
Sacramento Kings|새크라멘토 킹스|Kings
San Antonio Spurs|샌안토니오 스퍼스|San Antonio
Toronto Raptors|토론토 랩터스|Raptors
Utah Jazz|유타 재즈|Jazz
Washington Wizards|워싱턴 위저즈|Wizards
Macarthur FC|맥아서FC|Macarthur
Melbourne Victory|멜버른 빅토리|Melbourne Victory FC
Melbourne City|멜버른 시티|Melbourne City FC
Brisbane Roar|브리즈번 로어|Brisbane Roar FC
Central Coast Mariners|센트럴코스트 매리너스|Central Coast|Central Coast Mariners FC
Sydney FC|시드니FC
Adelaide United|애들레이드 유나이티드|애들레이드|Adelaide United FC
Auckland FC|오클랜드FC|Auckland
Western Sydney Wanderers|웨스턴시드니 원더러스|Western Sydney|Western Sydney Wanderers FC
Wellington Phoenix|웰링턴 피닉스|Wellington Phoenix FC
Perth Glory|퍼스 글로리|Perth Glory FC
Newcastle Jets|뉴캐슬 제츠|Newcastle United Jets
Western United|웨스턴 유나이티드|Western United FC
FC Dallas|FC댈러스
FC Cincinnati|FC신시내티|신시내티|Cincinnati
Nashville SC|내슈빌SC|Nashville
New England Revolution|뉴잉글랜드 레벌루션|뉴잉글랜드 레볼루션|New England
Real Salt Lake|레알 솔트레이크|Real Salt Lake City
Vancouver Whitecaps|밴쿠버 화이트캡스FC|밴쿠버 화이트캡스|Vancouver Whitecaps FC
Charlotte FC|샬럿FC
Seattle Sounders|시애틀 사운더스FC|Seattle Sounders FC
Chicago Fire|시카고 파이어FC|Chicago Fire FC
Orlando City|올랜도 시티SC|Orlando City SC
Inter Miami|인터 마이애미CF|인터 마이애미|Inter Miami CF
Columbus Crew|콜럼버스 크루|Columbus Crew SC
Portland Timbers|포틀랜드 팀버스
Philadelphia Union|필라델피아 유니언
Atlanta United|애틀랜타 유나이티드|Atlanta United FC
Austin FC|오스틴FC
Colorado Rapids|콜로라도 래피즈
DC United|DC유나이티드|D.C. United
Houston Dynamo|휴스턴 다이너모|Houston Dynamo FC
LA Galaxy|LA갤럭시|Los Angeles Galaxy
LAFC|LAFC|Los Angeles FC
Minnesota United|미네소타 유나이티드|Minnesota United FC
CF Montréal|CF몽레알|몬트리올 임팩트|Montreal
New York City FC|뉴욕 시티FC|New York City
New York Red Bulls|뉴욕 레드불스
San Diego FC|샌디에이고FC
San Jose Earthquakes|새너제이 어스퀘이크스
Sporting Kansas City|스포팅 캔자스시티
St. Louis CITY SC|세인트루이스 시티SC|St Louis City
Toronto FC|토론토FC
FC Tokyo|FC도쿄
Machida Zelvia|FC마치다 젤비아|FC Machida Zelvia
V-Varen Nagasaki|V바렌 나가사키|V Varen Nagasaki
Kashima Antlers|가시마 앤틀러스
Kashiwa Reysol|가시와 레이솔
Kawasaki Frontale|가와사키 프론탈레
Gamba Osaka|감바 오사카
Kyoto Sanga|교토 상가FC|Kyoto Sanga FC
Nagoya Grampus|나고야 그램퍼스|Nagoya Grampus Eight
Tokyo Verdy|도쿄 베르디
Mito HollyHock|미토 홀리호크
Vissel Kobe|비셀 고베
Sanfrecce Hiroshima|산프레체 히로시마
Cerezo Osaka|세레소 오사카
Shimizu S-Pulse|시미즈 에스펄스
Avispa Fukuoka|아비스파 후쿠오카
Yokohama F. Marinos|요코하마 F마리노스|Yokohama Marinos
Urawa Red Diamonds|우라와 레드|Urawa Reds
JEF United Chiba|제프 유나이티드|JEF United|JEF United Ichihara Chiba
Fagiano Okayama|파지아노 오카야마
FC Imabari|FC이마바리
RB Omiya Ardija|RB오미야 아르디자|Omiya Ardija
Tochigi City|도치기 시티FC|Tochigi City FC
Tokushima Vortis|도쿠시마 보르티스
Montedio Yamagata|몬테디오 야마가타
Vanraure Hachinohe|반라우레 하치노헤FC|Vanraure Hachinohe FC
Ventforet Kofu|반포레 고후
Vegalta Sendai|베갈타 센다이
Blaublitz Akita|블라우블리츠 아키타
Sagan Tosu|사간 도스
Shonan Bellmare|쇼난 벨마레
Albirex Niigata|알비렉스 니가타
Oita Trinita|오이타 트리니타
Yokohama FC|요코하마FC
Iwaki FC|이와키FC
Jubilo Iwata|주빌로 이와타
Kataller Toyama|카탈레 도야마
Hokkaido Consadole Sapporo|콘사도레 삿포로|Consadole Sapporo
Tegevajaro Miyazaki|테게바자로 미야자키
Fujieda MYFC|후지에다 MYFC
FC Seoul|FC서울|서울FC
FC Anyang|FC안양|안양FC
Gangwon FC|강원FC|Gangwon
Gwangju FC|광주FC|Gwangju
Gimcheon Sangmu|김천상무 프로축구단|Gimcheon Sangmu FC|Gimcheon Sangmu Phoenix
Daejeon Hana Citizen|대전 하나시티즌|Daejeon Citizen|Daejeon Hana Citizen FC
Bucheon FC 1995|부천FC 1995|Bucheon FC
Ulsan HD|울산 HDFC|울산 현대|Ulsan HD FC|Ulsan Hyundai
Incheon United|인천 유나이티드|Incheon United FC
Jeonbuk Hyundai Motors|전북 현대모터스|전북 현대|Jeonbuk Motors|Jeonbuk Hyundai Motors FC
Jeju SK|제주 SKFC|제주 유나이티드|Jeju SK FC|Jeju United
Pohang Steelers|포항 스틸러스|Pohang Steelers FC
Gyeongnam FC|경남FC|Gyeongnam
Gimpo FC|김포FC
Gimhae FC 2008|김해FC 2008|Gimhae FC
Daegu FC|대구FC
Busan IPark|부산 아이파크|Busan I Park
Seoul E-Land|서울 이랜드|Seoul E-Land FC
Seongnam FC|성남FC
Suwon Samsung Bluewings|수원 삼성블루윙즈|수원 삼성|Suwon Bluewings
Suwon FC|수원FC
Ansan Greeners|안산 그리너스|Ansan Greeners FC
Yongin FC|용인FC
Jeonnam Dragons|전남 드래곤즈|Chunnam Dragons
Cheonan City|천안 시티FC|Cheonan City FC
Chungnam Asan|충남아산 프로축구단|Chungnam Asan FC
Chungbuk Cheongju|충북청주 프로축구단|Chungbuk Cheongju FC
Paju Frontier|파주 프런티어|Paju Frontier FC
Neftchi Fergana|네프치 페르가나|Neftchi FK
Al Hilal|알힐랄SFC|알 힐랄|Al Hilal SFC|Al-Hilal Saudi
BNK Sum|BNK 썸|Busan BNK Sum
KB Stars|KB 스타즈|Cheongju KB Stars|KB국민은행 스타즈
Samsung Life Blueminx|삼성생명 블루밍스|Yongin Samsung Life Blueminx
Shinhan Bank S-Birds|신한은행 에스버드|Incheon Shinhan Bank S-Birds
Woori Bank WooriWON|우리은행 우리WON|Asan Woori Bank WooriWON
Hana Bank|하나은행|Bucheon Hana Bank
IBK Altos|IBK기업은행 알토스|Hwaseong IBK Altos
SOOP Supers|SOOP 수퍼스|수퍼스
Red Sparks|정관장 레드스파크스|Daejeon JungKwanJang Red Sparks
High Pass|한국도로공사 하이패스|Gimcheon Korea Expressway Corporation Hi-Pass
Hillstate|현대건설 힐스테이트|Suwon Hyundai E&C Hillstate
Pink Spiders|흥국생명 핑크스파이더스|Incheon Heungkuk Life Pink Spiders
KB Insurance Stars|KB손해보험 스타즈|Uijeongbu KB Insurance Stars
OK Savings Bank|OK저축은행 읏맨|Ansan OK Financial Group Okman
Samsung Bluefangs|삼성화재 블루팡스|Daejeon Samsung Fire Bluefangs
Woori Card WooriWON|우리카드 우리WON|Seoul Woori Card WooriWON
KEPCO Vixtorm|한국전력 빅스톰|Suwon KEPCO Vixtorm
Hyundai Skywalkers|현대캐피탈 스카이워커스|Cheonan Hyundai Capital Skywalkers
Doosan Bears|두산 베어스
Hanwha Eagles|한화 이글스
Kia Tigers|KIA 타이거즈
Kiwoom Heroes|키움 히어로즈
KT Wiz|KT 위즈
LG Twins|LG 트윈스
Lotte Giants|롯데 자이언츠
NC Dinos|NC 다이노스
Samsung Lions|삼성 라이온즈
SSG Landers|SSG 랜더스
"""


@lru_cache(maxsize=4096)
def normalize(value):
    folded = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in folded if char.isalnum())


ALIASES = {}
DISPLAY_NAMES = {}
for line in ALIAS_ROWS.strip().splitlines():
    canonical, korean, *variants = line.split("|")
    key = normalize(canonical)
    DISPLAY_NAMES[key] = korean
    for value in (canonical, korean, *variants):
        alias = normalize(value)
        if alias in ALIASES and ALIASES[alias] != key:
            raise ValueError(f"Ambiguous team alias: {value}")
        ALIASES[alias] = key


def team_key(value):
    key = normalize(value or "")
    return ALIASES.get(key, key)


@lru_cache(maxsize=8192)
def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is not None:
            return result.astimezone(timezone.utc)
    except (ValueError, AttributeError):
        pass
    return None


def score_of(value):
    if isinstance(value, str) and re.fullmatch(r"\d+:\d+", value):
        return tuple(map(int, value.split(":")))
    if isinstance(value, (list, tuple)) and len(value) == 2:
        if all(type(point) is int and point >= 0 for point in value):
            return tuple(value)
    return None


def pair(event):
    return team_key(event.get("home")), team_key(event.get("away"))


def known_source(event):
    source = event.get("source")
    if isinstance(source, (list, tuple)) and len(source) == 2 and all(isinstance(item, str) for item in source):
        url = urlsplit(source[1])
        if url.scheme == "https" and url.hostname:
            return list(source)
    return None


def provenance(event):
    source = known_source(event)
    if source is None:
        return None
    return urlsplit(source[1]).hostname.removeprefix("www.")


def match_fixtures(fixtures, events):
    """Match each official fixture using league, both oriented teams and kickoff time."""
    pairs = defaultdict(list)
    for event in events:
        when = timestamp(event.get("start"))
        if when and event.get("id"):
            pairs[(event.get("league"), *pair(event))].append((when, event))

    mapped = {}
    for fixture in fixtures:
        when = timestamp(fixture.get("startsAt"))
        names = pair(fixture)
        if when is None or not all(names) or len(set(names)) != 2:
            continue
        official_score = score_of(fixture.get("result"))
        candidates = []
        for event_start, event in pairs.get((fixture.get("league"), *names), []):
            distance = abs(event_start - when)
            score = score_of(event.get("score")) if event.get("complete") else None
            if distance <= KICKOFF_TOLERANCE and (
                official_score is None or score is None or score == official_score
            ):
                candidates.append((distance, score, event))
        if not candidates:
            continue
        candidates.sort(key=lambda item: (item[0], official_score is not None and item[1] != official_score))
        nearest = candidates[0][0]
        tied = [item for item in candidates if item[0] == nearest]
        if len({score for _, score, _ in tied if score is not None}) > 1:
            continue
        mapped[fixture["number"]] = candidates[0][2]
    return mapped


def completed_history(fixture, event, events, sources, verified=()):
    """Use scored, completed matches from the same competition before kickoff."""
    start = timestamp(fixture.get("startsAt"))
    if start is None:
        return []
    league = fixture.get("league")
    team_names = pair(fixture)
    direct_source = provenance(event) if event else None
    direct_id = event.get("id") if event else None
    direct_pairs = pair(event) if event else team_names
    direct_ids = [event.get("home_id"), event.get("away_id")] if event else [None, None]
    known_ids = {str(uid): name for uid, name in zip(direct_ids, direct_pairs) if uid is not None}
    source_histories = defaultdict(list)
    for row in events:
        if row.get("league") != league or not row.get("complete"):
            continue
        day = timestamp(row.get("start"))
        score = score_of(row.get("score"))
        provider = provenance(row)
        if day is None or day >= start or score is None or provider is None:
            continue
        if row.get("dateOnly") and day.astimezone(KST).date() == start.astimezone(KST).date():
            continue
        if direct_id and provider == direct_source and row.get("id") == direct_id:
            continue
        home, away = pair(row)
        if provider == direct_source:
            home = known_ids.get(str(row.get("home_id")), home)
            away = known_ids.get(str(row.get("away_id")), away)
        if not home or not away or home == away:
            continue
        if (home, away) == team_names and start - day <= KICKOFF_TOLERANCE:
            continue
        source_histories[provider].append((day, home, away, score, row))

    # Prefer the source with broader verified pre-match coverage for both teams.
    def coverage(rows):
        counts = [
            min(10, len({(day, home, away) for day, home, away, *_ in rows if side in (home, away)}))
            for side in team_names
        ]
        return min(counts), sum(counts)

    best_rows = max(source_histories.values(), key=coverage, default=[])
    if direct_source in source_histories and coverage(source_histories[direct_source]) == coverage(best_rows):
        best_rows = source_histories[direct_source]
    by_match = defaultdict(list)
    for entry in best_rows:
        day, home, away, score, _ = entry
        by_match[(day, home, away)].append(entry)
    rows = []
    for same_match in by_match.values():
        if len({option[3] for option in same_match}) == 1:
            rows.append(same_match[0])
    # Club results include dates, so use them in place of the same fixture from a general feed.
    verified_rows = []
    for event in verified:
        day, score = timestamp(event["start"]), score_of(event["score"])
        home, away = pair(event)
        if (day and score and event["league"] == league and known_source(event)
                and day.astimezone(KST).date() < start.astimezone(KST).date()
                and (home in team_names or away in team_names)):
            verified_rows.append((day, home, away, score, event))
    rows = [row for row in rows if not any(
        row[1:3] == club_row[1:3] and abs(row[0] - club_row[0]) < timedelta(days=1)
        for club_row in verified_rows
    )] + verified_rows
    rows.sort(key=lambda row: row[0], reverse=True)
    if rows:
        sources.append(known_source(rows[0][-1]))
    return rows


def display_name(key, raw, display_by_key):
    return display_by_key.get(key, DISPLAY_NAMES.get(key, raw))


def team_matches(history, team, display_by_key):
    for day, home, away, score, row in history:
        if team == home:
            yield day, display_name(away, row["away"], display_by_key), "홈", *score, row
        elif team == away:
            yield day, display_name(home, row["home"], display_by_key), "원정", *reversed(score), row


def summarize(games):
    wins = sum(game[3] > game[4] for game in games)
    draws = sum(game[3] == game[4] for game in games)
    return {
        "played": len(games),
        "wins": wins,
        "draws": draws,
        "losses": len(games) - wins - draws,
        "for": sum(game[3] for game in games),
        "against": sum(game[4] for game in games),
    }


def short_record(stats):
    return f'{stats["wins"]}승 {stats["draws"]}무 {stats["losses"]}패'


def rest_labels(teams, start):
    # An interval between listed league games is not a verified rest period:
    # cups, trips, and training might be absent from these feeds.
    labels = []
    for name, games in teams:
        if not games or games[0][-1].get("dateOnly"):
            return []
        previous_start = games[0][0]
        gap = start - previous_start
        if gap > timedelta(days=45):
            return []
        hours = int(gap.total_seconds() // 3600)
        days, hours = divmod(hours, 24)
        interval = f"{days}일 {hours}시간" if days else f"{hours}시간"
        labels.append(f"{name} {interval}")
    return labels


def scoring_context(fixture, event, history, home, away, source):
    """Compare observed counts on a documented threshold and common date window."""
    sport = fixture.get("sport")
    if sport == "축구":
        threshold, criterion = 2.5, "두 팀 합계 2골 이하"
        criterion_source = None
    elif event and sport in ("농구", "야구", "배구"):
        threshold = event.get("total_line")
        criterion_source = known_source({"source": event.get("total_source")})
        if (type(threshold) not in (int, float) or not 0 < threshold < 1000
                or criterion_source is None or (sport == "배구" and not 2.5 <= threshold <= 5.5)):
            return None
        unit = "세트" if sport == "배구" else "점"
        criterion = f"두 팀 합계 {threshold:g}{unit} 미만"
    else:
        return None

    entries = {}
    for team in (home, away):
        games = [row for row in history if team in row[1:3]][:5]
        if not games:
            return None
        for row in games:
            entries[row[:3]] = row
    recent = list(entries.values())
    earliest, latest = min(row[0] for row in recent), max(row[0] for row in recent)
    league = [row for row in history if earliest <= row[0] <= latest]
    team_hits = sum(sum(row[3]) < threshold for row in recent)
    league_hits = sum(sum(row[3]) < threshold for row in league)
    team_rate, league_rate = team_hits / len(recent), league_hits / len(league)
    gap = team_rate - league_rate
    if len(recent) < 6 or len(league) < 18:
        title = "비교 표본이 적습니다"
    elif gap >= .15:
        title = "낮은 합계가 리그 평균보다 자주 나왔습니다"
    elif gap <= -.15:
        title = "낮은 합계가 리그 평균보다 드물었습니다"
    else:
        title = "낮은 합계 빈도가 리그 평균과 비슷했습니다"

    result = {
        "title": title,
        "value": f"{len(recent)}경기 중 {team_hits}경기",
        "text": (
            f"{criterion} 기준입니다. 두 팀의 최근 리그 경기에서 맞대결을 한 번만 세면 {team_rate:.0%}, "
            f"같은 기간 제공처 리그 기록은 {len(league)}경기 중 {league_hits}경기({league_rate:.0%})였습니다."
        ),
        "source": source,
        "date": f"{earliest.astimezone(KST):%Y-%m-%d}~{latest.astimezone(KST):%Y-%m-%d} · 한국 날짜",
    }
    if criterion_source is not None:
        result["criterionSource"] = criterion_source
        push = sum(sum(row[3]) == threshold for row in recent)
        if push:
            result["text"] += f"합계가 기준점과 같은 경기는 {push}경기였습니다."
    return result


def matchup_history(events, teams, before):
    rows = {}
    for event in events:
        when = timestamp(event.get("start"))
        score = score_of(event.get("score"))
        oriented = pair(event)
        if (not when or when >= before - timedelta(minutes=10) or when < before - timedelta(days=730)
                or not event.get("complete") or not score or set(oriented) != teams or not known_source(event)):
            continue
        key = next((key for key in rows if key[1:] == oriented and abs(key[0] - when) < timedelta(days=1)), None)
        if key is None:
            rows[(when, *oriented)] = (score, event)
        elif rows[key] is not None and rows[key][0] != score:
            rows[key] = None
    return [(*key, *value) for key,value in sorted(rows.items(), reverse=True) if value is not None][:5]


def analyze_fixture(fixture, event, events, verified=()):
    sources = []
    history = completed_history(fixture, event, events, sources, verified)
    if not history:
        return {}
    home, away = pair(fixture)
    display_by_key = {home: fixture["home"], away: fixture["away"]}
    teams = [(display, list(team_matches(history, key, display_by_key))) for key, display in display_by_key.items()]
    recent, records, team_stats = [], [], []
    for name, games in teams:
        if not games:
            continue
        recent.append([
            name,
            [[day.astimezone(KST).date().isoformat(), opposition, field, gf, ga] for day, opposition, field, gf, ga, _ in games[:5]],
            known_source(games[0][-1]),
        ])
        team_stats.append({
            "team": name,
            **summarize(games[:10]),
            "home": summarize([game for game in games if game[2] == "홈"][:5]),
            "away": summarize([game for game in games if game[2] == "원정"][:5]),
            "lastPlayed": games[0][0].isoformat(),
            "lastPlayedDateOnly": bool(games[0][-1].get("dateOnly")),
            "source": known_source(games[0][-1]),
        })
    if not recent:
        return {}

    head_to_head = matchup_history(events, {home, away}, timestamp(fixture["startsAt"]))
    if head_to_head:
        subject = fixture["home"]
        games = list(team_matches(head_to_head, home, display_by_key))
        scores = " · ".join(
            f"{day.astimezone(KST):%m/%d} {field} {gf}:{ga}"
            for day, _, field, gf, ga, _ in games
        )
        stats = summarize(games)
        records.append([
            f"맞대결 {stats['played']}경기 · {subject} {short_record(stats)}",
            f"한국 날짜 · {subject} 기준 점수 {scores}",
            known_source(games[0][-1]),
        ])

    rest = rest_labels(teams, timestamp(fixture.get("startsAt")))
    if rest:
        records.append(["직전 리그 경기부터 킥오프까지", " · ".join(rest) + ". 컵대회 일정은 집계에서 제외했습니다.", sources[0]])

    if fixture.get("sport") == "축구":
        conditional = []
        for day, home_key, away_key, total, row in history:
            half = score_of(row.get("half"))
            if half is not None and sum(half) == 2 and all(h <= f for h, f in zip(half,total)):
                conditional.append((home_key, away_key, sum(total) == 2, row))
        involved = [value for value in conditional if home in value[:2] or away in value[:2]]
        if involved:
            count = sum(value[2] for value in involved)
            whole = sum(value[2] for value in conditional)
            records.append([
                f"전반에 합계 두 골이 난 뒤 후반 무득점 {len(involved)}경기 중 {count}경기",
                f"두 팀이 치른 경기 중 전반 점수가 확인된 표본입니다. 같은 자료의 리그 전체는 {len(conditional)}경기 중 {whole}경기였습니다.",
                known_source(involved[0][-1]),
            ])

    result = {
        "recent": recent,
        "headToHead": [
            {"date": day.astimezone(KST).date().isoformat(),
             "home": display_name(row_home, row["home"], display_by_key),
             "away": display_name(row_away, row["away"], display_by_key),
             "score": list(score), "source": known_source(row)}
            for day, row_home, row_away, score, row in head_to_head
        ],
        "recentBasis": f"{fixture['league']} · 킥오프 전까지 제공처에 수록된 완료 경기 · 한국 날짜",
        "records": records,
        "teamStats": team_stats,
    }
    scoring = scoring_context(fixture, event, history, home, away, sources[0])
    if scoring is not None:
        result["scoring"] = scoring
    return result
