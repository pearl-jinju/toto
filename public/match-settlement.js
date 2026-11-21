const winners = ["home","draw","away"];

function officialScore(score) {
  return Array.isArray(score) && score.length === 2 &&
    score.every(value=>Number.isSafeInteger(value) && value >= 0);
}

export function settledWinner(match) {
  if (match.voided || !officialScore(match.score)) return null;
  if (Object.hasOwn(match,"outcome")) return winners.includes(match.outcome) ? match.outcome : null;
  // Older Betman snapshots carry the confirmed ordinary score but no outcome field.
  if (match.saleStatus !== "settled") return null;
  const [home,away] = match.score;
  return home === away ? "draw" : home > away ? "home" : "away";
}

export function settledTotal(match) {
  const market = match.total;
  if (match.voided || market?.status !== "settled") return null;
  return {
    outcome:["under","over"].includes(market.outcome) ? market.outcome : null,
    points:Number.isSafeInteger(market.points) && market.points >= 0 ? market.points : null
  };
}
