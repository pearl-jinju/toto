import { escapeHtml as escape, sourceCredits } from "./source-links.js";

const koreaDateTime = new Intl.DateTimeFormat("ko-KR", {
  timeZone:"Asia/Seoul", month:"numeric", day:"numeric",
  hour:"2-digit", minute:"2-digit", hourCycle:"h23"
});
const numberFormat = new Intl.NumberFormat("ko-KR", { maximumFractionDigits:2 });

const list = value => Array.isArray(value) ? value : [];
const hasValue = value => value != null && value !== "";
const teamKey = value => String(value ?? "").normalize("NFKC").toLowerCase().replace(/\s+/g,"");

function reading(value, unit = "") {
  if (!hasValue(value)) return '<span class="mb-missing" aria-label="자료 없음">—</span>';
  const text = typeof value === "number" && Number.isFinite(value) ? numberFormat.format(value) : String(value);
  return escape(text.endsWith(unit) ? text : text + unit);
}

function empty(message) {
  return `<p class="mb-empty">${escape(message)}</p>`;
}

function sources(pairs, updatedAt) {
  const links = sourceCredits(pairs);
  const time = Date.parse(updatedAt);
  const date = Number.isFinite(time)
    ? `<time datetime="${escape(updatedAt)}">${escape(koreaDateTime.format(time))} KST 기준</time>` : "";
  return links || date ? `<div class="mb-sources">${date}${links}</div>` : "";
}

function scorePair(score) {
  return Array.isArray(score) && score.length === 2 &&
    score.every(value => Number.isInteger(value) && value >= 0);
}

export function renderHeadToHead(auto, match) {
  const rows = list(auto?.headToHead).filter(row => row?.home && row.away &&
    /^\d{4}-\d{2}-\d{2}$/.test(row.date) && scorePair(row.score));
  if (!rows.length) return empty("확인된 맞대결 기록이 없습니다.");
  const home = teamKey(match?.home);
  const away = teamKey(match?.away);
  const results = { home:0, draw:0, away:0 };
  for (const row of rows) {
    const knownTeams = [teamKey(row.home),teamKey(row.away)];
    if (!knownTeams.includes(home) || !knownTeams.includes(away)) continue;
    if (row.score[0] === row.score[1]) results.draw++;
    else results[knownTeams[row.score[0] > row.score[1] ? 0 : 1] === home ? "home" : "away"]++;
  }
  const complete = results.home + results.draw + results.away === rows.length;
  const summary = complete
    ? `${escape(match.home)} ${results.home}승 · ${results.draw}무 · ${escape(match.away)} ${results.away}승`
    : `확인된 맞대결 ${rows.length}경기`;
  return `<div class="mb-panel">
    <p class="mb-h2h-summary">${summary}</p>
    <table class="mb-table mb-h2h">
      <caption class="sr-only">맞대결 경기별 스코어와 한국시간 경기일</caption>
      <thead><tr><th scope="col">경기일</th><th scope="col">홈</th><th scope="col">점수</th><th scope="col">원정</th></tr></thead>
      <tbody>${rows.map(({date,home:homeName,away:awayName,score}) => `<tr>
        <td><time datetime="${escape(date)}">${escape(date.slice(2).replaceAll("-","."))}</time></td>
        <td>${escape(homeName)}</td><td><strong>${score.join(" : ")}</strong></td><td>${escape(awayName)}</td>
      </tr>`).join("")}</tbody>
    </table>
    ${sources(rows.map(row => row.source))}
  </div>`;
}

function statRows(rows) {
  return list(rows).filter(row => row?.label && (hasValue(row.home) || hasValue(row.away)));
}

function bar(value, max) {
  const length = typeof value === "number" && Number.isFinite(value) && value >= 0 && max > 0
    ? 100 * value / max : 0;
  return `<span class="mb-meter" aria-hidden="true"><span style="--mb-length:${length}%"></span></span>`;
}

function statTable(rows, match, label, compare) {
  return `<table class="mb-table mb-stats">
    <caption class="sr-only">${label}</caption>
    <thead><tr><th scope="col">${escape(match?.home ?? "홈")}</th><th scope="col">${label}</th><th scope="col">${escape(match?.away ?? "원정")}</th></tr></thead>
    <tbody>${rows.map(({label,home,away,unit}) => {
      const max = Math.max(0, ...[home,away].filter(value => typeof value === "number" && Number.isFinite(value)));
      const suffix = typeof unit === "string" ? unit : "";
      const graphic = compare && typeof home === "number" && home >= 0 &&
        typeof away === "number" && away >= 0 && Number.isFinite(max);
      return `<tr>
        <td>${reading(home,suffix)}${graphic ? bar(home,max) : ""}</td>
        <th scope="row">${escape(label)}</th>
        <td>${reading(away,suffix)}${graphic ? bar(away,max) : ""}</td>
      </tr>`;
    }).join("")}</tbody>
  </table>`;
}

function startingLineups(lineups,match) {
  if (lineups?.home?.length !== 5 || lineups?.away?.length !== 5) return "";
  return `<details class="context-evidence mb-lineups">
    <summary>확정 선발 · 선수 득점과 도움</summary>
    <div class="context-grid-two">${["home","away"].map(side=>`
      <section class="context-stat"><h4>${escape(match[side])}</h4>
        <ul>${lineups[side].map(player=>`<li><span>${escape(player.name)}</span>
          <small>${reading(player.points,"득점")} · ${reading(player.assists,"도움")}</small></li>`).join("")}</ul>
      </section>`).join("")}</div>
  </details>`;
}

function eventList(events, match) {
  const verified = list(events).filter(event => event?.label);
  if (!verified.length) return "";
  return `<h4>주요 장면</h4><ol class="mb-events">
    ${verified.map(({minute,label,side}) => {
      const team = side === "home" ? match?.home : side === "away" ? match?.away : "";
      const time = Number.isFinite(minute) || /^\d+(?:\+\d+)?$/.test(minute ?? "") ? `${minute}분` : minute;
      return `<li>${hasValue(time) ? `<span class="mb-event-time">${escape(time)}</span>` : ""}
        <span>${team ? `<strong>${escape(team)}</strong> ` : ""}${escape(label)}</span></li>`;
    }).join("")}
  </ol>`;
}

export function renderMatchStatistics(auto, match) {
  const stats = auto?.matchStats;
  const periods = statRows(stats?.periods);
  const metrics = statRows(stats?.metrics);
  const events = eventList(stats?.events,match);
  const lineups = startingLineups(stats?.lineups,match);
  const live = stats?.state === "live";
  const finished = stats?.state === "finished";
  if (!(live || finished) || !(periods.length || metrics.length || events || lineups)) {
    if (match?.voided) return empty("취소된 경기입니다.");
    const start = Date.parse(match?.startsAt);
    if (Number.isFinite(start) && start > Date.now()) return empty("경기 시작 전입니다.");
    return empty("확인된 경기 통계가 아직 없습니다.");
  }
  return `<div class="mb-panel">
    <div class="mb-status" data-live="${live}">${live ? "경기 중" : "경기 종료"}</div>
    ${periods.length ? statTable(periods,match,"구간별 점수",false) : ""}
    ${metrics.length ? statTable(metrics,match,"주요 지표",true) : ""}
    ${lineups}${events}
    ${sources([stats.source,stats.reference],stats.updatedAt)}
  </div>`;
}

function winPercent(value) {
  if (!hasValue(value)) return reading(value);
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return reading(value);
  return reading(numeric <= 1 && numeric >= 0 ? numeric * 100 : numeric,"%");
}

function standingTable(group, match, league) {
  const rows = list(group?.rows).filter(row => row?.team);
  if (!rows.length) return "";
  const columns = [
    ["played","경기"],["points","승점"],["winPct","승률"],["wins","승"],["draws","무"],["losses","패"],
    ["for","득점"],["against","실점"]
  ].filter(([key]) => rows.some(row => hasValue(row[key])));
  const title = [league,group.name,"순위"].filter(Boolean).join(" ");
  return `<div class="mb-standings-scroll" role="region" aria-label="${escape(title)}" tabindex="0">
    <table class="mb-table mb-standings">
      <caption class="sr-only">${escape(title)}</caption>
      <thead><tr><th scope="col">순위</th><th scope="col">팀</th>
        ${columns.map(([,label]) => `<th scope="col">${label}</th>`).join("")}</tr></thead>
      <tbody>${rows.map(row => {
        const key = teamKey(row.team);
        const side = key === teamKey(match?.home) ? "홈" : key === teamKey(match?.away) ? "원정" : "";
        return `<tr${side ? ' class="mb-current-team"' : ""}>
          <td>${reading(row.rank)}</td>
          <th scope="row">${escape(row.team)}${side ? `<span class="mb-side">${side}</span>` : ""}</th>
          ${columns.map(([key]) => `<td>${key === "winPct" ? winPercent(row[key]) : reading(row[key])}</td>`).join("")}
        </tr>`;
      }).join("")}</tbody>
    </table>
  </div>`;
}

export function renderStandings(standings, match) {
  const league = standings?.league ?? match?.league;
  const groups = list(standings?.groups).map(group => {
    const content = standingTable(group,match,league);
    return content && `${group.name ? `<h4>${escape(group.name)}</h4>` : ""}${content}`;
  }).filter(Boolean);
  if (!groups.length) return empty("확인된 리그 순위 자료가 없습니다.");
  return `<div class="mb-panel">
    ${standings.season ? `<p class="mb-season">${escape(standings.season)} 시즌</p>` : ""}
    ${groups.join("")}
    ${sources([standings.source,standings.reference],standings.updatedAt)}
  </div>`;
}
