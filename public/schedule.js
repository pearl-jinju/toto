import { roundSnapshot } from "./fixtures.js";

const publishedRound = {
  ...roundSnapshot,
  matches:roundSnapshot.matches.map(([number, startsAt, closesAt, sport, league, home, away, venue, score, odds, voided, saleStatus]) =>
    ({number, startsAt, closesAt, sport, league, home, away, venue, score, odds, voided, saleStatus}))
};
const apiUrl = ["localhost", "127.0.0.1"].includes(location.hostname) ? "/api/round" : "https://matchindex-round-api.onrender.com/api/round";

function normalizeFeed(feed) {
  const source = new URL(feed.source);
  if (source.origin !== "https://www.betman.co.kr" || !Number.isInteger(feed.year) ||
      !Number.isInteger(feed.round) || !Number.isFinite(Date.parse(feed.snapshotAt)) ||
      !Array.isArray(feed.matches) || !feed.matches.length || feed.matchCount !== feed.matches.length) {
    throw new Error("Invalid official round");
  }
  const seen = new Set();
  const matches = feed.matches.map(fixture => {
    if (!Number.isInteger(fixture.number) || seen.has(fixture.number) ||
        !sportNames.slice(1).includes(fixture.sport) ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$/.test(fixture.startsAt) ||
        !fixture.home || !fixture.away || !fixture.league) throw new Error("Invalid fixture");
    seen.add(fixture.number);
    return {
      number:fixture.number, startsAt:fixture.startsAt, closesAt:fixture.closesAt,
      sport:fixture.sport, league:fixture.league, home:fixture.home, away:fixture.away, venue:fixture.venue,
      score:/^\d+:\d+$/.test(fixture.result) ? fixture.result.split(":").map(Number) : null,
      odds:Array.isArray(fixture.odds) ? fixture.odds.map(odd => typeof odd === "number" && odd > 1 ? odd : null) : [null,null,null],
      voided:fixture.status === "cancelled", saleStatus:fixture.saleStatus
    };
  });
  matches.sort((a,b) => a.startsAt.localeCompare(b.startsAt) || a.number - b.number);
  const sameRound = feed.year === roundSnapshot.year && feed.round === roundSnapshot.round;
  return {
    year:feed.year, round:feed.round, source:source.href, capturedAt:feed.snapshotAt, matches,
    sourceLabel:`베트맨 · 프로토 승부식 ${feed.round}회차`,
    editorial:sameRound ? roundSnapshot.editorial : {},
    briefingNumbers:sameRound ? roundSnapshot.briefingNumbers : {}
  };
}


const sportNames = ["전체", "축구", "야구", "농구", "배구"];
const views = [
  ["schedule", "경기 일정"],
  ["finished", "종료 경기"],
  ["all", "회차 전체"]
];
const pageSize = 24;
const koreaTime = "Asia/Seoul";
const dateLabel = new Intl.DateTimeFormat("ko-KR", { timeZone: koreaTime, month: "long", day: "numeric", weekday: "short" });
const snapshotLabel = new Intl.DateTimeFormat("ko-KR", { timeZone: koreaTime, month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const htmlCharacters = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function text(value) {
  return String(value).replace(/[&<>"']/g, character => htmlCharacters[character]);
}

function sourceLink(label, url) {
  return `<a class="source" href="${text(url)}" target="_blank" rel="noopener noreferrer">${text(label)}</a>`;
}

function matchStatus(match, now) {
  if (match.voided) return ["void", "취소"];
  if (match.score) return ["done", "종료"];
  if (Date.parse(match.startsAt) <= now) return ["pending", "결과 대기"];
  return ["next", "예정"];
}

function quickAnalysis(match, detail, roundData) {
  const extra = roundData.editorial[match.number];
  const ranked = match.odds.map((odd,index) => [odd,index]).filter(([odd]) => odd != null).sort((a,b) => a[0]-b[0]);
  const marketSummary = !match.score && ranked.length > 1 && ranked[0][0] !== ranked[1][0]
    ? `일반 배당은 ${[match.home + " 승", "무승부", match.away + " 승"][ranked[0][1]]} 쪽이 가장 낮습니다.` : "";
  const summary = extra?.summary ?? detail?.summary ?? marketSummary;
  const comparison = extra?.metrics ?? [];
  const oddsAvailable = match.odds.some(odd => odd != null);
  const venue = extra?.venue ?? detail?.venue ?? match.venue;
  const sourceLinks = [sourceLink("베트맨 경기 원본", roundData.source)];
  if (extra) sourceLinks.push(...extra.sources.map(([label, url]) => sourceLink(label, url)));
  if (extra?.roster) sourceLinks.push(sourceLink("NBA 부상 보고서 · 11/21 23:15 KST", extra.roster[1]));

  return `<div class="fixture-analysis">
    ${summary ? `<p class="quick-summary">${text(summary)}</p>` : ""}
    ${comparison.length ? `<dl class="quick-comparison">${comparison.map(([label, home, away]) =>
      `<div><dt>${text(label)}</dt><dd><strong>${text(home)}</strong><span>vs</span><strong>${text(away)}</strong></dd></div>`).join("")}</dl>` : ""}
    ${extra?.roster ? `<p class="quick-roster"><strong>출전 변수</strong> ${text(extra.roster[0])}</p>` : ""}
    <dl class="quick-facts">
      ${match.score ? `<div><dt>최종 점수</dt><dd>${match.score.join(" – ")}</dd></div>` : ""}
      ${venue ? `<div><dt>경기장</dt><dd>${text(venue)}</dd></div>` : ""}
      ${match.closesAt ? `<div><dt>발매 마감</dt><dd>${snapshotLabel.format(new Date(match.closesAt))}</dd></div>` : ""}
      ${oddsAvailable ? `<div><dt>프로토 일반 배당</dt><dd class="quick-odds">${match.odds.map((odd, index) =>
        odd == null ? "" : `<span>${["홈승", "무승부", "원정승"][index]} <strong>${odd.toFixed(2)}</strong></span>`).join("")}</dd></div>` : ""}
    </dl>
    ${!summary && !match.score && !oddsAvailable ? '<p class="muted">아직 확인된 배당과 팀 비교 자료가 없습니다.</p>' : ""}
    <div class="quick-actions">${detail ? `<a class="quick-detail" href="?match=${text(detail.id)}">상세 브리핑</a><a class="quick-detail" href="?match=${text(detail.id)}&amp;view=mini">미니 보기</a>` : ""}
      <details class="fixture-sources"><summary>출처</summary><div>${sourceLinks.join("")}</div></details></div>
  </div>`;
}

function matchRow(match, detail, now, roundData, openNumbers) {
  const [status, label] = matchStatus(match, now);
  const time = match.startsAt.slice(11, 16);
  return `<details class="fixture" data-status="${status}" data-number="${match.number}" name="fixture"${openNumbers.has(match.number) ? " open" : ""}>
    <summary class="fixture-line">
      <time datetime="${text(match.startsAt)}" class="fixture-time">${time}</time>
      <span class="fixture-league"><span class="sport-mark sport-${{축구:"football",야구:"baseball",농구:"basketball",배구:"volleyball"}[match.sport]}">${text(match.sport.slice(0,1))}</span><span>${text(match.league)}</span></span>
      <span class="fixture-teams"><strong>${text(match.home)}</strong><span class="fixture-versus">${match.score ? match.score.join(" : ") : "vs"}</span><strong>${text(match.away)}</strong></span>
      <span class="fixture-status" aria-label="경기 상태 ${label}">${label}</span>
      <span class="fixture-expand"><span>분석표</span><i aria-hidden="true"></i></span>
    </summary>
    ${quickAnalysis(match, detail, roundData)}
  </details>`;
}

function dateSections(matches, detailsByNumber, now, roundData, openNumbers) {
  const grouped = new Map();
  for (const match of matches) {
    const date = match.startsAt.slice(0,10);
    if (!grouped.has(date)) grouped.set(date, []);
    grouped.get(date).push(match);
  }
  return Array.from(grouped, ([date, list]) => `<section class="fixture-day">
    <h3 class="fixture-day-heading"><time datetime="${date}">${dateLabel.format(new Date(date + "T12:00:00+09:00"))}</time></h3>
    <div class="fixture-column-labels" aria-hidden="true"><span>시작</span><span>종목 · 리그</span><span>홈팀 · 원정팀</span><span>상태</span><span></span></div>
    ${list.map(match => matchRow(match, detailsByNumber[match.number], now, roundData, openNumbers)).join("")}
  </section>`).join("");
}

export function withOfficialStatus(game) {
  const fixture = publishedRound.matches.find(match => match.number === publishedRound.briefingNumbers[game.id]);
  return fixture ? { ...game, status:matchStatus(fixture, Date.now())[1], result:fixture.score?.join("–") } : game;
}

export function renderSchedule(main, briefings, params) {
  let roundData = publishedRound;
  let refreshing = false;
  let dateSignature = "";
  let timeState = -1;
  let view = "schedule";
  let chosenDate = "";
  let limit = pageSize;
  let sport = sportNames.includes(params.get("sport")) ? params.get("sport") : "전체";
  main.classList.add("schedule-page");
  main.innerHTML = `<section class="schedule-top">
    <p class="schedule-label" id="round-label"></p>
    <h1>경기 일정</h1>
    <p class="schedule-meta"><span id="round-count"></span> · 한국 시간 · <span id="round-updated" role="status"></span></p>
  </section>
  <div class="schedule-controls">
    <nav class="schedule-views" aria-label="경기 보기">${views.map(([id, label]) => `<button type="button" data-view="${id}">${label}</button>`).join("")}</nav>
    <div class="schedule-refine">
      <label class="schedule-search"><span class="sr-only">팀, 리그, 경기번호 검색</span><span aria-hidden="true" class="search-mark"></span><input id="schedule-search" type="search" placeholder="팀 · 리그 · 경기번호 검색"></label>
      <label class="schedule-sport"><span class="sr-only">종목 선택</span><select id="schedule-sport">${sportNames.map(name => `<option ${name === sport ? "selected" : ""}>${name === "전체" ? "전체 종목" : name}</option>`).join("")}</select></label>
    </div>
    <nav class="schedule-dates" id="schedule-dates" aria-label="경기 날짜"></nav>
  </div>
  <div id="schedule-results"></div>
  <details class="block secondary-panel"><summary>일정과 결과 출처</summary><p class="muted">베트맨 공개 경기표를 1분마다 확인합니다. 출전 변수와 팀 기록은 각 출처의 발표 시점을 기준으로 제공합니다.</p><div id="schedule-origin"></div></details>`;

  const results = main.querySelector("#schedule-results");
  const search = main.querySelector("#schedule-search");
  const select = main.querySelector("#schedule-sport");
  const viewButtons = [...main.querySelectorAll("[data-view]")];
  const dateNav = main.querySelector("#schedule-dates");
  const roundLabel = main.querySelector("#round-label");
  const countLabel = main.querySelector("#round-count");
  const updatedLabel = main.querySelector("#round-updated");
  const origin = main.querySelector("#schedule-origin");

  function updateMetadata(stale) {
    roundLabel.textContent = `프로토 승부식 ${roundData.round}회차`;
    countLabel.textContent = `${roundData.matches.length}경기`;
    updatedLabel.textContent = `${stale ? "마지막 확인" : "자동 갱신"} ${snapshotLabel.format(new Date(roundData.capturedAt))}`;
    origin.innerHTML = sourceLink(roundData.sourceLabel, roundData.source);
  }

  function updateDates() {
    const dates = [...new Set(roundData.matches.map(match => match.startsAt.slice(0,10)))];
    const signature = dates.join(",");
    if (dateSignature === signature) return;
    dateSignature = signature;
    if (chosenDate && !dates.includes(chosenDate)) chosenDate = "";
    dateNav.innerHTML = `<button type="button" data-date="">전체 날짜</button>
      ${dates.map(date => `<button type="button" data-date="${date}">${dateLabel.format(new Date(date + "T12:00:00+09:00"))}</button>`).join("")}`;
  }

  function render(preserveExpansion = false) {
    updateDates();
    const openNumbers = preserveExpansion
      ? new Set(Array.from(results.querySelectorAll(".fixture[open]"), row => Number(row.dataset.number)))
      : new Set();
    const focusNumber = preserveExpansion ? document.activeElement?.closest(".fixture")?.dataset.number : null;
    const detailsByNumber = Object.fromEntries(briefings.filter(game => roundData.briefingNumbers[game.id]).map(game => [roundData.briefingNumbers[game.id], game]));

    for (const button of viewButtons) button.setAttribute("aria-pressed", String(button.dataset.view === view));
    for (const button of dateNav.children) button.setAttribute("aria-pressed", String(button.dataset.date === chosenDate));
    const tokens = search.value.trim().toLocaleLowerCase("ko").split(/\s+/).filter(Boolean);
    const now = Date.now();
    const matching = roundData.matches.filter(match => (sport === "전체" || match.sport === sport) &&
      (!chosenDate || match.startsAt.startsWith(chosenDate)) &&
      tokens.every(token => `${match.home} ${match.away} ${match.league} ${match.number}`.toLocaleLowerCase("ko").includes(token)));
    const completed = matching.filter(match => match.score).reverse();
    const pending = matching.filter(match => matchStatus(match, now)[0] === "pending");
    const upcoming = matching.filter(match => matchStatus(match, now)[0] === "next");
    const lists = view === "finished" ? [["종료 경기", completed, limit]]
      : view === "all" ? [["회차 전체", matching, limit]]
      : [["다가오는 경기", upcoming, limit], ["결과 대기", pending.slice(-4), 4], ["최근 종료", completed.slice(0, 6), 6]];
    results.innerHTML = lists.filter(([, list], index) => list.length || index === 0).map(([label, list, max]) => `<section class="schedule-group">
      <div class="schedule-section-header"><h2>${label}</h2><span>${list.length}경기</span></div>
      ${list.length ? dateSections(list.slice(0,max), detailsByNumber, now, roundData, openNumbers) : '<p class="schedule-empty">조건에 맞는 경기가 없습니다.</p>'}
      ${list.length > max ? '<button class="schedule-more" type="button">경기 더 보기</button>' : ""}
      ${view === "schedule" && label === "최근 종료" && completed.length > list.length ? '<button class="schedule-more" data-show-finished type="button">종료 경기 전체 보기</button>' : ""}
    </section>`).join("");
    if (focusNumber) results.querySelector(`[data-number="${focusNumber}"] > summary`)?.focus({preventScroll:true});
  }

  for (const button of viewButtons) button.addEventListener("click", () => { view = button.dataset.view; limit = pageSize; render(); });
  dateNav.addEventListener("click", event => {
    const button = event.target.closest("[data-date]");
    if (!button) return;
    chosenDate = button.dataset.date;
    limit = pageSize;
    render();
  });
  search.addEventListener("input", () => { limit = pageSize; render(); });
  select.addEventListener("change", () => { sport = select.selectedIndex === 0 ? "전체" : select.value; limit = pageSize; render(); });
  results.addEventListener("click", event => {
    const button = event.target.closest(".schedule-more");
    if (!button) return;
    const showFinished = button.hasAttribute("data-show-finished");
    const nextIndex = showFinished ? 0 : limit;
    if (showFinished) { view = "finished"; limit = pageSize; }
    else limit += pageSize;
    render();
    results.querySelectorAll(".fixture > summary")[nextIndex]?.focus();
  });
  async function refresh() {
    if (refreshing || document.hidden) return;
    refreshing = true;
    try {
      const response = await fetch(apiUrl, { signal:AbortSignal.timeout(45_000) });
      if (!response.ok) throw new Error("Official round unavailable");
      const next = normalizeFeed(await response.json());
      if (next.year * 10_000 + next.round < roundData.year * 10_000 + roundData.round ||
          Date.parse(next.capturedAt) < Date.parse(roundData.capturedAt)) return;
      const expired = next.matches.filter(match => !match.score && Date.parse(match.startsAt) <= Date.now()).length;
      const sameRound = next.round === roundData.round && next.year === roundData.year;
      const updated = !sameRound ||
        JSON.stringify(roundData.matches) !== JSON.stringify(next.matches) || expired !== timeState;
      timeState = expired;
      roundData = next;
      updateMetadata(response.headers.get("X-Data-Stale") === "true");
      if (updated) render(sameRound);
    } catch {
      updateMetadata(true);
    } finally {
      refreshing = false;
    }
  }

  updateMetadata(true);
  render();
  refresh();
  setInterval(refresh, 60_000);
  document.addEventListener("visibilitychange", refresh);
}
