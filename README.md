# 매치인덱스

베트맨 프로토 승부식의 공개 경기표를 시간순으로 보여주는 경기 정보 보조 화면입니다. 경기표는 Render의 공개 읽기 API를 통해 1분 간격으로 확인하고, 구단·리그 기사에서 정리한 선수와 팀의 상세 브리핑은 확인 시각을 기준으로 게시합니다.

- 데이터: `public/data.js` (경기, 출처, 확인 일자)
- 상세 주소: `?match=man-city-fulham`
- 미니 주소: `?match=man-city-fulham&view=mini`
- 미니 오버레이는 지원 브라우저의 Document Picture-in-Picture를 사용하며, 일반 미니 창으로 대체할 수 있습니다.
- 로컬 실행: `python server.py` 후 http://localhost:8000
- Render 정적 사이트 게시 폴더: `public`

## Neon에서 브리핑 게시

Neon 프로젝트 `matchindex-proto`의 `matchindex` 데이터베이스에 날짜별로 공개 브리핑과 출처를 보관합니다. `development`에서 변경을 확인한 뒤 `main`에 반영합니다. 공개 웹은 마지막으로 게시한 스냅샷을 제공하며, DB 수정은 다음 게시 때 반영됩니다.

운영 DB를 가리키는 접속 문자열을 환경 변수에 둔 편집 환경에서 다음 명령으로 생성하세요. 접속 문자열은 Git과 공개 웹에 포함하지 않습니다.

```sh
psql "$DATABASE_URL" -XAt -v ON_ERROR_STOP=1 -f db/export_briefings.sql -o public/data.js.next && test -s public/data.js.next && mv public/data.js.next public/data.js
```

생성된 브리핑을 검토하고 `main`에 커밋하면 Render가 게시합니다. 이 내보내기는 공개가 승인된 기사 요약과 경기 정보에 사용합니다.

## 징크스 검증과 해외 시장 자료

징크스 사례와 해외 기사에 공개된 배당 시점은 Neon의 `research_snapshot`에 저장합니다. 개발 브랜치에서 확인한 데이터를 운영 브랜치에 반영하고 `db/export_research.sql`을 실행해 `public/research.js`로 게시합니다. 기사 인용 배당은 게시 당시의 자료를 보관합니다.

EPL 조건부 집계는 [OpenFootball의 공개 도메인 2025/26 EPL JSON](https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/en.1.json)을 사용합니다. 시즌 파일을 내려받아 `python scripts/aggregate_epl_patterns.py en.1.json`으로 집계를 재현할 수 있습니다. 원본 SHA-256은 `d6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1`입니다.

## 과거 경기 이력

`historical_football_season`에 시즌별 출처와 파일 SHA-256을 저장하고, `historical_football_match`에 홈·원정 팀과 경기 날짜, 전반·최종 점수를 저장합니다. 2021/22~2025/26 EPL 시즌 파일은 [OpenFootball](https://github.com/openfootball/football.json)의 공개 도메인 자료입니다.

```sh
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/10_historical_football.sql
python scripts/import_openfootball_epl.py | psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1
```

## 경기표 자동 갱신

- `scripts/import_betman_round.py 260138`은 베트맨 공개 조회로 138회차 본경기와 일반 배당을 내려받습니다. 핸디캡 및 전반 유형은 목록에서 별도로 세지 않습니다.
- Neon `proto_round_snapshot`의 게시본은 `db/export_proto_round.sql`로 내보내 `public/fixtures.js`를 생성합니다. 공식 조회를 사용할 수 없을 때 게시본을 먼저 표시합니다.
- Render 정적 사이트는 `matchindex-round-api`에서 경기표를 가져옵니다. `server.py`의 `/api/round`는 공식 경기표 읽기와 공유 캐시를 제공하며, `/healthz`로 서버 기동을 확인합니다.


### 경기 상세 정보

경기 분석표에서 `상세 정보`를 열면, 확인 자료가 있는 항목의 카드를 볼 수 있습니다. 경기별 자료는 `fixture_context_snapshot`에 베트맨 회차·경기번호와 함께 저장하고 `db/export_fixture_context.sql`로 게시합니다. 해외 배당은 출처가 공개한 시점의 값입니다.

EPL 최근 경기와 맞대결은 Neon의 경기 이력에서 `db/export_epl_history.sql`로 만든 자료를 카드가 열릴 때 읽습니다. 진행 중인 시즌과 과거 시즌의 범위는 카드에 표시됩니다. 경기 이력은 영국 현지 날짜를 기준으로 대상 경기 전날까지 집계합니다.
