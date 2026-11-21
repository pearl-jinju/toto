import { escapeHtml } from "./source-links.js";

function soccerMinute(live) {
  if (Number.isInteger(live.elapsedMinutes)) return live.elapsedMinutes;
  const display = /^([0-9]{1,3})(?:\+([0-9]{1,2}))?\s*(?:['′분])?$/.exec(live.clock ?? "");
  return display ? Number(display[1]) + Number(display[2] ?? 0) : null;
}

function readState(sport, side, gap, live) {
  if (sport === "축구") {
    const minute = soccerMinute(live);
    if (minute !== null && minute >= 75) {
      if (!side) return ["후반 막판 동점", "한 골로 리드가 바뀌는 상황입니다."];
      if (gap === 1) return [`${side} 1골 차 리드`, "뒤진 팀이 공격에 인원을 더 보내면, 리드한 팀에는 역습 공간이 열릴 수 있습니다."];
      return [`${side} ${gap}골 차 리드`, `경기 막판에 뒤진 팀이 따라붙으려면 최소 ${gap}골이 필요합니다.`];
    }
    return side ? [`${side} ${gap}골 차 리드`, gap === 1 ? "뒤진 팀이 한 골을 넣으면 다시 동점입니다." : "다음 득점이 두 팀의 경기 운영을 바꿀 수 있습니다."] : ["현재 동점", "어느 쪽이 먼저 리드를 잡는지가 남은 경기 흐름의 변수입니다."];
  }
  if (sport === "농구") {
    if (!side) return ["현재 동점", "다음 공격에서 득점을 올리는 팀이 앞섭니다."];
    const message = gap === 3 ? "뒤진 팀은 3점슛 한 번으로 따라붙을 수 있습니다."
      : gap < 3 ? "한 번의 공격으로 동점이나 역전이 가능한 점수 차입니다."
      : gap <= 6 ? "뒤진 팀은 보통 두 번 이상의 공격이 필요합니다."
      : "뒤진 팀에는 득점과 함께 연속으로 상대 공격을 막는 일이 중요합니다.";
    return [`${side} ${gap}점 차 리드`, message];
  }
  if (sport === "야구") {
    if (!side) return ["현재 동점", "다음 득점이 리드를 만듭니다."];
    return [`${side} ${gap}점 차 리드`, gap === 1 ? "추격 팀이 한 점을 내면 동점입니다. 공격 기회를 이어갈 출루가 중요합니다." : `추격 팀은 최소 ${gap}점을 보태야 동점입니다.`];
  }
  if (sport === "배구") {
    return side ? [`${side} ${gap}세트 차 리드`, "세트 전적 기준입니다. 진행 중인 세트의 개별 득점은 별도로 확인해야 합니다."] : ["세트 동률", "다음 세트를 따내는 팀이 다시 앞섭니다."];
  }
  return null;
}

function totalRead(match, live, total) {
  const line = match.total?.line;
  const unit = {축구:"골", 농구:"점", 야구:"점"}[match.sport];
  if (!unit || match.total?.status === "void" || !Number.isFinite(line) || line <= 0 || /연장|승부차기/.test(live.period ?? "")) return "";
  const remaining = Math.floor(line)+1-total;
  return remaining > 0
    ? `현재 합계 ${total}${unit}. ${remaining}${unit} 더 나오면 프로토 기준 ${line}${unit}을 넘습니다.`
    : `현재 합계 ${total}${unit}로 프로토 기준 ${line}${unit}을 넘었습니다.`;
}

export function renderLiveAnalysis(match, live) {
  if (live?.state !== "live" || !Array.isArray(live.score) || live.score.length !== 2 ||
      !live.score.every(value=>Number.isInteger(value) && value>=0)) return "";
  const [home,away] = live.score;
  const side = home === away ? "" : home > away ? match.home : match.away;
  const situation = readState(match.sport, side, Math.abs(home-away), live);
  if (!situation) return "";
  const [headline,comment] = situation;
  const criterion = totalRead(match,live,home+away);
  return `<section class="live-interpretation" aria-label="경기 중 분석">
    <span class="live-interpretation-label">경기 중 분석</span>
    <p><strong>${escapeHtml(headline)}</strong> ${escapeHtml(comment)}</p>
    ${criterion ? `<p class="live-interpretation-total">${escapeHtml(criterion)}</p>` : ""}
  </section>`;
}
