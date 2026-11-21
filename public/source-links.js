const directRecords = new Map([
  ["/game/cha-vs-atl-0022600043",["NBA 공식 경기 기록","https://statsdmz.nba.com/pdfs/20261120/20261120_CHAATL.pdf"]],
  ["/hawks/game/0022600043-hornets-vs-hawks-atlanta-ga-11-20-2026/event-details",["NBA 공식 경기 기록","https://statsdmz.nba.com/pdfs/20261120/20261120_CHAATL.pdf"]],
  ["/hornets/news/hornets-strong-start-fizzles-out-in-2nd-half-against-atlanta",["같은 경기 기록 · ESPN","https://www.espn.com/nba/game/_/gameId/401909305"]],
  ["/grizzlies/news/grizzlies-outlast-cavaliers-124121-for-franchise-record-eighth-straight-road-win",["같은 경기 공식 기록","https://statsdmz.nba.com/pdfs/20261118/20261118_MEMCLE.pdf"]],
  ["/game/0022600275",["같은 경기 기록 · Knickstats","https://knickstats.com/games/2026-11-21-portland/"]]
]);
const teamSchedules = {
  "1610612742": "dal/dallas-mavericks",
  "1610612746": "lac/la-clippers",
  "1610612749": "mil/milwaukee-bucks",
  "1610612750": "min/minnesota-timberwolves",
  "1610612752": "ny/new-york-knicks",
  "1610612755": "phi/philadelphia-76ers",
  "1610612757": "por/portland-trail-blazers",
  "1610612759": "sa/san-antonio-spurs"
};
for (const [id,path] of Object.entries(teamSchedules)) {
  directRecords.set(`/team/${id}/schedule`,["같은 팀 경기 일정과 결과 · ESPN",`https://www.espn.com/nba/team/schedule/_/name/${path}`]);
}
directRecords.set("/timberwolves/schedule",directRecords.get("/team/1610612750/schedule"));

const limited = new Set([
  "official.nba.com/comments-on-the-rules/",
  "support.pinnacle.com/hc/en-us/articles/42376048557073-What-is-a-betting-margin",
  "support.pinnacle.bet/hc/en-us/articles/42376048557073-What-is-a-betting-margin",
  "help.bet365.com/s/en-ch/sportsrules/soccer/result-event-half-time"
]);
const textChars = {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => textChars[char]);
}

function addressOf(pair) {
  if (!Array.isArray(pair) || typeof pair[0] !== "string" || typeof pair[1] !== "string") return null;
  try {
    const url = new URL(pair[1]);
    return url.protocol === "https:" && !url.username && !url.password ? url : null;
  } catch { return null; }
}

export function isSource(pair) {
  return Boolean(addressOf(pair));
}

function technicalSource(url) {
  const {hostname,pathname:path} = url;
  return (hostname === "github.com" && /^\/(openfootball\/football\.json|sportsdataverse\/sportsdataverse-data)(\/|$)/.test(path))
    || hostname === "raw.githubusercontent.com"
    || (hostname === "api.openligadb.de" && path.startsWith("/getmatchdata/"))
    || (hostname === "api.met.no" && /\/(compact|complete)$/.test(path));
}

function anchor(label, href) {
  return `<a class="source" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
}

export function sourceCredit(pair) {
  const label = Array.isArray(pair) ? pair[0] : null;
  return typeof label === "string" && label.trim() ? `<span class="source-credit">${escapeHtml(label)}</span>` : "";
}

export function sourceLink(pair) {
  const url = addressOf(pair);
  if (!url) return "";
  const [label] = pair;
  const key = url.hostname + url.pathname;
  const nbaRestricted = url.hostname === "www.nba.com" &&
    /^\/(?:team\/|game\/|[^/]+\/(?:game\/|news\/|schedule$))/.test(url.pathname);
  if (limited.has(key) || nbaRestricted) {
    const related = nbaRestricted ? directRecords.get(url.pathname) : null;
    return `<span class="source-credit">${escapeHtml(label)} · 원문 접속 제한</span>${related ? anchor(...related) : ""}`;
  }
  if (technicalSource(url)) return `<span class="source-credit">${escapeHtml(label)} · 자료 제공</span>`;
  return anchor(label,url.href);
}

export function sourceCredits(pairs) {
  const unique = new Map();
  for (const pair of pairs) {
    if (!isSource(pair)) continue;
    const address = addressOf(pair);
    // Multiple seasons from the same dataset share a credit when they have no public-facing link.
    const key = technicalSource(address) ? pair[0] : address.href;
    if (!unique.has(key)) unique.set(key,pair);
  }
  return [...unique.values()].map(sourceLink).join("");
}
