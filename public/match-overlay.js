import { escapeHtml as escape } from "./source-links.js";
import { fixtureDateKeys, koreaDateKey, mountDateRoller } from "./date-roller.js";
import { mascotArt } from "./match-visuals.js";
import { teamLabel } from "./team-symbols.js";

const sports = ["전체","축구","야구","농구","배구"];
const overlaySizes = [
  {name:"작게",width:260,height:330},
  {name:"보통",width:320,height:410},
  {name:"크게",width:410,height:525}
];
export const defaultOverlaySize = overlaySizes[1];

export function mountMatchOverlay(container, {close, resize, renderMatch, mode, initialMatch}) {
  container.innerHTML = `<section class="match-overlay" role="region" aria-label="경기 분석 오버레이" data-mode="${mode}">
    <div class="overlay-header">
      <div class="overlay-heading">
        <span class="overlay-mascot" aria-hidden="true">${mascotArt("courtside",true)}</span>
        <div>
          <strong tabindex="-1">${mode === "dock" ? "웹 미니 보기" : "경기 분석"}</strong>
          ${mode === "dock" ? '<small>이 웹페이지 안에 표시됩니다</small>' : ""}
        </div>
      </div>
      <div class="overlay-actions">
        <button type="button" class="overlay-back" hidden>경기 목록</button>
        ${resize ? `<details class="overlay-size">
          <summary aria-label="창 크기">크기</summary>
          <div class="overlay-size-options">${overlaySizes.map((size,index)=>`<button type="button" data-overlay-size="${index}" aria-pressed="${size === defaultOverlaySize}">${size.name}</button>`).join("")}
            <p role="status" hidden>창 가장자리를 끌어 크기를 조절할 수 있습니다.</p></div>
        </details>` : ""}
        ${close ? '<button type="button" class="overlay-close" aria-label="오버레이 닫기">닫기</button>' : ""}
      </div>
    </div>
    <div class="overlay-picker">
      <button type="button" class="overlay-filter-toggle" aria-controls="overlay-refinement" aria-expanded="false">
        <span>검색·날짜</span><small class="overlay-filter-date"></small>
      </button>
      <div class="overlay-filter-bar" id="overlay-refinement">
        <div class="overlay-filters">
          <label><span class="sr-only">경기 검색</span><input type="search" placeholder="팀 · 리그 · 경기번호"></label>
          <label><span class="sr-only">종목 선택</span><select>${sports.map(sport=>`<option value="${sport}">${sport === "전체" ? "전체 종목" : sport}</option>`).join("")}</select></label>
        </div>
        <div class="overlay-dates"></div>
      </div>
      <ul class="overlay-list" aria-label="경기 목록"></ul>
      <p class="schedule-empty overlay-empty" hidden>검색 조건에 맞는 경기가 없습니다.</p>
    </div>
    <div class="overlay-detail fixture-mini" hidden></div>
  </section>`;
  const panel = container.firstElementChild;
  const picker = panel.querySelector(".overlay-picker");
  const list = panel.querySelector(".overlay-list");
  const empty = panel.querySelector(".overlay-empty");
  const search = panel.querySelector("input");
  const sport = panel.querySelector("select");
  const back = panel.querySelector(".overlay-back");
  const heading = panel.querySelector(".overlay-header strong");
  const sizing = panel.querySelector(".overlay-size");
  const filterToggle = panel.querySelector(".overlay-filter-toggle");
  const filterDate = panel.querySelector(".overlay-filter-date");
  const detail = panel.querySelector(".overlay-detail");
  let matches = [];
  let active = initialMatch ?? null;
  let activeRound;
  let listMarkup = null;
  let datesSignature = "";
  let chosenDate = koreaDateKey();
  const datePanel = panel.querySelector(".overlay-dates");
  const updateFilterDate = () => {
    filterDate.textContent = datePanel.querySelector("[role=slider]").getAttribute("aria-valuetext") ?? "";
  };
  const dateRoller = mountDateRoller(datePanel,date=>{
    chosenDate = date;
    updateFilterDate();
    results();
  });
  filterToggle.addEventListener("click",()=>{
    const expanded = picker.classList.toggle("filters-open");
    filterToggle.setAttribute("aria-expanded",String(expanded));
  });

  function results() {
    const query = search.value.trim().toLocaleLowerCase("ko");
    const terms = query ? query.split(/\s+/) : [];
    const visible = matches.filter(match => (sport.value === "전체" || match.sport === sport.value) &&
      (!chosenDate || match.startsAt.startsWith(chosenDate)) &&
      terms.every(term => `${match.home} ${match.away} ${match.league} ${match.number}`.toLocaleLowerCase("ko").includes(term)));
    empty.hidden = visible.length > 0;
    const ended = match => Boolean(match.score || match.voided);
    visible.sort((a,b)=>Number(ended(a))-Number(ended(b)) ||
      (ended(a) ? b.startsAt.localeCompare(a.startsAt) : a.startsAt.localeCompare(b.startsAt)));
    const markup = visible.map(match => {
      const day = match.startsAt.slice(5,10).replace("-",".");
      const time = match.startsAt.slice(11,16);
      return `<li><button type="button" data-overlay-match="${match.number}">
        <span class="overlay-match-meta">${day} ${time} · ${escape(match.league)}</span>
        <span class="overlay-match-teams">${teamLabel(match.home)} <span class="overlay-score">${match.score ? match.score.join(" : ") : "vs"}</span> ${teamLabel(match.away)}</span>
      </button></li>`;
    }).join("");
    if (listMarkup !== markup) {
      list.innerHTML = markup;
      listMarkup = markup;
    }
  }

  function render() {
    const match = active === null ? null : matches.find(item=>item.number === active);
    if (!match) active = null;
    picker.hidden = Boolean(match);
    detail.hidden = !match;
    back.hidden = !match;
    if (match) renderMatch(detail,match);
    else {
      detail.replaceChildren();
      results();
    }
  }

  function choose(number) {
    if (active === number) return;
    const previous = active;
    active = number;
    detail.replaceChildren();
    detail.scrollTop = 0;
    render();
    if (number === null) (list.querySelector(`[data-overlay-match="${previous}"]`) ?? heading).focus();
    else detail.querySelector("h1")?.focus();
  }

  sizing?.addEventListener("click",event=>{
    const button = event.target.closest("[data-overlay-size]");
    if (!button) return;
    const help = sizing.querySelector("p");
    try {
      resize(overlaySizes[Number(button.dataset.overlaySize)]);
      for (const option of sizing.querySelectorAll("button")) option.setAttribute("aria-pressed",String(option === button));
      help.hidden = true;
      sizing.open = false;
      sizing.querySelector("summary").focus({preventScroll:true});
    } catch {
      help.hidden = false;
    }
  });
  search.addEventListener("input",results);
  sport.addEventListener("change",results);
  back.addEventListener("click",()=>choose(null));
  panel.querySelector(".overlay-close")?.addEventListener("click",close);
  list.addEventListener("click",event=>{
    const game = event.target.closest("[data-overlay-match]");
    if (game) choose(Number(game.dataset.overlayMatch));
  });
  panel.addEventListener("keydown",event=>{
    if (event.key !== "Escape") return;
    if (sizing?.open) {
      sizing.open = false;
      sizing.querySelector("summary").focus({preventScroll:true});
      return;
    }
    if (active !== null) choose(null);
    else close?.();
  });
  detail.addEventListener("click",event=>{
    if (!event.target.closest(".history-shortcut")) return;
    event.preventDefault();
    const section = detail.querySelector('.context-card[data-context-card="recent"], .context-card[data-context-card="headtohead"]');
    if (!section) return;
    section.closest(".match-context").open = true;
    section.open = true;
    section.querySelector("summary")?.focus();
  });

  return {
    destroy: dateRoller.destroy,
    update(next,round) {
      matches = next;
      const today = koreaDateKey();
      const dates = fixtureDateKeys(next,today);
      const signature = dates.join(",");
      if (signature !== datesSignature) {
        datesSignature = signature;
        if (chosenDate && !dates.includes(chosenDate)) chosenDate = today;
        dateRoller.update(dates,chosenDate);
        updateFilterDate();
      }
      if (activeRound != null && activeRound !== round) {
        active = null;
        detail.replaceChildren();
      }
      activeRound = round;
      render();
    },
    focus() {
      (active === null ? heading : back).focus({preventScroll:true});
    }
  };
}
