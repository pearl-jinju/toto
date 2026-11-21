import { games, sports } from "./data.js";

const filters = document.querySelector("#filters");
const list = document.querySelector("#matches");
const panel = document.querySelector("#analysis");
const search = document.querySelector("#search");
let sport = "전체";
let selected = games[0].id;

function button(label, active, onClick) {
  const element = document.createElement("button");
  element.type = "button";
  element.textContent = label;
  element.setAttribute("aria-pressed", String(active));
  element.addEventListener("click", onClick);
  return element;
}

for (const category of ["전체", ...Object.keys(sports)]) {
  filters.append(button(category, category === sport, () => {
    sport = category;
    for (const item of filters.children) {
      item.setAttribute("aria-pressed", String(item.textContent === sport));
    }
    render();
  }));
}

function render() {
  const query = search.value.trim().toLocaleLowerCase("ko");
  const matches = games.filter(game =>
    (sport === "전체" || game.sport === sport) &&
    [game.home, game.away, game.league].some(name => name.toLocaleLowerCase("ko").includes(query))
  );
  const game = matches.find(match => match.id === selected) ?? matches[0];
  selected = game?.id;
  list.replaceChildren();

  for (const match of matches) {
    const entry = button("", match.id === selected, () => {
      selected = match.id;
      for (const item of list.children) item.setAttribute("aria-pressed", String(item === entry));
      showAnalysis(match);
    });
    entry.className = "match";
    const meta = document.createElement("small");
    meta.textContent = `${match.sport} · ${match.league} · ${match.time}`;
    const teams = document.createElement("strong");
    teams.textContent = `${match.home} vs ${match.away}`;
    entry.append(meta, teams);
    list.append(entry);
  }

  if (game) showAnalysis(game);
  else panel.textContent = "조건에 맞는 경기가 없습니다.";
}

function showAnalysis(game) {
  const { outcomes, metrics, rule } = sports[game.sport];
  const impliedTotal = game.odds.reduce((sum, price) => sum + 1 / price, 0);
  const row = (label, home, away) => `<div class="metric"><b>${home}</b><span>${label}</span><b>${away}</b></div>`;
  // All interpolated text comes from first-party, bundled fixtures.
  panel.innerHTML = `
    <p class="muted">${game.league} · ${game.time} (한국 시간) · 가상 경기</p>
    <h2 class="score"><strong>${game.home}</strong><span>VS</span><strong>${game.away}</strong></h2>
    <h3>예시 결과 확률</h3>
    <div class="prob" aria-hidden="true">${game.weights.map(value => `<span style="width:${value}%"></span>`).join("")}</div>
    <div class="labels">${outcomes.map((name, index) => `<span>${name} <b>${game.weights[index]}%</b></span>`).join("")}</div>
    <p class="muted">${rule}</p>
    <h3>홈·원정 전력 비교</h3>
    ${row("최근 5경기 (최신 → 과거)", ...game.form)}
    ${row("홈팀 홈 / 원정팀 원정 최근 5경기", ...game.splits)}
    ${metrics.map((label, index) => row(label, ...game.values[index])).join("")}
    <p><strong>최근 맞대결 5경기</strong> · ${game.h2h}</p>
    <p><strong>경기 변수</strong> · ${game.note}</p>
    <details><summary>예시 배당과 환산 확률</summary>
    ${outcomes.map((name, index) => `<div class="metric"><span>${name}</span><b>${game.odds[index].toFixed(2)} · ${(100 / game.odds[index] / impliedTotal).toFixed(1)}%</b></div>`).join("")}
    <p class="muted">환산 확률은 배당 역수를 그 합으로 나눈 값입니다. 위의 예시 결과 확률은 화면 시연용으로 설정한 값입니다.</p></details>`;
}

search.addEventListener("input", render);
render();
