# 매치인덱스

베트맨 프로토 승부식 기준 경기 정보 보조 화면입니다. 2026년 11월 21일 한국 시간 기준의 선정 경기와 출처를 수동 검증해 담았습니다. 138회차 편성은 공개 보조 자료로 확인하고, 경기 정보는 구단·리그·언론과 대조합니다. 베트맨 실시간 발매 데이터는 연결되어 있지 않습니다.

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
