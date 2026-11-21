const displayDate = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "long",
  day: "numeric",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});
const htmlCharacters = { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" };

const categories = [
  ["venue","구장 세부","◎","경기장과 시설"],
  ["weather","경기 환경","☀","예보와 경기 중 볼 점"],
  ["players","주요 선수","◇","선발과 몸 상태"],
  ["news","주요 뉴스","≡","공식 발표와 보도"],
  ["odds","해외 배당","∷","출처에 공개된 배당"],
  ["schedule","일정 변수","◷","경기 간격과 이동"],
  ["scoring","득점 기록","↗","기준점 아래가 나온 횟수"]
];
const coverageLabels = [
  ["recent","최근 경기"], ["compare","팀 비교"], ["record","맞대결·패턴"],
  ...categories.slice(0,5).map(([category,title]) => [category,title])
];

function escape(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => htmlCharacters[char]);
}

function sourceLink(pair) {
  if (!Array.isArray(pair) || typeof pair[0] !== "string" || typeof pair[1] !== "string") return "";
  try {
    const address = new URL(pair[1]);
    if (address.protocol !== "https:" || address.username || address.password) return "";
    return `<a class="source" href="${escape(address.href)}" target="_blank" rel="noopener noreferrer">${escape(pair[0])}</a>`;
  } catch {
    return "";
  }
}

function formatDate(date) {
  if (typeof date !== "string" || !date) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(date)) return date;
  if (!/^\d{4}-\d{2}-\d{2}T/.test(date)) return date;
  const time = Date.parse(date);
  return Number.isFinite(time) ? displayDate.format(time) : date;
}

function renderLine(label,value) {
  return value ? `<div><dt>${label}</dt><dd>${escape(value)}</dd></div>` : "";
}

function renderFact(fact) {
  const {title, value, text, date, source, reference} = fact;
  return `<section class="context-item">
    ${value != null && value !== "" ? `<h4 class="context-number">${escape(value)}</h4><p class="context-basis">${escape(title)}</p>` : `<h4>${escape(title)}</h4>`}
    ${text ? `<p>${escape(text)}</p>` : ""}
    ${date ? `<p class="context-basis">${escape(formatDate(date))}</p>` : ""}
    ${sourceLink(source)}${sourceLink(reference)}
    </section>`;
}

export function renderAutomaticFactors(context,category) {
  const facts = Array.isArray(context?.factors) ? context.factors : [];
  return facts.filter(fact => fact?.category === category && fact.title && sourceLink(fact.source)).map(renderFact).join("");
}

function fixtureCheck(match,round,context,available) {
  const score = match.score?.join(" – ");
  const status = match.voided ? "취소"
    : score ? "종료" : Date.parse(match.startsAt) <= Date.now() ? "결과 대기" : "예정";
  const missing = coverageLabels.filter(([category]) => !available.has(category)).map(([,label]) => label);
  const source = context?.coverage?.source;
  const matched = context?.coverage?.matched === true;
  const anyExternal = available.size > 0;
  const dataStatus = matched
    ? (source && typeof source === "string" && !source.startsWith("https://") && !source.startsWith("http://") ? source + " 경기 연결" : "외부 경기 자료 연결")
    : anyExternal ? "일부 항목 자료 확인" : context ? "추가 자료 확인 중" : "추가 자료 확인 전";
  return `<h4>${escape(match.home)} <span aria-hidden="true">·</span> ${escape(match.away)}</h4>
    <dl class="quick-facts">
      ${renderLine("대회",match.league)}
      ${renderLine("시작",formatDate(match.startsAt))}
      ${renderLine(status === "종료" ? "최종 점수" : "경기 상태",status === "종료" ? score : status)}
      ${renderLine("경기장",match.venue)}
    </dl>
    <div class="context-item">
      <h4>${escape(dataStatus)}</h4>
      ${context?.updatedAt ? `<p class="context-basis">추가 자료 확인 ${escape(formatDate(context.updatedAt))} · 한국 시간</p>` : ""}
      ${missing.length ? `<p class="context-basis">현재 확인된 추가 자료 없음 · ${escape(missing.join(" · "))}</p>` : ""}
      ${sourceLink(["베트맨 · 경기 정보",round.source])}
    </div>`;
}

export function automaticCards(match, round, context, existingIds, card, opened) {
  const present = new Set(existingIds);
  const facts = Array.isArray(context?.factors) ? context.factors : [];
  const grouped = new Map();
  for (const fact of facts) {
    if (!fact?.title || !sourceLink(fact.source)) continue;
    const items = grouped.get(fact.category) ?? [];
    items.push(fact);
    grouped.set(fact.category,items);
  }

  const supplemental = [];
  for (const [category,title,icon,hint] of categories) {
    const items = grouped.get(category);
    if (items?.length && !present.has(category)) {
      present.add(category);
      supplemental.push(card(category,title,icon,hint,items.map(renderFact).join(""),opened));
    }
  }

  return [card("check","경기 체크","✓","대진·시간·자료 확인",fixtureCheck(match,round,context,present),opened), ...supplemental];
}

const contextEndpoint = ["localhost","127.0.0.1"].includes(location.hostname)
  ? "/api/context" : "https://matchindex-round-api.onrender.com/api/context";

export async function fetchAutomaticContext(roundId) {
  const request = await fetch(`${contextEndpoint}?round=${roundId}`, {signal:AbortSignal.timeout(18_000)});
  if (request.status === 202) return null;
  if (!request.ok) throw new Error("Match context unavailable");
  const data = await request.json();
  if (data.roundId !== roundId || !data.contexts || !Number.isFinite(Date.parse(data.updatedAt))) {
    throw new Error("Invalid match context");
  }
  return data;
}

export function renderOutlook(outlook, cancelled = false) {
  if (cancelled) return "";
  if (!outlook?.headline) return `<section class="outlook-box"><p class="outlook-label">경기 전망</p>
    <p class="outlook-line">현재 확인된 자료로는 득점 전망을 내기 어렵습니다</p></section>`;
  return `<section class="outlook-box">
    <p class="outlook-label">${outlook.kind === "model" ? "경기 전망" : "베트맨 배당 참고"}${outlook.archived ? " · 경기 전 기록 기준" : ""}</p>
    <p class="outlook-line">${escape(outlook.headline)}</p>
    ${outlook.range ? `<p class="outlook-range">예상 범위 ${escape(outlook.range)}</p>` : ""}
    <p class="outlook-basis">${escape(outlook.basis)}</p>
    ${outlook.weather ? `<p class="outlook-basis"><strong>날씨 변수</strong> ${escape(outlook.weather)}</p>` : ""}
    ${sourceLink(outlook.source)}
  </section>`;
}
