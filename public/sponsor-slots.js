import { escapeHtml, isSource } from "./source-links.js";

// Add a contracted sponsor with {name, image, url} to the applicable placement.
const creatives = {};

const placements = {
  feed: {label:"모바일 · 세 번째 경기 뒤",width:320,height:100},
  rail: {label:"PC · 경기 목록 오른쪽",width:300,height:250},
  detail: {label:"상세 분석 · 카드 아래",width:320,height:100}
};

export function sponsorSlot(placement, preview) {
  const {label,width,height} = placements[placement];
  const creative = creatives[placement];
  const ready = creative?.name && isSource([creative.name,creative.url]) &&
    /^assets\/sponsors\/[a-z0-9_-]+\.(avif|jpe?g|png|webp)$/i.test(creative.image);
  if (!preview && !ready) return "";

  return `<aside class="sponsor-slot sponsor-${placement}" data-sponsor-placement="${placement}" aria-label="${preview ? "광고 위치 미리보기" : "광고"}">
    <span class="sponsor-disclosure">${preview ? "광고 위치 미리보기" : "광고"}</span>
    ${preview
      ? `<div class="sponsor-preview"><strong>${label}</strong><span>${width} × ${height}</span></div>`
      : `<a class="sponsor-creative" href="${escapeHtml(creative.url)}" target="_blank" rel="sponsored noopener noreferrer">
          <img src="${escapeHtml(creative.image)}" alt="${escapeHtml(creative.name)}" width="${width}" height="${height}" loading="lazy" decoding="async">
        </a>`}
  </aside>`;
}
