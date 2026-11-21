# 매치인덱스

베트맨 프로토 승부식 기준의 한국어 경기 분석 데모입니다. 공식 안내에 명시된 축구, 야구, 농구, 배구를 제공합니다. 경기, 선수 변수, 배당 및 예시 결과 확률은 가상입니다. 실시간 회차나 경기 정보를 연동하지 않습니다.

- 공식 종목 및 경기 규정: https://m.betman.co.kr/main/mainPage/gameguide/proto.do
- 데이터 및 종목별 지표: `public/data.js`
- 로컬 실행: `python server.py` 후 http://localhost:8000
- Render Python 웹 서비스: 빌드 `python -m py_compile server.py`, 시작 `python server.py`. 추가 의존성은 없습니다.
