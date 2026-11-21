const mascotFiles = {
  standing: new URL("./assets/mascot/sun-moon-standing.png", import.meta.url).href,
  running: new URL("./assets/mascot/sun-moon-running.png", import.meta.url).href,
  resting: new URL("./assets/mascot/sun-moon-resting.png", import.meta.url).href
};
const conditions = {
  calm:"평온한 예보", rain:"비", wind:"강한 바람", fog:"안개", frost:"낮은 기온", heat:"더위",
  indoor:"실내", roof:"지붕 개폐 미확인", unknown:"예보 자료 미확인"
};
const conditionWords = {
  calm:"평온", rain:"비", wind:"강풍", fog:"안개", frost:"영하", heat:"더위", indoor:"실내", roof:"지붕", unknown:"미확인"
};
const impactLevels = {
  low:["영향 작음",1], watch:["영향 주의",2], high:["영향 큼",3], unknown:["영향 판단 보류",0]
};
const chars = {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};

function escape(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => chars[char]);
}

export function scoringPose(outlook) {
  if (outlook?.kind !== "model") return "standing";
  if (Object.hasOwn(mascotFiles, outlook.pose)) return outlook.pose;
  // Older round snapshots can stay visible while their refreshed data is collected.
  if (outlook.headline?.includes("오버 쪽으로")) return "running";
  if (outlook.headline?.includes("언더 쪽으로")) return "resting";
  return "standing";
}

export function mascotArt(pose = "standing", small = false) {
  const src = mascotFiles[pose] ?? mascotFiles.standing;
  if (small) return `<img class="mascot-icon" src="${src}" alt="" width="30" height="30" loading="lazy" decoding="async">`;
  return `<span class="mascot-art" data-pose="${pose}" style="--mascot-image:url('${src}')" aria-hidden="true">
    <img src="${src}" alt="" width="120" height="120" loading="lazy" decoding="async">
  </span>`;
}

export function scoringWord(outlook, pose) {
  if (pose === "running") return "오버";
  if (pose === "resting") return "언더";
  if (outlook?.kind === "market") return "참고";
  if (outlook?.headline?.includes("팽팽합니다")) return "균형";
  return outlook?.headline ? "예상" : "미정";
}

export function mascotFigure(word, pose = "standing") {
  return `<div class="mascot-figure">${mascotArt(pose)}<span class="mascot-word">${escape(word)}</span></div>`;
}

export function weatherVisual(fact) {
  if (Object.hasOwn(conditions, fact?.visual?.condition) && Object.hasOwn(impactLevels, fact.visual.impact)) return fact.visual;
  if (fact?.title === "실내 경기 환경" || fact?.title === "돔 구장 환경") return {condition:"indoor",impact:"low"};
  if (fact?.title === "경기장 지붕" || fact?.value === "지붕이 열리는지 먼저 확인") return {condition:"roof",impact:"unknown"};
  const tag = fact?.forecastTag;
  if (tag && Object.hasOwn(conditions,tag)) return {condition:tag,impact:"watch"};
  if (fact?.value === "도시 예보에서 두드러진 날씨 신호 없음") return {condition:"calm",impact:"low"};
  return {condition:"unknown",impact:"unknown"};
}

export function curatedWeatherVisual(game) {
  if (game?.weather?.[0] === "실내") return {condition:"indoor",impact:"low"};
  if (game?.weatherAssessment?.tone === "check") return {condition:"fog",impact:"watch",label:"영하권 · 옅은 안개"};
  if (game?.weatherAssessment) return {condition:"calm",impact:"low"};
  return {condition:"unknown",impact:"unknown"};
}

export function weatherHint(visual) {
  const condition = conditions[visual?.condition] ?? conditions.unknown;
  const [level] = impactLevels[visual?.impact] ?? impactLevels.unknown;
  return `${visual?.label ?? condition} · ${level}`;
}

export function weatherPanel(visual) {
  const [level,lit] = impactLevels[visual?.impact] ?? impactLevels.unknown;
  const bars = [1,2,3].map(step => `<i${step <= lit ? ' class="lit"' : ""}></i>`).join("");
  const readings = Array.isArray(visual?.readings) ? visual.readings : [];
  return `<div class="weather-visual" data-impact="${lit}" data-condition="${escape(visual?.condition ?? "unknown")}">
    ${mascotFigure(conditionWords[visual?.condition] ?? conditionWords.unknown)}
    <div class="weather-visual-text">
      <span class="weather-visual-label">${escape(visual?.label ?? conditions[visual?.condition] ?? conditions.unknown)}</span>
      <div class="weather-impact"><strong>${level}</strong><span class="weather-impact-bars" aria-hidden="true">${bars}</span></div>
      ${readings.length ? `<dl class="weather-observations">${readings.map(({label,value})=>`<div><dt>${escape(label)}</dt><dd>${escape(value)}</dd></div>`).join("")}</dl>` : ""}
    </div>
  </div>`;
}
