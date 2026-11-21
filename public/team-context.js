import { sourceLink as link } from "./source-links.js";
import { fixtureHistoryHref } from "./history-report.js";
import { fixtureContext } from "./fixture-context.js";
import { sources } from "./data.js";
import { automaticCards, renderAutomaticFactors, renderOutlook, weatherFacts } from "./auto-context.js";
import { curatedWeatherVisual, mascotArt, weatherHint, weatherPanel } from "./match-visuals.js";

const aliases = {
  "맨체스터시티":"Manchester City FC", "맨체스터유나이티드":"Manchester United FC",
  "풀럼":"Fulham FC", "뉴캐슬유나이티드":"Newcastle United FC", "아스널":"Arsenal FC",
  "애스턴빌라":"Aston Villa FC", "선덜랜드":"Sunderland AFC", "afc본머스":"AFC Bournemouth",
  "노팅엄포리스트":"Nottingham Forest FC", "첼시":"Chelsea FC", "리즈유나이티드":"Leeds United FC",
  "코번트리시티":"Coventry City FC", "크리스털팰리스":"Crystal Palace FC",
  "토트넘홋스퍼":"Tottenham Hotspur FC", "입스위치타운":"Ipswich Town FC",
  "헐시티":"Hull City AFC", "브라이턴&호브앨비언":"Brighton & Hove Albion FC", "리버풀":"Liverpool FC",
  "브렌트퍼드":"Brentford FC", "에버턴":"Everton FC", "울버햄튼":"Wolverhampton Wanderers FC",
  "울버햄튼원더러스":"Wolverhampton Wanderers FC", "웨스트햄유나이티드":"West Ham United FC",
  "레스터시티":"Leicester City FC", "번리":"Burnley FC", "사우샘프턴":"Southampton FC"
};
const venueAliases = {"대구im뱅크park":"im뱅크파크","장충체육관":"서울장충체육관"};
const byEnglish = Object.fromEntries(Object.entries(aliases).map(([k,v]) => [v,k]));
const extraNames = {"Brighton & Hove Albion FC":"브라이턴","AFC Bournemouth":"본머스","Manchester City FC":"맨시티",
 "Manchester United FC":"맨유","Newcastle United FC":"뉴캐슬","Tottenham Hotspur FC":"토트넘","Nottingham Forest FC":"노팅엄",
 "Crystal Palace FC":"크리스털 팰리스","Aston Villa FC":"애스턴 빌라","Coventry City FC":"코번트리"};
let historyPromise;

function key(value) {
  return String(value ?? "").toLowerCase().normalize("NFC").replace(/\s+/g, "");
}

function escape(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function card(id, title, icon, hint, body, opened) {
  return `<details class="context-card" data-context-card="${id}" data-keep-open="${id}"${opened.has(id) ? " open" : ""}>
    <summary><span class="context-icon${id === "weather" ? " context-icon-weather" : ""}" aria-hidden="true">${id === "weather" ? mascotArt("standing",true) : icon}</span><span><strong>${title}</strong><small>${escape(hint)}</small></span><span class="context-plus" aria-hidden="true"></span></summary>
    <div class="context-body">${body}</div>
  </details>`;
}

function resultWord(difference) {
  return difference > 0 ? "승" : difference < 0 ? "패" : "무";
}

function counts(games) {
  const won = games.filter(game => game[3] > game[4]).length;
  const drew = games.filter(game => game[3] === game[4]).length;
  return [won, drew, games.length - won - drew];
}

function resultRun(games) {
  return `<span class="form-run" aria-label="최신 경기부터 순서대로">${games.map(game => {
    const result = resultWord(game[3] - game[4]);
    return `<b class="result-${{"승":"win","무":"draw","패":"loss"}[result]}">${result}</b>`;
  }).join("")}</span>`;
}

function recentTeams(teams, basis, sport = "축구") {
  return `<p class="context-basis">${escape(basis)} · 최신 경기부터</p>
    <div class="context-grid-two">${teams.map(([name, games, source]) => {
      const [w,d,l] = counts(games);
      const scored = games.reduce((sum, r) => sum+r[3],0);
      const allowed = games.reduce((sum, r) => sum+r[4],0);
      return `<section class="context-stat">
        <h4>${escape(name)}</h4>${resultRun(games)}
        <p class="context-number">${w}승 ${d ? d+"무 " : ""}${l}패</p>
        <p class="context-basis">${games.length}경기 · ${sport === "배구" ? `${scored}세트 획득 · ${allowed}세트 허용` : `${scored}득점 · ${allowed}실점`}</p>
        <details class="context-evidence"><summary>날짜별 결과</summary>
          <ol>${games.map(([day, opp, venue, gf, ga]) => `<li><time>${escape(day)}</time><span>${escape(opp)} <small>${escape(venue)}</small></span><strong>${gf} : ${ga}</strong></li>`).join("")}</ol>
          ${link(source)}
        </details>
      </section>`;
    }).join("")}</div>`;
}

function genericItems(rows, labels) {
  return rows.map(([first, second, third, last, source]) => {
    const [title, basis, value, body, ref] = labels === "player"
      ? [first, second, third, last, source]
      : [second, first, "", third, last];
    return `<section class="context-item">
      <p class="context-basis">${escape(basis)}</p><h4>${escape(title)}</h4>
      ${value ? `<p class="context-number">${escape(value)}</p>` : ""}
      <p>${escape(body)}</p>${link(ref)}
    </section>`;
  }).join("");
}

function decimal(american) {
  return (american < 0 ? 1 - 100/american : 1 + american/100).toFixed(2);
}

const blockedOddsArticle = "https://www.fanduel.com/research/nba-predictions-odds-11-21-2026";
const oddsComparisons = {
  "5049": [
    "BetMGM · 같은 경기 배당 비교",
    "https://sports.betmgm.com/en/blog/nba/bucks-76ers-prediction-odds-lines-picks-nba-nov-21-jaa/"
  ],
  "5103": [
    "Action Network · 같은 경기 배당 비교",
    "https://www.actionnetwork.com/nba/portland-trail-blazers-vs-new-york-knicks-prediction-pick-nba-odds-saturday-november-21"
  ],
  "5107": [
    "BetMGM · 같은 경기 배당 비교",
    "https://sports.betmgm.com/en/blog/nba/clippers-mavericks-prediction-odds-lines-picks-nba-nov-21-jaa/"
  ],
  "5111": [
    "BetMGM · 같은 경기 배당 비교",
    "https://sports.betmgm.com/en/blog/nba/grizzlies-timberwolves-player-prop-bets-picks-nba-nov-21-jaa/"
  ],
  "5115": [
    "BetMGM · 같은 경기 배당 비교",
    "https://sports.betmgm.com/en/blog/nba/pelicans-spurs-player-prop-bets-picks-nba-nov-21-jaa/"
  ],
  "5123": [
    "BetMGM · 같은 경기 배당 비교",
    "https://sports.betmgm.com/en/blog/nba/celtics-kings-player-prop-bets-picks-nba-nov-21-jaa/"
  ]
};

function oddsSource(source, date, values, match, officialSource) {
  if (source?.[1] !== blockedOddsArticle) return link(source);
  const american = values.map((odd,i) => odd == null ? "" : `${["홈승","무승부","원정승"][i]} ${odd > 0 ? "+" : ""}${odd}`).filter(Boolean).join(" · ");
  return `<details class="context-evidence odds-source-details">
    <summary>FanDuel 출처 자료</summary>
    <p>${escape(source[0])} · ${escape(date)}</p>
    <p>당시 미국식 배당 ${escape(american)}</p>
    <p class="context-basis">FanDuel 원문 접속 제한 · 아래 비교 자료의 배당은 게시 시점에 따라 다를 수 있습니다.</p>
    ${link(oddsComparisons[match.number])}${link(["베트맨 · 공식 경기표",officialSource])}
  </details>`;
}

function overseas(lines, match, officialSource) {
  const local = match.odds;
  return `${lines.map(([name, date, values, total, source]) => `<section class="context-item">
    <h4>${escape(name)}</h4><p class="context-basis">${escape(date)} · 소수 배당</p>
    <dl class="context-values">${values.map((odd, index) => odd == null ? "" :
      `<div><dt>${["홈승","무승부","원정승"][index]}</dt><dd>${decimal(odd)}</dd></div>`).join("")}</dl>
    <p>${escape(total)}</p>${oddsSource(source,date,values,match,officialSource)}
  </section>`).join("")}
  ${local?.some(odd => odd != null) ? `<p class="context-basis">베트맨 일반 배당 · 홈 ${local[0]?.toFixed(2) ?? "—"} · 무 ${local[1]?.toFixed(2) ?? "—"} · 원정 ${local[2]?.toFixed(2) ?? "—"}</p>` : ""}`;
}

function stadium(venue, onSite) {
  const list = values => `<ul class="context-chips">${values.map(value => `<li>${escape(value)}</li>`).join("")}</ul>`;
  return `${venue ? `<h4>${escape(venue.name)}</h4>${list(venue.facts)}<p>${escape(venue.note)}</p>${venue.sources.map(link).join("")}` : ""}
    ${onSite ? `<div class="context-item"><h4>경기 당일 관측</h4>${list(onSite.facts)}${link(onSite.source)}</div>` : ""}`;
}

export function teamContextPanels(match, round, {detail, editorial, auto, opened = new Set()} = {}) {
  if (!match) return "";
  const roundId = (round.year % 100)*10000 + round.round;
  const scoped = roundId === fixtureContext.roundId;
  const curated = scoped ? fixtureContext.numbers[match.number] ?? {} : {};
  const matched = auto?.fixture;
  if (!matched || ["number","league","home","away","startsAt"].some(key => matched[key] !== match[key])) auto = null;
  const extra = {...curated, ...auto, records:[...(auto?.records ?? []), ...(curated.records ?? [])]};
  const venueKey = key(match.venue || editorial?.venue || detail?.venue);
  const venue = Object.entries(fixtureContext.venues).find(([name])=>key(name)===(venueAliases[venueKey]??venueKey))?.[1];
  const homeCode = aliases[key(match.home)];
  const awayCode = aliases[key(match.away)];
  const epl = match.league.includes("프리미어리그") && homeCode && awayCode;
  const eplSlot = type => `<div class="epl-slot" data-epl-type="${type}" data-epl-home="${escape(match.home)}" data-epl-away="${escape(match.away)}" data-epl-date="${escape(match.startsAt)}">
      <p class="context-basis">기록 불러오는 중…</p></div>`;
  const playerRows = extra.players ?? detail?.playerNotes?.map(p => [p.name,p.team,p.figure,`${p.availability} · ${p.scope} ${p.pattern ?? ""} ${p.note ?? ""}`.trim(),sources[p.refs[0]]]) ?? [];
  const weather = detail?.weatherAssessment;
  const newsRows = [...(extra.news ?? []),...(detail?.events?.map(([date, category, title, body, ref])=>[date,title,body,sources[ref]]) ?? [])];
  const cards = [
    (venue || extra.onSite) ? card("venue","구장 특징","◎","잔디·시설·당일 조건",stadium(venue,extra.onSite)+renderAutomaticFactors(auto,"venue"),opened) : "",
    weather && !weatherFacts(auto).length ? card("weather","경기 환경","",weatherHint(curatedWeatherVisual(detail)),
      `${weatherPanel({...curatedWeatherVisual(detail),readings:weather.readings.map(([label,value])=>({label,value}))})}
      <p class="weather-origin"><strong>${escape(weather.basis)}</strong></p>
      <p>${escape(weather.impact)}</p>
      <details class="weather-evidence"><summary>중계에서 볼 점 · 출처</summary>
      <p>${escape(weather.watch)}</p><p class="context-basis">${escape(weather.basis)}</p>
      ${link(sources[detail.weather?.[2]])}${weather.refs.map(ref=>link(sources[ref])).join("")}</details>`,opened) : "",
    (playerRows.length || editorial?.roster) ? card("players","주요 선수","◇","최근 활약과 출전 상태",
      (editorial?.roster ? `<section class="context-item"><h4>출전 변수</h4><p>${escape(editorial.roster[0])}</p>${link(["NBA 부상 보고서 · 11/21 23:15 KST",editorial.roster[1]])}</section>` : "")+genericItems(playerRows,"player")+renderAutomaticFactors(auto,"players"),opened) : "",
    newsRows.length ? card("news","주요 뉴스","≡","경기에 관련된 발표",genericItems(newsRows,"news")+renderAutomaticFactors(auto,"news"),opened) : "",
    extra.odds ? card("odds","해외 배당","∷","해외 업체가 공개한 배당",overseas(extra.odds,match,round.source),opened) : "",
    (epl || extra.comparison || extra.teamStats?.length) ? card("compare","팀 비교","⇆","홈·원정 득실점",
      extra.comparison ? statedComparison(extra.comparison) : epl ? eplSlot("compare") : automaticComparison(extra.teamStats,match.sport),opened) : "",
    (extra.recent || epl) ? card("recent","최근 5경기","↗","승·무·패와 실제 점수",
      extra.recent ? recentTeams(extra.recent, extra.recentBasis, match.sport) : eplSlot("recent"), opened) : "",
    (extra.records.length || epl) ? card("record","맞대결·팀 패턴","↔","반복된 기록과 경기 수",
      (epl ? eplSlot("record") : "")+(extra.records ?? []).map(([title,summary,source])=>`<section class="context-item"><h4>${escape(title)}</h4><p>${escape(summary)}</p>${link(source)}</section>`).join(""), opened) : ""
  ].filter(Boolean);
  const ids = cards.map(markup => markup.match(/data-context-card="([a-z]+)"/)?.[1]);
  const [check, ...additional] = automaticCards(match,round,auto,ids,card,opened);
  const allCards = [...additional,...cards,check];
  return `<details class="match-context" data-keep-open="context"${opened.has("context") ? " open" : ""}>
    <summary><span>상세 정보</span><span class="context-count">${allCards.length}개 항목</span><span class="context-plus" aria-hidden="true"></span></summary>
    ${renderOutlook(auto?.outlook ?? (match.total ? {kind:"market",headline:`베트맨 기준 ${match.total.line}${match.sport === "축구" ? "골" : "점"} · ${match.total.under === match.total.over ? "언더·오버 배당이 같습니다" : `${match.total.under < match.total.over ? "언더" : "오버"} 쪽 배당이 낮습니다`}`,basis:`언더 ${match.total.under.toFixed(2)} · 오버 ${match.total.over.toFixed(2)}`,source:["베트맨 · 경기 배당",round.source]} : null), match.voided,fixtureHistoryHref(match.number,roundId))}
    <div class="context-cards">${allCards.join("")}</div>
  </details>`;
}

function automaticComparison(teams,sport) {
  const unit = sport === "축구" ? "득점" : sport === "배구" ? "획득 세트" : "득점";
  return `<p class="context-basis">최대 최근 10경기 · 홈과 원정은 각각 최대 5경기 · 등록 자료 기준</p>
    <div class="context-grid-two">${teams.map(team => `<section class="context-stat">
      <h4>${escape(team.team)}</h4><p class="context-number">${team.wins}승 ${team.draws ? team.draws+"무 " : ""}${team.losses}패</p>
      ${splitRows([team,team.home,team.away].map(row=>[row.played,row.for,row.against]),unit)}${link(team.source)}
    </section>`).join("")}</div>`;
}

function archive() {
  historyPromise ??= import("./epl-history.js").then(({ eplHistory }) => {
    const rows = eplHistory.scores.split(";").map(score => {
      const [date,...numbers] = score.split(",");
      return [date,...numbers.map(value=>value === "" ? null : Number(value))];
    });
    return {...eplHistory, rows};
  }).catch(error => { historyPromise = undefined; throw error; });
  return historyPromise;
}

function teamRows(matches, team, teamNames) {
  return matches.map(([day,home,away,htHome,htAway,ftHome,ftAway])=>{
    const atHome = home === team;
    const opponent = teamNames[atHome ? away : home];
    return [day.slice(5).replace("-","/"), extraNames[opponent] ?? byEnglish[opponent] ?? opponent,
      atHome ? "홈" : "원정",atHome ? ftHome : ftAway,atHome ? ftAway : ftHome,atHome ? htHome : htAway,atHome ? htAway : htHome];
  });
}

function splitRows(splits, label = "득점") {
  return `<div class="context-splits"><span>장소</span><span>경기당 ${label}</span><span>경기당 실점</span>
    ${splits.map(([n,gf,ga],i)=>`<span>${["전체","홈","원정"][i]} · ${n}경기</span>
      <b>${n ? (gf/n).toFixed(1) : "—"}</b><b>${n ? (ga/n).toFixed(1) : "—"}</b>`).join("")}</div>`;
}

function statedComparison({date,teams,source}) {
  return `<p class="context-basis">${escape(date)}</p><div class="context-grid-two">${teams.map(([team,rank,points,record,splits])=>
    `<section class="context-stat"><h4>${escape(team)}</h4><p class="context-number">${rank}위</p>
    <p class="context-basis">${points}점 · ${escape(record)}</p>${splitRows(splits)}</section>`).join("")}</div>${link(source)}`;
}

function leagueComparison(matches, teams, season, archiveDate, source) {
  const totals = new Map();
  for (const [,home,away,,,homeGoals,awayGoals] of matches) {
    for (const [team,gf,ga] of [[home,homeGoals,awayGoals],[away,awayGoals,homeGoals]]) {
      const total = totals.get(team) ?? {points:0, difference:0, goals:0};
      total.points += gf > ga ? 3 : gf === ga ? 1 : 0;
      total.difference += gf-ga;
      total.goals += gf;
      totals.set(team,total);
    }
  }
  const order = (a,b) => b.points-a.points || b.difference-a.difference || b.goals-a.goals;
  return `<p class="context-basis">${escape(season)} EPL · ${escape(archiveDate)}까지 집계</p>
    <div class="context-grid-two">${teams.map(([id,name])=>{
      const total = totals.get(id);
      if (!total) return `<section class="context-stat"><h4>${escape(name)}</h4><p>이번 시즌 집계된 리그 경기가 없습니다.</p></section>`;
      const rank = [...totals.values()].filter(other=>order(other,total) < 0).length+1;
      const splits = [
        matches.filter(g=>g[1]===id || g[2]===id),
        matches.filter(g=>g[1]===id),
        matches.filter(g=>g[2]===id)
      ].map(rows=>rows.reduce(([n,gf,ga],[,home,,,,hg,ag])=>
        home===id ? [n+1,gf+hg,ga+ag] : [n+1,gf+ag,ga+hg],[0,0,0]));
      return `<section class="context-stat"><h4>${escape(name)}</h4><p class="context-number">${rank}위</p>
        <p class="context-basis">${total.points}점 · ${splits[0][0]}경기</p>${splitRows(splits)}</section>`;
    }).join("")}</div>${link(source)}`;
}

function halfTimePattern(seasonal, home, away, homeName, awayName) {
  const twoGoals = seasonal.filter(g=>g[3] != null && g[4] != null && g[3]+g[4] === 2);
  const involved = twoGoals.filter(g=>[g[1],g[2]].some(team=>team===home || team===away));
  const noMore = games => games.filter(g=>g[5]+g[6] === 2).length;
  if (!involved.length) return "";
  return `<div class="context-item"><h4>전반에 두 골이 나면 후반은 조용할까?</h4>
    <p class="context-number">${involved.length}경기 중 ${noMore(involved)}경기</p>
    <p>전반에 두 골이 나온 ${escape(homeName)} 또는 ${escape(awayName)}의 리그 경기 중 후반에 골이 더 나오지 않은 횟수입니다.</p>
    <p class="context-basis">같은 기간 리그 전체는 ${twoGoals.length}경기 중 ${noMore(twoGoals)}경기</p>
    <details class="context-evidence"><summary>비교한 경기 점수</summary><ol>
    ${involved.map(([day,h,a,htH,htA,ftH,ftA])=>`<li><time>${escape(day)}</time><span>${escape(h===home || a===home ? homeName : awayName)}</span><strong>전반 ${htH}:${htA} · 최종 ${ftH}:${ftA}</strong></li>`).join("")}
    </ol></details>
  </div>`;
}

function eplContent(slot, history) {
  const {eplHome: homeName,eplAway: awayName,eplDate: date,eplType:type} = slot.dataset;
  const home = history.teams.indexOf(aliases[key(homeName)]);
  const away = history.teams.indexOf(aliases[key(awayName)]);
  // The archive records matches by UK local date, with no kickoff times.
  const local = new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/London",year:"numeric",month:"2-digit",day:"2-digit"})
    .formatToParts(new Date(date));
  const fields = Object.fromEntries(local.map(({type,value})=>[type,value]));
  const cutoff = `${fields.year}-${fields.month}-${fields.day}`;
  const rows = history.rows.filter(game => game[0] < cutoff);
  const homeGames = rows.filter(game => game[1] === home || game[2] === home);
  const awayGames = rows.filter(game => game[1] === away || game[2] === away);
  const [firstSource] = history.sources;
  const recentSource = ["EPL 이번 시즌 기록", firstSource];
  if (type === "recent") {
    return recentTeams([[homeName,teamRows(homeGames.slice(0,5),home,history.teams),recentSource],
      [awayName,teamRows(awayGames.slice(0,5),away,history.teams),recentSource]],
      `EPL 리그 경기만 · 확보 자료 ${history.last}까지 · 이 대진 전`);
  }

  const seasonal = rows.filter(game => game[0] >= history.currentSeason.slice(0,4)+"-07-01");
  if (type === "compare") {
    return leagueComparison(seasonal, [[home,homeName],[away,awayName]], history.currentSeason, history.last, recentSource);
  }
  const homeVenue = teamRows(seasonal.filter(game => game[1] === home),home,history.teams);
  const awayVenue = teamRows(seasonal.filter(game => game[2] === away),away,history.teams);
  const sameVenue = rows.filter(game => game[1] === home && game[2] === away);
  const against = rows.filter(game => (game[1] === home && game[2] === away) || (game[1] === away && game[2] === home));
  const recentH2h = teamRows(against.slice(0,5),home,history.teams);
  const sameHome = teamRows(sameVenue,home,history.teams);
  const describe = (title,games) => {
    if (!games.length) return `<section class="context-stat"><h4>${escape(title)}</h4><p>이 기간에 집계된 경기가 없습니다.</p></section>`;
    const [w,d,l] = counts(games);
    const withHalf = games.filter(g => g[5] != null && g[6] != null);
    const held = withHalf.filter(g => g[5]>g[6]);
    const clean = games.filter(g => g[4]===0).length;
    const halfBlank = withHalf.filter(g => g[5]===0).length;
    return `<section class="context-stat"><h4>${escape(title)}</h4><p class="context-number">${w}승 ${d}무 ${l}패</p>
      <p>${games.length}경기 중 무실점 <b>${clean}</b>경기${withHalf.length ? ` · 전반 무득점 <b>${halfBlank}/${withHalf.length}</b>` : ""}</p>
      ${held.length ? `<p class="context-basis">전반에 앞선 ${held.length}경기 중 ${held.filter(g=>g[3]>g[4]).length}승</p>` : ""}
    </section>`;
  };
  const low = sameHome.filter(g=>g[3]+g[4]<=2).length;
  return `<p class="context-basis">${history.currentSeason.replace("-","/")} 시즌 · 이 대진 전 · 자료 ${history.last}까지</p>
    <div class="context-grid-two">${describe(homeName+" 홈",homeVenue)}${describe(awayName+" 원정",awayVenue)}</div>
    <div class="context-item"><h4>최근 맞대결 ${recentH2h.length}경기 · ${escape(homeName)} 기준</h4>
      ${recentH2h.length ? resultRun(recentH2h) : "<p>이 기간 EPL 맞대결 기록이 없습니다.</p>"}
      ${sameHome.length ? `<p><strong>${escape(homeName)} 홈 맞대결</strong> ${sameHome.length}경기 중 합계 2골 이하 ${low}경기</p>` : ""}
      ${recentH2h.length ? `<details class="context-evidence"><summary>전반·최종 점수</summary><ol>
        ${against.slice(0,5).map(([day,h,a,htH,htA,ftH,ftA])=>`<li><time>${escape(day)}</time><span>${escape(h===home ? homeName+" 홈" : awayName+" 홈")}</span><strong>${htH == null ? "전반 —" : "전반 "+htH+":"+htA} · 최종 ${ftH}:${ftA}</strong></li>`).join("")}
      </ol></details>` : ""}
      <p class="context-basis">표본 ${history.first}~${history.last} · 지난 결과의 빈도</p>
      ${link(["OpenFootball · 과거 EPL 경기 이력","https://github.com/openfootball/football.json"])} ${link(recentSource)}
    </div>${halfTimePattern(seasonal,home,away,homeName,awayName)}`;
}

export function attachTeamContext(container) {
  container.addEventListener("toggle", async event => {
    const panel = event.target;
    if (!panel.open) return;
    const slot = panel.querySelector?.(":scope > .context-body > .epl-slot");
    if (!slot || slot.dataset.loaded) return;
    slot.dataset.loaded = "pending";
    try {
      slot.innerHTML = eplContent(slot, await archive());
      slot.dataset.loaded = "true";
    } catch {
      delete slot.dataset.loaded;
      slot.textContent = "기록을 불러오지 못했습니다. 이 카드를 다시 열어 주세요.";
    }
  }, true);
}
