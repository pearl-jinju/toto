export const research = {
    "cases": [
        {
            "limit": "같은 시즌 전체의 언더 2.5는 45.0% · 171/380였습니다. ‘한 팀이 전반에 정확히 2골’로 조건을 바꾸면 언더 2.5는 12.5% · 10/80였습니다. 배당과 수익은 집계하지 않았습니다. 2021/22~2025/26 5시즌에서도 같은 조건 440경기 중 78경기(17.7%)가 언더 2.5였습니다.",
            "links": [
                [
                    "OpenFootball · 2025/26 EPL 경기 원본 (CC0)",
                    "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/en.1.json"
                ],
                [
                    "OpenFootball · EPL 5시즌 원본 목록 (CC0)",
                    "https://github.com/openfootball/football.json"
                ]
            ],
            "scope": "2025/26 프리미어리그 380경기 · 자체 집계",
            "sport": "축구",
            "title": "전반 2골이면 언더가 자주 나온다?",
            "answer": "양 팀 합계 2골이라면, 기준점에 따라 결과가 크게 달랐습니다.",
            "method": "전반 종료 시 양 팀이 합쳐 정확히 2골을 넣은 85경기. 언더 2.5는 후반에 추가 골이 전혀 없는 경우입니다.",
            "figures": [
                [
                    "언더 2.5",
                    "20.0% · 17/85"
                ],
                [
                    "언더 3.5",
                    "57.6% · 49/85"
                ],
                [
                    "언더 4.5",
                    "82.4% · 70/85"
                ]
            ]
        },
        {
            "limit": "2골 차 리드 57경기 중 4경기는 무승부, 1경기는 역전패였습니다. 상대 전력과 퇴장 등은 보정하지 않은 기록입니다. 5시즌 합계에서도 1골 차 리드 팀은 529/821(64.4%), 2골 차 리드 팀은 239/261(91.6%)가 이겼습니다.",
            "links": [
                [
                    "OpenFootball · 2025/26 EPL 경기 원본 (CC0)",
                    "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/en.1.json"
                ]
            ],
            "scope": "2025/26 프리미어리그 380경기 · 자체 집계",
            "sport": "축구",
            "title": "두 골 차 리드가 더 위험하다?",
            "answer": "전반 두 골 차 리드를 잡은 팀이 한 골 차로 앞선 팀보다 더 자주 이겼습니다.",
            "method": "전반 종료 시 홈·원정 구분 없이 앞선 팀의 최종 결과를 집계했습니다. 2–0뿐 아니라 3–1처럼 전반 점수 차가 정확히 2골인 경우를 포함합니다.",
            "figures": [
                [
                    "1골 차 리드 팀 승리",
                    "65.3% · 111/170"
                ],
                [
                    "2골 차 리드 팀 승리",
                    "91.2% · 52/57"
                ]
            ]
        },
        {
            "limit": "후반 득점 팀이나 최종 득점 수를 예측하는 통계는 아닙니다. 5시즌 합계에서는 전반 0–0 501경기 중 402경기(80.2%)에서 후반에 골이 나왔습니다.",
            "links": [
                [
                    "OpenFootball · 2025/26 EPL 경기 원본 (CC0)",
                    "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/en.1.json"
                ]
            ],
            "scope": "2025/26 프리미어리그 380경기 · 자체 집계",
            "sport": "축구",
            "title": "전반이 0–0이면 그대로 끝난다?",
            "answer": "전반 무득점 경기 네 번 중 세 번은 후반에 골이 나왔습니다.",
            "method": "전반 0–0이었던 경기만 골라 최종 점수를 비교했습니다.",
            "figures": [
                [
                    "후반 1골 이상",
                    "75.0% · 81/108"
                ],
                [
                    "최종 0–0",
                    "25.0% · 27/108"
                ]
            ]
        },
        {
            "limit": "투구 단위 파울 건수입니다. 구장별 펜스를 실제 넘었는지는 확인하지 못하는 대체 지표입니다.",
            "links": [
                [
                    "독립 분석 · 원문",
                    "https://note.com/baseball_labo/n/ne15d6e29a5f9?hl=ko"
                ],
                [
                    "MLB · Statcast 데이터 설명",
                    "https://baseballsavant.mlb.com/csv-docs"
                ]
            ],
            "scope": "2022~2025 MLB 정규시즌 · Statcast 독립 분석",
            "sport": "야구",
            "title": "홈런성 파울을 치면 삼진을 당한다?",
            "answer": "볼·스트라이크 수를 맞춰 비교하자, 큰 파울 뒤 삼진이 뚜렷하게 늘지 않았습니다.",
            "method": "추정 비거리가 확인된 파울 439,599건 중 타구 속도 95mph 이상, 발사각 8~32도, 추정 거리 300피트 이상인 6,453건을 큰 파울로 정의했습니다. 다음 공에서 바로 삼진은 큰 파울 11.7%, 일반 파울 12.3%였습니다.",
            "figures": [
                [
                    "큰 파울 뒤 타석 삼진",
                    "33.5%"
                ],
                [
                    "일반 파울 뒤 타석 삼진",
                    "33.5%"
                ]
            ]
        },
        {
            "limit": "투수·타자 수준, 좌우 조합 등을 고려한 별도 연구에서는 세 번째 대결에 들어가는 순간 성적이 급격히 떨어진다는 근거가 약했습니다. 투구 수와 구속·제구 변화도 함께 보세요.",
            "links": [
                [
                    "MLB · 타순 순회별 공식 집계",
                    "https://www.mlb.com/glossary/miscellaneous/third-time-through-the-order-penalty"
                ],
                [
                    "Brill 외 · 보정 분석",
                    "https://arxiv.org/abs/2210.06724"
                ]
            ],
            "scope": "2016~2025 MLB · 공식 집계와 후속 연구",
            "sport": "야구",
            "title": "타자가 선발 투수를 세 번째 만나면 유리하다?",
            "answer": "리그 평균은 타자가 같은 선발을 다시 볼수록 높아졌습니다.",
            "method": "OPS는 출루율과 장타율을 더한 값입니다. MLB가 10년간 선발 투수 상대 타석을 타순 순회별로 집계했습니다.",
            "figures": [
                [
                    "첫 번째 대결 · 타자 OPS",
                    "0.713"
                ],
                [
                    "두 번째 대결",
                    "0.747"
                ],
                [
                    "세 번째 대결",
                    "0.780"
                ]
            ]
        },
        {
            "limit": "특정 선수가 연속 득점하더라도 다음 슛의 위치와 수비 압박이 달라질 수 있습니다. 3점슛 대회처럼 수비가 없는 환경의 연구와도 구분해야 합니다.",
            "links": [
                [
                    "Pelechrinis·Winston · 실제 NBA 경기 연구",
                    "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0261890"
                ],
                [
                    "Miller·Sanjurjo · 3점슛 대회 연구",
                    "https://www.sciencedirect.com/science/article/pii/S0014292121001240"
                ]
            ],
            "scope": "2013/14·2014/15 NBA · 시즌별 약 20만 슛",
            "sport": "농구",
            "title": "슛을 연속으로 넣으면 다음 슛도 잘 들어간다?",
            "answer": "일부 선수에게는 연속 성공 효과가 보였지만, 리그 평균에서는 나타나지 않았습니다.",
            "method": "연구는 슛 거리, 가장 가까운 수비수와의 거리, 드리블 수 등 슛 난도를 고려했습니다."
        },
        {
            "limit": "의무 휴식과 감독의 자발적 타임아웃에는 다른 조건이 작용합니다. 이후 교체나 공격 전술이 실제로 바뀌었는지 보세요.",
            "links": [
                [
                    "Weimer 외 · NBA TV 타임아웃 연구",
                    "https://journals.sagepub.com/doi/10.3233/JSA-220592"
                ],
                [
                    "Assis 외 · 감독 타임아웃 분석",
                    "https://arxiv.org/abs/2009.06750"
                ]
            ],
            "scope": "2004/05~2016/17 NBA 13시즌 · TV 타임아웃 연구",
            "sport": "농구",
            "title": "상대가 연속 득점하면 작전타임이 흐름을 끊는다?",
            "answer": "TV 타임아웃 연구에서는 득점 감소가 관측됐고, 감독이 부른 타임아웃 연구는 결과가 엇갈렸습니다.",
            "method": "의무 TV 타임아웃 뒤 연속 득점 중이던 팀의 다음 3분 득점을 비교했습니다.",
            "figures": [
                [
                    "연구상 이후 3분 득점 변화",
                    "약 −11%"
                ]
            ]
        },
        {
            "limit": "첫 세트 승리는 경기 승리에 필요한 3세트 중 하나입니다. 팀 전력과 별개의 기세 효과는 이 수치만으로 분리하기 어렵습니다.",
            "links": [
                [
                    "VolleyBTN · NCAA 2024 시즌 독립 집계",
                    "https://volleybtn.com/2024/11/29/how-common-are-reverse-sweeps-in-college-volleyball/"
                ]
            ],
            "scope": "2024년 NCAA 여자배구 D1·D3 10,680경기 · 외부 집계",
            "sport": "배구",
            "title": "첫 세트를 이기면 흐름까지 가져간다?",
            "answer": "첫 세트를 이긴 팀은 자주 이겼고, 세트가 1–1로 맞춰진 뒤에는 차이가 거의 없었습니다.",
            "method": "가을 2024 시즌 D1·D3 경기 결과를 직접 집계한 외부 분석입니다. 1–1 표본에서는 양 팀 중 누가 첫 세트를 이겼는지만 비교했습니다.",
            "figures": [
                [
                    "첫 세트를 이긴 팀의 승률",
                    "81.2%"
                ],
                [
                    "1–1 경기에서 첫 세트 승자 승률",
                    "50.4%"
                ]
            ]
        },
        {
            "limit": "NCAA 여자배구 표본입니다. V리그의 팀별 실제 확률과는 자료 범위가 다릅니다.",
            "links": [
                [
                    "VolleyBTN · NCAA 2024 시즌 독립 집계",
                    "https://volleybtn.com/2024/11/29/how-common-are-reverse-sweeps-in-college-volleyball/"
                ]
            ],
            "scope": "2024년 NCAA 여자배구 D1·D3 10,680경기 · 외부 집계",
            "sport": "배구",
            "title": "세트 0–2면 역전은 거의 없다?",
            "answer": "0–2에서 뒤집은 경우는 약 4.5%였습니다.",
            "method": "첫 2세트를 모두 내준 뒤 3~5세트를 연속으로 따낸 경우입니다. 4.5%는 첫 두 세트가 같은 팀에 돌아간 경기만 분모로 사용합니다.",
            "figures": [
                [
                    "0–2로 뒤진 팀의 최종 승리",
                    "4.5%"
                ],
                [
                    "전체 경기 중 0–2 역전",
                    "3.0%"
                ]
            ]
        }
    ],
    "markets": {
        "hawks-hornets": {
            "note": "양 팀 점수를 더하면 208점으로, 당시 공개 기준보다 10.5점 낮았습니다.",
            "links": [
                [
                    "BetMGM · 경기 전 농구 프리뷰",
                    "https://sports.betmgm.com/en/blog/nba/hornets-hawks-prediction-odds-lines-picks-nba-nov-20-jaa/"
                ],
                [
                    "NBA · 공식 경기 기록",
                    "https://www.nba.com/game/cha-vs-atl-0022600043"
                ]
            ],
            "scope": "11월 20일 현지 오전 게시 자료 · BetMGM",
            "figures": [
                [
                    "경기 총득점 기준",
                    "218.5점"
                ],
                [
                    "공식 최종 합계",
                    "208점"
                ]
            ]
        },
        "man-city-fulham": {
            "note": "언더 3.5는 정규시간 합계 3골 이하입니다. 해외 기사에 실린 시점의 수치입니다.",
            "links": [
                [
                    "Sports Betting Dime · BetMGM·theScore Bet 인용",
                    "https://www.sportsbettingdime.com/news/soccer/epl-picks-saturday-nov-21-2026/"
                ]
            ],
            "scope": "11월 21일 18:45 KST 게시 자료 · BetMGM·theScore Bet 인용",
            "figures": [
                [
                    "총득점 기준",
                    "3.5골"
                ],
                [
                    "오버 / 언더 배당",
                    "2.15 / 1.69"
                ]
            ]
        },
        "newcastle-arsenal": {
            "note": "언더 2.5는 정규시간 합계 2골 이하입니다. 해외 기사에 실린 시점의 수치입니다.",
            "links": [
                [
                    "Sports Betting Dime · BetMGM·theScore Bet 인용",
                    "https://www.sportsbettingdime.com/news/soccer/epl-picks-saturday-nov-21-2026/"
                ]
            ],
            "scope": "11월 21일 18:45 KST 게시 자료 · BetMGM·theScore Bet 인용",
            "figures": [
                [
                    "총득점 기준",
                    "2.5골"
                ],
                [
                    "오버 / 언더 배당",
                    "1.68 / 2.05"
                ]
            ]
        }
    },
    "numbers": {
        "samsung-ok": 4818,
        "hawks-hornets": 4702,
        "man-city-fulham": 4894,
        "newcastle-arsenal": 5025
    },
    "roundLink": [
        "138회차 경기번호·편성 참고",
        "https://pickreview.kr/round/260138"
    ],
    "marketSources": [
        [
            "Betfair · 과거 시세 데이터 범위",
            "https://betfair-datascientists.github.io/data/usingHistoricDataSite/"
        ],
        [
            "Pinnacle · 배당 마진 설명",
            "https://support.pinnacle.com/hc/en-us/articles/42376048557073-What-is-a-betting-margin"
        ],
        [
            "bet365 · 축구 정산 규칙",
            "https://help.bet365.com/s/en-ch/sportsrules/soccer/result-event-half-time"
        ],
        [
            "DraftKings · 축구 정산 규칙",
            "https://support.draftkings.com/dk/en-us/how-are-soccer-bets-settled?id=kb_article_view&sysparm_article=KB0010834"
        ]
    ]
};
