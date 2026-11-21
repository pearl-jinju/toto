import { snapshot, sources, games } from "./data.js";

const main = document.querySelector("#main");
const categories = ["전체", "축구", "야구", "농구", "배구"];
const params = new URLSearchParams(location.search);
const selected = games.find(game => game.id === params.get("match"));
const mini = params.get("view") === "mini";
let sport = categories.includes(params.get("sport")) ? params.get("sport") : "전체";

// Markup below interpolates editorial data shipped with this release.
// User-entered search text is only used for comparison.
function source(key) {
  if (!key) return "";
  const [label, url] = sources[key];
  return `<a class="source" href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
}
function matchUrl(game, compact = mini) {
  return `?match=${game.id}${compact ? "&view=mini" : ""}`;
}

const variables = {
  축구: [
    ["실외 환경","강수와 배수는 잔디 마찰을, 맞바람·측풍은 롱볼과 크로스를, 폭염은 압박 강도를 점검할 단서입니다. 적설·결빙·박무는 경기 진행 공지를 먼저 확인하세요."],
    ["홈·원정","같은 대회 홈·원정 xG와 실점, 원정 이동 및 대표팀 복귀 일정, 잔디 종류, 관중 규모를 대조하세요. 상대 수준과 퇴장 여부도 확인하세요."],
    ["특정 구장만 가면 약하다?","미검증 가설. 최근 몇 번의 결과만으로는 판단하기 어렵습니다. 같은 구장 성적을 리그 전체 원정 성적과 비교하고 감독·선수 교체, 상대 수준, 홈 관중 조건을 같이 확인하세요."],
    ["전두언 · 전반 2골이면 언더?","미검증 가설. 전반 합계 2골에 도달한 경기에서 최종 언더 비율을 기준점별로 따로 계산해야 합니다. 2.5와 3.5를 섞지 말고 하프타임 점수 차, 퇴장, 리그, 배당 시점을 통제해야 합니다."]
  ],
  야구: [
    ["비 오는 날 투수 우세?","미검증 가설. 비는 공·마운드·수비에도 영향을 주고, 우천 중단은 선발의 재등판 또는 불펜 투입을 바꿀 수 있습니다. 강수량, 중단 시점, 돔 지붕 상태와 양 팀 불펜 소모를 확인하세요."],
    ["기온·바람·구장 구조","MLB 연구에서는 평균적으로 높은 기온과 홈런 증가가 연관됐습니다. 외야 방향에 대한 바람, 펜스 치수, 구장 고도, 지붕, 타구 각도도 함께 보세요.", "research"],
    ["홈·원정과 투수 운용","구장 보정 득점, 상대 선발의 좌우 유형, 포수와의 조합, 최근 투구 수·휴식일, 전날 불펜 연투를 보세요. 홈팀 끝내기까지 포함한 최종 득점은 이닝 맥락과 함께 읽으세요."],
    ["파울 홈런 뒤 삼진?","미검증 가설. 이미 2스트라이크였는지, 풀카운트인지에 따라 삼진 가능성이 다릅니다. 같은 카운트·투타 조합에서 평범한 파울 뒤 삼진율과 비교하고, ‘홈런성 파울’ 분류의 일관성도 확인해야 합니다."]
  ],
  농구: [
    ["실내 환경과 날씨","외부 날씨의 직접 영향은 제한적입니다. 폭설·폭우로 실제 항공 지연이나 경기 연기가 공지됐다면 이동 일정과 워밍업 시간을 확인하세요."],
    ["홈·원정","백투백 두 번째 경기인지, 원정 연전 몇 번째인지, 시차와 고도가 달라졌는지 확인하세요. 홈·원정 공격 효율과 수비 효율은 같은 포제션 기준으로 비교하세요."],
    ["친정팀 상대 복수전?","미검증 가설. 개인 득점 증가가 출전 시간이나 볼 소유 증가 때문인지, 같은 역할과 상대 수비 수준을 기준으로 비교해야 합니다."]
  ],
  배구: [
    ["실내 환경과 날씨","기상은 이동 차질이나 경기장 운영 공지가 있을 때 따로 봅니다. 조명, 천장 높이, 배경 대비, 실내 온습도는 실제 구장 변화나 선수 발언이 확인되면 검토하세요."],
    ["홈·원정","홈·원정 서브 득실, 리시브 효율, 세터와 주공격수 조합, 직전 경기 세트 수와 이동을 비교하세요. 홈 이점은 상대 수준과 로테이션을 함께 고려하세요."],
    ["첫 세트를 가져가면 흐름이 굳는다?","첫 세트 리드는 이미 승리에 가까워진 상태입니다. 별도의 기세 효과를 보려면 사전 전력, 첫 세트 점수 차, 라인업 변화가 비슷했던 경기끼리 비교해야 합니다."]
  ]
};

function guide(category, all = false) {
  const names = all ? Object.keys(variables) : [category];
  return names.map(name => `<details class="guide"><summary>${name} 변수와 징크스</summary><div>${variables[name].map(([title, body, ref]) =>
    `<h3>${title}</h3><p>${body}</p>${source(ref)}`).join("")}</div></details>`).join("");
}

function showBoard() {
  main.innerHTML = `<section class="hero"><p class="kicker">프로토 승부식 · 138회차</p><h1>스코어 옆, 경기의 맥락</h1>
    <p>부상과 감독 발언, 홈·원정, 경기장 환경까지 확인하세요.</p>
    <p class="snapshot">${snapshot} 스냅샷 · 선정 경기 브리핑</p></section>
    <section aria-labelledby="games-title"><div class="bar"><h2 id="games-title">경기 브리핑</h2><input id="search" type="search" aria-label="팀, 리그, 구장 검색" placeholder="팀, 리그, 구장 검색"></div>
    <div id="filters" class="filters" aria-label="종목 필터"></div><p id="count" class="muted" role="status"></p><div class="cards" id="cards"></div></section>
    <section class="block"><h2>경기 환경과 징크스</h2><p>확인된 기록과 추가 검증이 필요한 가설을 살펴보세요.</p>${guide(null,true)}</section>
    <section class="block"><h2>데이터 범위</h2><p>138회차 일부를 편성 자료와 구단·리그 원문으로 대조했습니다. 자동 갱신은 제공하지 않습니다.</p>${source("round")} ${source("slate")}</section>`;
  const filters = document.querySelector("#filters");
  const search = document.querySelector("#search");
  for (const name of categories) {
    const button = document.createElement("button");
    button.textContent = name;
    button.type = "button";
    button.addEventListener("click", () => { sport = name; renderCards(); });
    filters.append(button);
  }
  function renderCards() {
    for (const button of filters.children) button.setAttribute("aria-pressed", String(button.textContent === sport));
    const query = search.value.trim().toLocaleLowerCase("ko");
    const matches = games.filter(game => (sport === "전체" || game.sport === sport) &&
      [game.home, game.away, game.league, game.venue].some(value => value.toLocaleLowerCase("ko").includes(query)));
    document.querySelector("#count").textContent = `브리핑 ${matches.length}경기 · 한국 시간`;
    document.querySelector("#cards").innerHTML = matches.map(game => `<article class="card">
      <p class="meta"><span>${game.sport} · ${game.league}</span><span class="pill">${game.status}</span></p>
      <h3>${game.home} <span class="muted">vs</span> ${game.away}</h3><p class="muted">${game.time} · ${game.venue}</p>
      <p>${game.summary}</p><div class="actions"><a class="primary" href="${matchUrl(game)}">상세 브리핑</a><a href="${matchUrl(game,true)}">미니 보기</a></div>
    </article>`).join("") || `<p class="empty">${sport === "야구" && !query ? "138회차에는 야구가 편성되지 않았습니다. 아래 야구 변수와 징크스 가이드를 이용할 수 있습니다." : "조건에 맞는 브리핑이 없습니다."}</p>`;
  }
  search.addEventListener("input", renderCards);
  renderCards();
}

function metricList(rows) {
  return `<dl class="metrics">${rows.map(([label,value,ref]) => `<div><dt>${label}</dt><dd><strong>${value}</strong>${source(ref)}</dd></div>`).join("")}</dl>`;
}
function briefing(game, compact) {
  const [weatherTitle, weatherBody, weatherRef] = game.weather;
  return `<section class="${compact ? "minihead" : "hero"}">
    <p class="kicker">${game.sport} · ${game.league} · ${game.listed ? "138회차" : "리그 일정 참고"} </p>
    <h1>${game.home} vs ${game.away}</h1>
    <p class="muted">${game.time} KST · ${game.venue}</p>
    <p><span class="pill">${game.status}${game.result ? " · " + game.result : ""}</span></p>
    <p>${game.summary}</p>${source(game.source)}
  </section>
  <div class="brief-grid">
    <section class="block"><h2>경기장 환경</h2><strong>${weatherTitle}</strong><p>${weatherBody}</p>${source(weatherRef)}</section>
    <section class="block"><h2>홈·원정</h2><p><strong>홈</strong> ${game.home} · <strong>원정</strong> ${game.away}</p>
      ${game.splits ? metricList(game.splits) : '<p class="muted">비교 가능한 홈·원정 분리 기록은 아직 확인되지 않았습니다.</p>'}</section>
    <section class="block"><h2>주요 지표</h2>${metricList(game.metrics)}</section>
    <section class="block"><h2>해석과 확인 포인트</h2><ul>${game.watch.map(note => `<li>${note}</li>`).join("")}</ul></section>
  </div>
  <section class="block"><h2>최근 7일 이슈</h2><div class="timeline">${game.events.map(([date,type,title,body,ref]) =>
    `<article><p class="kicker">${date} · ${type}</p><h3>${title}</h3><p>${body}</p>${source(ref)}</article>`).join("")}</div></section>
  <section class="block"><h2>추가 변수와 징크스</h2>${guide(game.sport)}</section>
  <p class="muted">${snapshot} 자료 · 부상과 출전 상태는 이후 공식 발표에 따라 바뀔 수 있습니다.</p>`;
}
function showBriefing(game) {
  document.title = `${game.home} vs ${game.away} · 매치인덱스`;
  document.body.classList.toggle("compact", mini);
  main.innerHTML = `<nav class="actions detail-nav" aria-label="브리핑 탐색">
    <a href="./?sport=${game.sport}">경기 목록</a>
    ${mini ? `<a href="${matchUrl(game,false)}">전체 브리핑</a>` : '<button class="primary" id="overlay">미니 오버레이 열기</button>'}</nav>${briefing(game,mini)}`;
  document.querySelector("#overlay")?.addEventListener("click", async () => {
    const options = { width: 420, height: 640 };
    try {
      const overlay = await window.documentPictureInPicture.requestWindow(options);
      overlay.document.documentElement.lang = "ko";
      overlay.document.title = document.title;
      const stylesheet = overlay.document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = new URL("./style.css", location.href);
      overlay.document.head.append(stylesheet);
      overlay.document.body.className = "compact";
      const content = overlay.document.createElement("main");
      content.className = "wrap";
      content.innerHTML = briefing(game,true);
      overlay.document.body.append(content);
    } catch {
      window.open(matchUrl(game,true), "_blank", "popup,width=420,height=640,noopener");
    }
  });
}

if (selected) showBriefing(selected);
else showBoard();
