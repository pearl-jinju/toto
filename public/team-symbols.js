import { teamSymbols } from "./team-symbols-data.js";
import { escapeHtml as escape } from "./source-links.js";

const nameKey = name => String(name ?? "").normalize("NFC").toLowerCase().replace(/\s+/g,"");
const symbols = new Map(Object.entries(teamSymbols).map(([name,mark])=>[nameKey(name),mark]));

export function teamLabel(name) {
  const mark = symbols.get(nameKey(name));
  const logo = mark ? `<img class="team-symbol${mark.url.includes("/monochrome/") ? " team-symbol-mono" : ""}" src="${escape(mark.url)}" alt="" width="22" height="22" loading="lazy" decoding="async">` : "";
  return `<strong class="team-label">${logo}<span>${escape(name)}</span></strong>`;
}

export function teamSymbolSources(...teams) {
  const sources = new Map();
  for (const name of teams) {
    const source = symbols.get(nameKey(name))?.source;
    if (source && !sources.has(source)) sources.set(source,`${name} 엠블럼`);
  }
  return [...sources].map(([url,label])=>[label,url]);
}

export function hideBrokenTeamSymbols(root) {
  root.addEventListener("error",event=>{
    if (event.target.matches?.("img.team-symbol")) event.target.hidden = true;
  },true);
}
