import { fetchAutomaticContext } from "./auto-context.js";
import { escapeHtml, sourceCredits } from "./source-links.js";

export function fixtureHistoryHref(number,roundId) {
  if (!Number.isInteger(number) || !Number.isInteger(roundId)) return "";
  const target = new URL("./",import.meta.url);
  target.search = new URLSearchParams({fixture:String(number),round:String(roundId),view:"history"});
  return target.href;
}

const date = new Intl.DateTimeFormat("ko-KR",{timeZone:"Asia/Seoul",year:"numeric",month:"long",day:"numeric",hour:"2-digit",minute:"2-digit",hourCycle:"h23"});
const cleanDate = value => typeof value === "string" ? value.slice(0,10) : "";

function teamHistory(team,games) {
  return `<section class="block history-team">
    <h2>${escapeHtml(team)}</h2>
    <p class="muted">${games.length}경기 · 이 팀 점수를 왼쪽에 표시</p>
    <table class="history-table">
      <thead><tr><th scope="col">날짜</th><th scope="col">상대 팀</th><th scope="col">점수</th></tr></thead>
      <tbody>${games.map(([day,opponent,site,gf,ga])=>`<tr>
        <td>${escapeHtml(cleanDate(day))}</td>
        <th scope="row">${escapeHtml(opponent)} <small>${escapeHtml(site)}</small></th>
        <td class="history-score">${escapeHtml(gf)} : ${escapeHtml(ga)}</td>
      </tr>`).join("")}</tbody>
    </table>
  </section>`;
}

function headToHead(games) {
  return `<section class="block history-team">
    <h2>계산에 사용한 맞대결</h2>
    <table class="history-table">
      <thead><tr><th scope="col">날짜</th><th scope="col">홈 · 원정</th><th scope="col">점수</th></tr></thead>
      <tbody>${games.map(([day,home,away,hg,ag])=>`<tr>
        <td>${escapeHtml(cleanDate(day))}</td>
        <th scope="row">${escapeHtml(home)}<small>${escapeHtml(away)}</small></th>
        <td class="history-score">${escapeHtml(hg)} : ${escapeHtml(ag)}</td>
      </tr>`).join("")}</tbody>
    </table>
  </section>`;
}

function report(context,number,roundId) {
  const {fixture,outlook} = context;
  const evidence = outlook?.evidence;
  const modelTeams = Array.isArray(evidence?.teams) ? evidence.teams.filter(team=>Array.isArray(team.games) && team.games.length) : [];
  const recent = Array.isArray(context.recent) ? context.recent : [];
  const teams = modelTeams.length ? modelTeams : recent.map(([team,games])=>({team,games})).filter(team=>Array.isArray(team.games) && team.games.length);
  const h2h = Array.isArray(evidence?.headToHead) ? evidence.headToHead : [];
  const sources = sourceCredits([...(evidence?.sources ?? []),...recent.map(row=>row[2]),outlook?.source]);
  const kickoff = Number.isFinite(Date.parse(fixture.startsAt)) ? date.format(new Date(fixture.startsAt)) : "";
  return `<p class="detail-nav"><a href="./?fixture=${number}">경기 분석표로 돌아가기</a></p>
    <section class="history-header">
      <p class="kicker">${escapeHtml(fixture.league)} · 경기 이력</p>
      <h1>${escapeHtml(fixture.home)} vs ${escapeHtml(fixture.away)}</h1>
      <p class="muted">${escapeHtml(kickoff)} · 한국 시간</p>
      ${roundId === 260138 && number === 5019 ? sourceCredits([["세리에 A 공식 경기 페이지","https://en.legaseriea.it/serie-a/match/97ef80e0aff84867ae6f6c53b2be31e5/parma-vs-roma"]]) : ""}
      ${modelTeams.length ? '<p>득점 전망에 사용한 경기입니다.</p>' : ''}
      ${Number.isInteger(evidence?.leagueCount) ? `<p class="muted">리그 평균에는 ${evidence.leagueCount}경기를 반영했습니다.</p>` : ""}
    </section>
    ${teams.length ? `<div class="history-grid">${teams.map(({team,games})=>teamHistory(team,games)).join("")}</div>`
      : '<p class="block">이 경기에서 확인된 과거 점수 기록이 없습니다.</p>'}
    ${h2h.length ? headToHead(h2h) : ""}
    ${sources ? `<details class="block"><summary>자료 제공처</summary><div class="history-credits">${sources}</div></details>` : ""}`;
}

export function renderHistoryPage(main,params) {
  const match = params.get("fixture") ?? "";
  const round = params.get("round") ?? "";
  if (!/^\d{1,5}$/.test(match) || !/^\d{6}$/.test(round)) {
    main.innerHTML = '<section class="block"><h1>경기 이력</h1><p>경기 번호와 회차를 확인해 주세요.</p><a href="./">경기 목록</a></section>';
    return;
  }
  const number = Number(match);
  const roundId = Number(round);
  document.title = "경기 이력 · 매치인덱스";
  main.innerHTML = '<section class="block" aria-live="polite"><h1>경기 이력</h1><p id="history-status">경기 기록을 불러오는 중입니다.</p><a href="./">경기 목록</a></section>';
  const status = main.querySelector("#history-status");
  async function load(remaining) {
    try {
      const packet = await fetchAutomaticContext(roundId);
      const context = packet?.contexts?.[number];
      if (context?.fixture) {
        main.innerHTML = report(context,number,roundId);
        document.title = `${context.fixture.home} vs ${context.fixture.away} 경기 이력 · 매치인덱스`;
        return;
      }
      if (!packet && remaining > 0) {
        setTimeout(()=>load(remaining-1),3500);
        return;
      }
      status.textContent = "이 회차의 경기 기록을 찾을 수 없습니다.";
    } catch {
      if (remaining > 0) {
        setTimeout(()=>load(remaining-1),3500);
        return;
      }
      status.textContent = "경기 기록을 불러오지 못했습니다.";
    }
  }
  load(8);
}
