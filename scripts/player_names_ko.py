"""Korean NBA names for display. Player keys and source metadata stay unchanged."""

import re
from unicodedata import combining, normalize


def _key(name):
    # Providers differ on accents, dotted initials, apostrophes and hyphen spacing.
    text = "".join(char for char in normalize("NFKD", name.casefold()) if not combining(char))
    text = re.sub(r"[.'’]", "", text)
    return " ".join(text.replace("-", " ").split())


# Established Korean spellings and native pronunciation for recent roster additions.
_NAMES = """Adem Bona|아뎀 보나
AJ Dybantsa|에이제이 디반사
Alex Caruso|알렉스 카루소
Alperen Sengun|알페렌 센군
Amari Williams|아마리 윌리엄스
Anthony Davis|앤서니 데이비스
Anthony Edwards|앤서니 에드워즈
Ariel Hukporti|아리엘 후크포르티
Asa Newell|아사 뉴얼
Austin Reaves|오스틴 리브스
Ayo Dosunmu|아요 도순무
Bam Adebayo|뱀 아데바요
Ben Sheppard|벤 셰퍼드
Ben Simmons|벤 시몬스
Bennedict Mathurin|베네딕트 매서린
Bradley Beal|브래들리 빌
Brandon Ingram|브랜든 잉그램
Brandon Williams|브랜든 윌리엄스
Bruce Thornton|브루스 손턴
Bryce Hopkins|브라이스 홉킨스
Bryce McGowens|브라이스 맥고원스
Cade Cunningham|케이드 커닝햄
Caleb Wilson|케일럽 윌슨
Cam Whitmore|캠 휘트모어
Cameron Boozer|캐머런 부저
Cason Wallace|케이슨 월러스
Cedric Coward|세드릭 카워드
Chet Holmgren|쳇 홈그렌
Chris Youngblood|크리스 영블러드
CJ McCollum|시제이 맥컬럼
Clint Capela|클린트 카펠라
Collin Murray-Boyles|콜린 머리보일스
Cooper Flagg|쿠퍼 플래그
Dailyn Swain|데일린 스웨인
DaRon Holmes II|다론 홈스 2세
Darius Acuff Jr.|다리우스 에이컵 주니어
Darius Garland|다리우스 갈런드
Dean Wade|딘 웨이드
Dejounte Murray|디존테 머리
Deni Avdija|데니 아브디야
Dennis Schroder|데니스 슈뢰더
Dereck Lively II|데릭 라이블리 2세
Derrick White|데릭 화이트
Devin Booker|데빈 부커
Dillon Mitchell|딜런 미첼
Donovan Clingan|도노반 클링언
Donovan Mitchell|도너번 미첼
Donte DiVincenzo|단테 디빈첸조
Draymond Green|드레이먼드 그린
Drew Timme|드루 팀미
Duncan Robinson|던컨 로빈슨
Duop Reath|두옵 리스
Dylan Harper|딜런 하퍼
Ebuka Okorie|이부카 오코리
Ernest Udeh Jr.|어니스트 우데 주니어
Evan Mobley|에번 모블리
Felix Okpara|펠릭스 오크파라
Franz Wagner|프란츠 바그너
GG Jackson|지지 잭슨
Giannis Antetokounmpo|야니스 아데토쿤보
Grant Nelson|그랜트 넬슨
Grant Williams|그랜트 윌리엄스
Grayson Allen|그레이슨 앨런
Harrison Ingram|해리슨 잉그램
Henri Veesaar|헨리 베사르
Izaiyah Nelson|아이자이아 넬슨
Jaden Bradley|제이든 브래들리
Jaden McDaniels|제이든 맥대니얼스
Ja Morant|자 모란트
Ja'Kobi Gillespie|자코비 길레스피
Jaime Jaquez Jr.|하이메 하케스 주니어
Jalen Brunson|제일런 브런슨
Jalen Duren|제일런 듀런
Jalen Johnson|제일런 존슨
Jalen Pickett|제일런 피켓
Jalen Smith|제일런 스미스
Jamal Murray|저말 머리
Jamir Watkins|자미르 왓킨스
Jaren Jackson Jr.|자렌 잭슨 주니어
Javon Small|제이본 스몰
Jayden Quaintance|제이든 퀘인턴스
Jaylen Brown|제일런 브라운
Jaylen Clark|제일런 클라크
Jaylon Tyson|제일런 타이슨
Jayson Tatum|제이슨 테이텀
Jimmy Butler|지미 버틀러
Jimmy Butler III|지미 버틀러 3세
Johnny Furphy|조니 퍼피
Jonas Aidoo|조나스 아이두
Jonathan Isaac|조너선 아이작
Jonathan Mogbo|조너선 모그보
Jordan Clarkson|조던 클라크슨
Jordan Miller|조던 밀러
Julian Phillips|줄리언 필립스
Julius Randle|줄리어스 랜들
Justin Champagnie|저스틴 샴페니
Kam Jones|캠 존스
Karl-Anthony Towns|칼앤서니 타운스
Kasparas Jakucionis|카스파라스 야쿠치오니스
Kawhi Leonard|커와이 레너드
Kevin Durant|케빈 듀랜트
Keyonte George|키욘테 조지
Kyle Kuzma|카일 쿠즈마
LeBron James|르브론 제임스
Luka Doncic|루카 돈치치
Mark Williams|마크 윌리엄스
Maxime Raynaud|막심 레노
Myles Turner|마일스 터너
Naz Reid|나즈 리드
Nikola Jokic|니콜라 요키치
Noah Penda|노아 펜다
Norman Powell|노먼 파월
OG Anunoby|오지 아누노비
Ousmane Dieng|우스만 디엥
Pascal Siakam|파스칼 시아캄
Richie Saunders|리치 손더스
RJ Barrett|알제이 배럿
Scotty Pippen Jr.|스코티 피펜 주니어
Sergio de Larrea|세르히오 데 라레아
Shaedon Sharpe|셰이든 샤프
Shai Gilgeous-Alexander|샤이 길저스알렉산더
Stephen Curry|스테픈 커리
Tarik Biberovic|타리크 비베로비치
Tyrese Haliburton|타이리스 핼리버튼
Tyrese Maxey|타이리스 맥시
Victor Wembanyama|빅터 웸반야마
Yaxel Lendeborg|약셀 렌더보그
Zion Williamson|자이언 윌리엄슨
Bogoljub Markovic|보골류브 마르코비치"""
_DISPLAY = {_key(english): korean for english, korean in (line.split("|") for line in _NAMES.splitlines())}
_SUFFIXES = {"jr": "주니어", "sr": "시니어", "ii": "2세", "iii": "3세", "iv": "4세"}
_PARTS = {}
for english, korean in _DISPLAY.items():
    original_parts, localized_parts = english.split(), korean.split()
    if len(original_parts) == len(localized_parts):
        for index, (original, localized) in enumerate(zip(original_parts, localized_parts)):
            if original not in _SUFFIXES:
                part = ("given" if index == 0 else "surname", original)
                _PARTS.setdefault(part, set()).add(localized)


def player_name_ko(name):
    """Prefer a roster spelling; reuse known name components only when unambiguous."""
    key = _key(name)
    if key in _DISPLAY:
        return _DISPLAY[key]
    tokens = key.split()
    if not 2 <= len(tokens) <= 5 or not all(re.fullmatch(r"[a-z]+", token) for token in tokens):
        return name
    suffix = _SUFFIXES.get(tokens[-1]) if len(tokens) >= 3 else None
    if suffix:
        tokens.pop()
    parts = []
    for index, token in enumerate(tokens):
        variants = _PARTS.get(("given" if index == 0 else "surname", token))
        if not variants or len(variants) != 1:
            return name
        parts.append(next(iter(variants)))
    if suffix:
        parts.append(suffix)
    return " ".join(parts)
