import { escapeHtml } from "./source-links.js";

const number = new Intl.NumberFormat("ko-KR", {minimumFractionDigits:1,maximumFractionDigits:1});

function measurement(value) {
  return Number.isFinite(value) && value >= 0 ? value : null;
}

function heading({team,role,side}) {
  return `<div class="comparison-team" data-side="${side}">
    <span class="comparison-role">${role}</span>
    ${team?.name ? `<strong class="comparison-name">${escapeHtml(team.name)}</strong>` : ""}
    <span class="comparison-sample">${escapeHtml(team?.scope || "비교 자료 없음")}</span>
  </div>`;
}

function metric(sides,key,label,unit) {
  const values = sides.map(({team})=>measurement(team?.[key]));
  const comparable = values.every(value=>value !== null);
  const max = comparable ? Math.max(...values) : 0;
  return `<div class="comparison-metric">
    <dt>${label}</dt>
    <dd class="comparison-pair">${sides.map(({team,role,side},index)=>{
      const value = values[index];
      const content = value === null ? '<span class="comparison-missing">자료 없음</span>'
        : `<strong>${number.format(value)}</strong><span class="comparison-unit">${unit}</span>`;
      const percent = max > 0 ? Number((value/max*100).toFixed(1)) : 0;
      return `<div class="comparison-result" data-side="${side}">
        <span class="sr-only">${role}${team?.name ? " "+escapeHtml(team.name) : ""} </span>
        <div class="comparison-reading">${content}</div>
        ${comparable ? `<div class="comparison-track" aria-hidden="true"><span style="--comparison-fill:${percent}%"></span></div>` : ""}
      </div>`;
    }).join("")}</dd>
  </div>`;
}

export function renderComparisonGraphic({home,away,unit} = {}) {
  const sides = [{team:home,role:"홈팀",side:"home"},{team:away,role:"원정팀",side:"away"}];
  const measureUnit = ["골","점","세트"].includes(unit) ? unit : "";
  const metrics = measureUnit === "세트"
    ? [["gf","경기당 따낸 세트"],["ga","경기당 내준 세트"]]
    : [["gf","경기당 득점"],["ga","경기당 실점"]];
  return `<figure class="comparison-board">
    <figcaption>이 경기 기준 홈·원정 비교</figcaption>
    <div class="comparison-pair comparison-teams">${sides.map(heading).join("")}</div>
    <dl class="comparison-metrics">${metrics.map(([key,label])=>metric(sides,key,label,measureUnit)).join("")}</dl>
  </figure>`;
}
