import { escapeHtml, sourceCredits } from "./source-links.js";
import { settledTotal, settledWinner } from "./match-settlement.js";

const units = {축구:"골", 농구:"점", 야구:"점", 배구:"세트"};
const sides = ["home","draw","away"];
const sideLabels = {home:"홈승", draw:"무승부", away:"원정승"};
const directions = {under:"언더", over:"오버"};
const numberPattern = "(\\d+(?:\\.\\d+)?)";

function validScore(score) {
  return Array.isArray(score) && score.length === 2 && score.every(value=>Number.isSafeInteger(value) && value >= 0);
}

function numeric(value) {
  return Number.isFinite(value) && value >= 0;
}

function scopeOf(match) {
  return match.voided ? null : validScore(match.score) ? "official"
    : match.live?.state === "final" && validScore(match.live.score) ? "external" : null;
}

function scoringProjection(outlook, unit) {
  if (outlook?.kind !== "model") return null;
  const projection = outlook.projection;
  if (projection?.unit === unit && numeric(projection.expectedTotal)) return projection;
  // Older saved contexts contain model values in their generated labels.
  const headline = outlook.headline ?? "";
  const expected = new RegExp("(?:예상 합계 |^합계 )"+numberPattern+unit).exec(headline);
  const range = new RegExp("^"+numberPattern+"[–-]"+numberPattern+unit+"$").exec(outlook.range ?? "");
  const side = new RegExp("^"+numberPattern+unit+" (언더|오버) 쪽으로 ").exec(headline);
  const sets = unit === "세트" ? /^(\d+)세트 안팎 이어질 경기$/.exec(headline) : null;
  if (!expected && !sets && !range && !side) return null;
  return {
    expectedTotal:expected ? Number(expected[1]) : sets ? Number(sets[1]) : undefined,
    range:range?.slice(1).map(Number),
    line:side ? Number(side[1]) : undefined,
    direction:side?.[2] === "언더" ? "under" : side?.[2] === "오버" ? "over" : undefined
  };
}

function resultProjection(outlook, match) {
  const result = outlook?.result;
  const outcomes = Array.isArray(result?.outcomes) ? result.outcomes : [];
  if (outcomes.length >= 2 && outcomes.every(entry=>sides.includes(entry?.side) &&
      Number.isInteger(entry.percent) && entry.percent >= 0 && entry.percent <= 100) &&
      new Set(outcomes.map(entry=>entry.side)).size === outcomes.length &&
      outcomes.reduce((sum, entry)=>sum + entry.percent,0) === 100) {
    const [first,second] = [...outcomes].sort((a,b)=>b.percent-a.percent);
    const market = result.label === "베트맨 배당 환산";
    const lead = first.percent - second.percent >= 5 ? first.side : null;
    return {
      market, lead,
      message:lead ? `${sideLabels[lead]} 쪽 ${market ? "배당상 우세" : "우세 예상"} (${first.percent}%)`
        : market ? "배당상 뚜렷하게 앞선 선택 없음" : "승부가 팽팽할 것으로 예상"
    };
  }
  if (!Array.isArray(match.odds) || match.odds.length !== sides.length) return null;
  const offered = match.odds.map((price,i)=>({price,side:sides[i]}))
    .filter(entry=>Number.isFinite(entry.price) && entry.price > 1)
    .sort((a,b)=>a.price-b.price);
  const [first,second] = offered;
  if (!second || (match.sport === "축구" && offered.length !== 3)) return null;
  const lead = first.price < second.price ? first.side : null;
  return {market:true,lead,message:lead ? `${sideLabels[lead]} 배당이 가장 낮았음 (${first.price.toFixed(2)})` : "베트맨 최저 배당이 같았음"};
}

function scoreForecast(outlook, projection, unit) {
  if (projection) {
    const {expectedTotal,range,line,direction} = projection;
    return [
      numeric(expectedTotal) ? `예상 합계 ${expectedTotal}${unit}` : "",
      Array.isArray(range) && range.length === 2 && range.every(numeric) && range[0] <= range[1]
        ? `범위 ${range[0]}–${range[1]}${unit}` : "",
      Number.isFinite(line) && line > 0 && Object.hasOwn(directions,direction) ? `${line}${unit} 기준 ${directions[direction]} 예상`
        : Number.isFinite(line) && line > 0 && direction === "neutral" ? `${line}${unit} 기준 언더·오버 접전` : ""
    ].filter(Boolean);
  }
  if (outlook?.kind === "market") {
    const odds = new RegExp("^베트맨 기준 "+numberPattern+"(골|점|세트) · (언더|오버) 쪽 배당이 낮습니다$").exec(outlook.headline ?? "");
    if (odds) return [`${odds[1]}${odds[2]} 기준 ${odds[3]} 배당이 낮았음`];
  }
  return [];
}

function totalUnit(match, unit) {
  return match.sport === "배구" && match.total?.line >= 6 ? "점" : unit;
}

function comparisonRows({match, projection, forecast, winner, total, points, unit}) {
  const rows = [];
  const metric = unit === "세트" ? "세트" : "득점";
  if (forecast?.lead && winner) {
    const agrees = forecast.lead === winner;
    const first = forecast.market ? "배당상 앞섰던 선택과" : "우세 전망과";
    rows.push(["승부", agrees ? "same" : "different", `${first} 실제 결과가 ${agrees ? "일치했습니다." : "달랐습니다."}`]);
  }
  if (projection && Number.isFinite(projection.line) && projection.line > 0 &&
      Object.hasOwn(directions,projection.direction)) {
    const sameMarket = projection.line === match.total?.line && totalUnit(match,unit) === unit;
    const actualPoints = sameMarket && numeric(total?.points) ? total.points : points;
    if (sameMarket && match.total?.status === "void") return rows;
    const actual = (sameMarket ? total?.outcome : null) ??
      (actualPoints === projection.line ? null : actualPoints < projection.line ? "under" : "over");
    if (actual) {
      const agrees = actual === projection.direction;
      rows.push([metric, agrees ? "same" : "different", `${projection.line}${unit} 기준 ${directions[projection.direction]}를 예상했고, 실제는 ${directions[actual]}였습니다.`]);
    } else {
      rows.push([metric,"neutral",`최종 합계가 전망 기준점 ${projection.line}${unit}과 같았습니다.`]);
    }
  } else if (Array.isArray(projection?.range) && projection.range.length === 2 &&
      projection.range.every(numeric) && projection.range[0] <= projection.range[1]) {
    const [low,high] = projection.range;
    const position = points < low ? "low" : points > high ? "high" : "in";
    rows.push([metric,position === "in" ? "same" : "different",
      position === "in" ? "최종 합계가 예상 범위 안에 들었습니다."
        : `최종 합계가 예상 범위보다 ${position === "low" ? "낮았습니다." : "높았습니다."}`]);
  }
  return rows;
}

function footballFlow(match, stats, score) {
  if (match.sport !== "축구" || stats?.state !== "finished" || stats.periods?.length !== 2) return "";
  const first = stats.periods.find(period=>period?.label === "전반");
  const second = stats.periods.find(period=>period?.label === "후반");
  if (!first || !second || !validScore([first.home,first.away]) || !validScore([second.home,second.away]) ||
      first.home + second.home !== score[0] || first.away + second.away !== score[1]) return "";
  const halftime = Math.sign(first.home-first.away);
  const final = Math.sign(score[0]-score[1]);
  const change = halftime && final === -halftime ? "후반에 승부가 뒤집혔습니다."
    : halftime && !final ? "전반의 점수 차가 후반에 사라졌습니다."
    : !halftime && final ? "전반 동점 뒤 후반에 승부가 갈렸습니다." : "";
  return `전반 ${first.home}:${first.away} · 후반 ${second.home}:${second.away}${change ? ` · ${change}` : ""}`;
}

export function renderPostMatchReview(match, outlook, {historyHref = "", source, stats} = {}) {
  const scope = scopeOf(match);
  const unit = units[match.sport];
  if (!scope || !unit) return "";
  const official = scope === "official";
  const score = official ? match.score : match.live.score;
  const points = score[0] + score[1];
  const winner = official ? settledWinner(match) : null;
  const scoreSide = score[0] === score[1] ? "draw" : score[0] > score[1] ? "home" : "away";
  const actual = official ? (scoreSide === "draw" ? "무승부" : `${match[scoreSide]} 승`)
    : scoreSide === "draw" ? "외부 종료 점수 동률" : `외부 점수상 ${match[scoreSide]} 앞섬`;
  // A final score from a secondary source can include extra time or another settlement scope.
  const total = official ? settledTotal(match) : null;
  const projection = scoringProjection(outlook, unit);
  const forecast = resultProjection(outlook, match);
  const scoring = scoreForecast(outlook, projection, unit);
  const hasForecast = Boolean(forecast || scoring.length);
  const captured = Date.parse(outlook?.capturedAt);
  const recorded = Number.isFinite(captured) && captured < Date.parse(match.startsAt);
  const provenance = recorded && hasForecast ? "경기 전 저장 전망"
    : projection || (outlook?.result && forecast && !forecast.market) ? "경기 전 기록으로 재구성"
    : hasForecast ? "베트맨 공개 배당 참고" : "";
  const rows = official ? comparisonRows({match, projection, forecast, winner, total, points, unit}) : [];
  const flow = official ? footballFlow(match,stats,score) : "";
  if (flow) rows.unshift(["경기 흐름","neutral",flow]);
  const totalsLine = total?.outcome ? `프로토 ${match.total.line}${totalUnit(match,unit)} 기준 ${directions[total.outcome]}`
    + (numeric(total.points) && (total.points !== points || totalUnit(match,unit) !== unit) ? ` · 합계 ${total.points}${totalUnit(match,unit)}` : "") : "";
  const officialSource = typeof source === "string" ? ["베트맨 · 확정 결과",source] : source;
  const links = sourceCredits([official ? officialSource : match.live?.source, outlook?.source, outlook?.result?.source]);
  return `<section class="post-match-review" data-result-source="${scope}" aria-label="경기 복기">
    <div class="post-match-review-head"><h4>경기 복기</h4>
      <span>${official ? "베트맨 확정 결과" : "외부 종료 기록 · 베트맨 확인 중"}</span></div>
    <div class="post-match-comparison">
      <div class="post-match-before">
        <h5>경기 전 전망</h5>
        ${provenance ? `<small>${provenance}</small>` : ""}
        ${forecast ? `<p>${escapeHtml(forecast.message)}</p>` : ""}
        ${scoring.length ? `<p>${escapeHtml(scoring.join(" · "))}</p>` : ""}
        ${!hasForecast ? "<p>확인된 경기 전 전망 없음</p>" : ""}
      </div>
      <div class="post-match-actual">
        <h5>실제 결과</h5>
        <strong class="post-match-score">${score.join(" : ")}</strong>
        <p>${actual ? `${escapeHtml(actual)} · ` : ""}합계 ${points}${unit}</p>
        ${totalsLine ? `<p>${escapeHtml(totalsLine)}</p>` : ""}
      </div>
    </div>
    ${rows.length ? `<ul class="post-match-deltas">${rows.map(([label,status,message])=>`<li data-verdict="${status}"><strong>${label}</strong><span>${escapeHtml(message)}</span></li>`).join("")}</ul>` : ""}
    ${links || historyHref ? `<div class="post-match-links">${links}${historyHref ? `<a class="history-shortcut" href="${escapeHtml(historyHref)}">경기 이력 보기</a>` : ""}</div>` : ""}
  </section>`;
}
