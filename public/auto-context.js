import { escapeHtml as escape, isSource, sourceCredit, sourceCredits, sourceLink } from "./source-links.js";
import { mascotFigure, scoringPose, scoringWord, weatherHint, weatherPanel, weatherVisual } from "./match-visuals.js";

const displayDate = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "long",
  day: "numeric",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});
const categories = [
  ["venue","구장 세부","◎","경기장과 시설"],
  ["weather","경기 환경","","예보와 경기 중 볼 점"],
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

function forecastBasis(fact) {
  if (fact.forecastBasis?.city) return fact.forecastBasis;
  try {
    const url = new URL(fact.source?.[1]);
    const city = fact.title?.match(/^(.*) 도심 경기 시간대 예보$/)?.[1];
    if (url.hostname !== "api.met.no" || !city) return null;
    const lat = url.searchParams.get("lat");
    const lon = url.searchParams.get("lon");
    return {city, latitude:lat === null ? null : Number(lat), longitude:lon === null ? null : Number(lon), validAt:fact.date};
  } catch { return null; }
}

function formatCoordinates(latitude,longitude) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude)>90 || Math.abs(longitude)>180) return "";
  const coordinate = (value,positive,negative) => `${Math.abs(value).toFixed(2)}°${value < 0 ? negative : positive}`;
  return `${coordinate(latitude,"N","S")}, ${coordinate(longitude,"E","W")}`;
}

function renderForecastBasis(basis) {
  if (!basis) return "";
  return `<dl class="weather-source-details">
    ${renderLine("예보 위치",`${basis.city} 도심 대표 지점`)}
    ${renderLine("대표 좌표",formatCoordinates(basis.latitude,basis.longitude))}
    ${renderLine("예보 대상 시각",basis.validAt ? `${formatDate(basis.validAt)} · 한국 시간` : "")}
    ${renderLine("예보 발표 시각",basis.issuedAt ? `${formatDate(basis.issuedAt)} · 한국 시간` : "")}
  </dl>`;
}

function renderFact(fact) {
  const {title, value, text, date, source, reference} = fact;
  if (fact.category === "weather") {
    const basis = forecastBasis(fact);
    return `<section class="context-item">
      ${weatherPanel(weatherVisual(fact))}
      ${basis ? `<p class="weather-origin"><strong>${escape(basis.city)} 도심 기준</strong> <span>노르웨이 기상청(MET Norway) · 경기 시간대 예보</span></p>` : ""}
      <p class="weather-explanation">${escape(value ?? title)}</p>
      <details class="weather-evidence"><summary>${basis ? "예보 시각·기준 위치" : "환경 해석과 출처"}</summary>
        ${renderForecastBasis(basis)}
        <p>${escape(text)}</p>
        ${basis ? '<p class="context-basis">도심 대표 지점의 예보입니다. 경기장 잔디나 관중석에서 측정한 값은 확인되지 않았습니다.</p>' : ""}
        ${!basis && date ? `<p class="context-basis">${escape(formatDate(date))} 기준</p>` : ""}
        ${sourceCredit(source)}${sourceCredit(reference)}
      </details>
    </section>`;
  }
  if (fact.category === "venue" && Array.isArray(fact.venueFacts)) {
    return `<section class="context-item venue-profile">
      <h4>${escape(value ?? title)}</h4>
      <dl class="venue-features">
        ${fact.venueFacts.map(([label,detail])=>renderLine(escape(label),detail)).join("")}
      </dl>
      <details class="context-evidence"><summary>구장 자료 출처</summary>
        ${sourceCredits([source,...(fact.venueReferences ?? [])])}
      </details>
    </section>`;
  }
  const original = Array.isArray(fact.originalNames) ? fact.originalNames : [fact.originalName];
  const names = original.filter(name => typeof name === "string" && name.trim());
  return `<section class="context-item">
    ${fact.category === "players" || value == null || value === ""
      ? `<h4>${escape(title)}</h4>${value ? `<p class="context-number">${escape(value)}</p>` : ""}`
      : `<h4 class="context-number">${escape(value)}</h4><p class="context-basis">${escape(title)}</p>`}
    ${renderInterpretation(fact.insight,true)}
    ${text ? `<p>${escape(text)}</p>` : ""}
    ${date ? `<p class="context-basis">${escape(formatDate(date))}</p>` : ""}
    ${names.length ? `<details class="weather-evidence"><summary>선수 이름 원문</summary><p>${names.map(escape).join(" · ")}</p></details>` : ""}
    ${sourceLink(source)}${sourceLink(reference)}
    </section>`;
}

function analysisLine(lead, body, className) {
  return `<p class="${className}"><strong class="analysis-keyword">${escape(lead)}</strong>${body ? ` <span>${escape(body)}</span>` : ""}</p>`;
}

function renderInterpretation(read, detail = false) {
  if (!read?.headline || !read.explanation) return "";
  const line = analysisLine(read.headline, read.explanation, "outlook-angle");
  if (!detail) return line;
  return `<div class="match-interpretation">${line}
    ${read.watch ? analysisLine("중계에서 볼 점", read.watch, "interpretation-watch") : ""}
  </div>`;
}

export function outlookInterpretations(context) {
  const factors = Array.isArray(context?.factors) ? context.factors : [];
  const playerRead = factors.find(fact => fact?.category === "players" && fact.insight)?.insight;
  return [context?.weatherRead, context?.scheduleRead, playerRead];
}

export function renderMatchFlow(context, cancelled = false) {
  if (cancelled) return "";
  const preview = context?.flowPreview;
  const flow = preview ?? context?.outlook?.flow;
  const published = flow?.published ? flow.published.replaceAll("-", ".") : "";
  return `<section class="venue-flow">
    <span>경기 양상${context?.fixture?.status === "finished" ? " · 경기 전 자료 기준" : ""}</span>
    <h4 class="${flow?.headline ? "analysis-keyword" : ""}">${escape(flow?.headline ?? "득점 흐름을 비교할 경기 기록을 확인 중입니다.")}</h4>
    ${flow?.basis ? `<p>${escape(flow.basis)}</p>` : ""}
    ${published ? `<div class="venue-flow-source"><time datetime="${escape(flow.published)}">${escape(published)} 발표</time>${sourceLink(flow.source)}</div>` : ""}
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

export function weatherFacts(context) {
  const facts = Array.isArray(context?.factors) ? context.factors : [];
  const weather = facts.filter(fact => fact?.category === "weather" && fact.title && isSource(fact.source));
  if (weather.length) return weather;
  const roof = facts.find(fact => fact?.category === "venue" && weatherVisual(fact).condition === "roof" && isSource(fact.source));
  return roof ? [{...roof, category:"weather"}] : [];
}

export function renderWeatherFacts(context) {
  return renderInterpretation(context?.weatherRead,true) + weatherFacts(context).map(renderFact).join("");
}

export function automaticCards(match, round, context, existingIds, card, opened) {
  const present = new Set(existingIds);
  const facts = Array.isArray(context?.factors) ? context.factors : [];
  const grouped = new Map();
  for (const fact of facts) {
    if (!fact?.title || !isSource(fact.source)) continue;
    const items = grouped.get(fact.category) ?? [];
    items.push(fact);
    grouped.set(fact.category,items);
  }

  const supplemental = [];
  for (const [category,title,icon,hint] of categories) {
    const items = grouped.get(category);
    if (present.has(category)) continue;
    if (category === "weather") {
      const weather = weatherFacts(context);
      if (weather.length) present.add(category);
      const visual = weatherVisual(weather[0]);
      supplemental.push(card(category,title,icon,weatherHint(visual),weather.length ? renderWeatherFacts(context) : weatherPanel(visual),opened));
      continue;
    }
    const scheduleRead = category === "schedule" ? context?.scheduleRead : null;
    if (items?.length || scheduleRead) {
      present.add(category);
      const venue = category === "venue" ? items.find(fact=>Array.isArray(fact.venueFacts)) : null;
      const titleText = venue ? "구장 특징" : category === "venue" && items.every(fact=>fact.title==="개최 도시") ? "경기장 위치" : title;
      const hintText = venue ? venue.venueFacts.slice(0,2).map(([,value])=>value).join(" · ") : hint;
      const flow = category === "venue" ? renderMatchFlow(context,match.voided) : "";
      const reading = renderInterpretation(scheduleRead,true);
      supplemental.push(card(category,titleText,icon,hintText,flow + reading + (items ?? []).map(renderFact).join(""),opened));
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

function renderResult(result, archived) {
  const names = {home:"홈승",draw:"무승부",away:"원정승"};
  const outcomes = (result?.outcomes ?? []).filter(({side,percent})=>Object.hasOwn(names,side) &&
    Number.isInteger(percent) && percent >= 0 && percent <= 100);
  if (outcomes.length < 2) return "";
  return `<section class="result-outlook" aria-label="승부 전망">
    <p class="result-outlook-label"><strong>승부 전망</strong> <span>${escape(result.label)}${archived ? " · 경기 전 기록 기준" : ""}</span></p>
    ${analysisLine(result.headline,"","result-outlook-headline")}
    <ul class="result-outcomes">
      ${outcomes.map(({side,percent})=>`<li data-side="${side}"><span>${names[side]}</span><b>${percent}%</b></li>`).join("")}
    </ul>
  </section>`;
}

export function renderOutlook(outlook, cancelled = false, historyHref = "", {angle, interpretations = [], notes = [], extraEvidence = "", openEvidence = false} = {}) {
  if (cancelled) return "";
  const pose = scoringPose(outlook);
  const label = outlook?.kind === "market" ? "베트맨 배당 참고" : "경기 예상";
  const headline = outlook?.headline ?? "현재 확인된 자료로는 득점 전망을 내기 어렵습니다";
  const [lead, ...summary] = headline.split(" · ");
  const result = outlook?.result;
  const credits = sourceCredits([angle?.source,result?.source,outlook?.source,...(outlook?.evidence?.sources ?? [])]);
  const evidence = [
    result?.basis ? `<p class="outlook-basis"><strong>승부 전망</strong> ${escape(result.basis)}</p>` : "",
    angle?.basis ? `<p class="outlook-basis"><strong>${escape(angle.label)}</strong> ${escape(angle.basis)}</p>` : "",
    outlook?.basis ? `<p class="outlook-basis">${escape(outlook.basis)}</p>` : "",
    outlook?.weather ? `<p class="outlook-basis"><strong>날씨 변수</strong> ${escape(outlook.weather)}</p>` : "",
    ...notes.map(([title,body,source])=>`<p class="outlook-basis"><strong>${escape(title)}</strong> ${escape(body)} ${sourceLink(source)}</p>`)
  ].join("");
  return `<section class="outlook-box" data-pose="${pose}">
    ${renderResult(result,outlook?.archived)}
    ${outlook?.kind !== "result" ? `<div class="outlook-visual">
      ${mascotFigure(scoringWord(outlook,pose),pose)}
      <div class="outlook-main">
        <p class="outlook-label">${label}${outlook?.archived ? " · 경기 전 기록 기준" : ""}</p>
        ${analysisLine(lead, summary.length ? "· " + summary.join(" · ") : "", "outlook-line")}
        ${outlook?.range ? `<p class="outlook-range">예상 범위 ${escape(outlook.range)}</p>` : ""}
      </div>
    </div>` : ""}
    ${angle?.summary ? analysisLine(angle.label,angle.summary,"outlook-angle") : ""}
    ${interpretations.map(read => renderInterpretation(read)).join("")}
    <div class="outlook-links">
      ${historyHref ? `<a class="history-shortcut" href="${escape(historyHref)}">경기 이력 보기</a>` : ""}
    </div>
    ${evidence || extraEvidence || credits ? `<details class="outlook-evidence" data-keep-open="outlook-evidence"${openEvidence ? " open" : ""}>
      <summary>근거 펼치기</summary>
      <div class="context-body">${evidence}${extraEvidence}${credits ? `<div class="outlook-credits">${credits}</div>` : ""}</div>
    </details>` : ""}
  </section>`;
}
