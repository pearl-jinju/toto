import { isSource } from "./source-links.js";

const liveApi = ["localhost","127.0.0.1"].includes(location.hostname)
  ? "/api/live" : "https://matchindex-round-api.onrender.com/api/live";
const maxCurrentAge = 180_000;
const maxClockSkew = 30_000;
const knownStates = new Set(["live","final","delayed","postponed","scheduled"]);

function parsedTime(value) {
  return typeof value === "string" && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? Date.parse(value) : NaN;
}

function compactText(value) {
  return typeof value === "string" ? value.trim().slice(0,32) : "";
}

export async function fetchLiveRound(roundId) {
  const response = await fetch(`${liveApi}?round=${roundId}`, {signal:AbortSignal.timeout(14_000),cache:"no-store"});
  if (!response.ok) throw new Error("Live scores unavailable");
  const packet = await response.json();
  const updatedAt = parsedTime(packet?.updatedAt);
  if (packet?.roundId !== roundId || !Number.isFinite(updatedAt) || updatedAt > Date.now() + maxClockSkew ||
      !packet.fixtures || typeof packet.fixtures !== "object" || Array.isArray(packet.fixtures)) {
    throw new Error("Invalid live score packet");
  }
  return {roundId, updatedAt, fixtures:packet.fixtures};
}

export function withLiveScores(match, packet, now = Date.now()) {
  if (!match || !packet || match.score || match.voided) return match;
  const entry = Object.hasOwn(packet.fixtures, match.number) ? packet.fixtures[match.number] : null;
  if (!entry || entry.home !== match.home || entry.away !== match.away || entry.startsAt !== match.startsAt ||
      !knownStates.has(entry.state) || !isSource(entry.source)) return match;
  const observedAt = parsedTime(entry.observedAt);
  const final = entry.state === "final";
  if (!Number.isFinite(observedAt) || observedAt > now + maxClockSkew || observedAt > packet.updatedAt + maxClockSkew ||
      (!final && now - Math.min(observedAt,packet.updatedAt) > maxCurrentAge)) return match;
  if (["live","final"].includes(entry.state) && Date.parse(match.startsAt) > Math.min(now,observedAt + maxClockSkew)) return match;
  const score = ["live","final"].includes(entry.state) && Array.isArray(entry.score) &&
    entry.score.length === 2 && entry.score.every(value=>Number.isSafeInteger(value) && value >= 0 && value < 10_000)
    ? entry.score : null;
  if (entry.state === "final" && !score) return match;
  return {...match,live:{
    state:entry.state, score,
    period:compactText(entry.period), clock:compactText(entry.clock),
    elapsedMinutes:Number.isInteger(entry.elapsedMinutes) && entry.elapsedMinutes >= 0 && entry.elapsedMinutes <= 180
      ? entry.elapsedMinutes : null,
    observedAt:entry.observedAt, source:entry.source
  }};
}

export function liveClock(live) {
  return live?.state === "live" ? [live.period,live.clock].filter(Boolean).join(" ") : "";
}

export function matchScore(match) {
  return match.voided ? null : match.score ?? match.live?.score ?? null;
}

export function matchStatus(match, now = Date.now()) {
  if (match.voided) return ["void","취소"];
  if (match.score || match.live?.state === "final") return ["done","종료"];
  if (match.live?.state === "live") return ["live","진행 중"];
  if (match.live?.state === "postponed") return ["postponed","연기"];
  if (match.live?.state === "delayed") return ["delayed","지연"];
  if (Date.parse(match.startsAt) <= now) {
    return match.live?.state === "scheduled" ? ["waiting","시작 대기"] : ["pending","결과 대기"];
  }
  return ["next","예정"];
}
