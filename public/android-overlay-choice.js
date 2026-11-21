export function androidOverlayIntent(location) {
  const fallback = new URL(location.href);
  fallback.searchParams.set("overlay", "android");
  return "intent://start-overlay/start#Intent;scheme=matchindex;action=android.intent.action.VIEW;"
    + "category=android.intent.category.BROWSABLE;package=kr.matchindex.overlay;"
    + "S.browser_fallback_url=" + encodeURIComponent(fallback.href) + ";end";
}

export function mountAndroidOverlayChoice(container, { openWeb }) {
  const document = container.ownerDocument;
  const dialog = document.createElement("dialog");
  dialog.className = "android-overlay-choice";
  dialog.setAttribute("aria-labelledby", "android-overlay-choice-title");
  dialog.setAttribute("aria-describedby", "android-overlay-choice-description");
  dialog.innerHTML = `
    <div class="android-overlay-choice-head">
      <h2 id="android-overlay-choice-title">오버레이로 보기</h2>
      <button type="button" class="android-overlay-choice-close" aria-label="닫기">×</button>
    </div>
    <p id="android-overlay-choice-description">앱을 설치하거나 0.1.4 이상으로 업데이트하면 홈페이지에서 바로 실행할 수 있습니다.</p>
    <div class="android-overlay-choice-actions">
      <a class="android-overlay-choice-action primary" href="./downloads/matchindex-overlay-0.1.4-test.apk" download>Android 앱 설치·업데이트</a>
      <a class="android-overlay-choice-action" data-android-action="app">앱 실행 다시 시도</a>
      <button type="button" class="android-overlay-choice-action" data-android-action="web">웹 미니 보기</button>
    </div>
    <p class="android-overlay-choice-note">웹 미니 보기는 현재 탭 안에서 열립니다.</p>`;

  const appLink = dialog.querySelector('[data-android-action="app"]');
  appLink.href = androidOverlayIntent(document.location);
  dialog.querySelector(".android-overlay-choice-close").addEventListener("click", () => dialog.close());
  dialog.querySelector('[data-android-action="web"]').addEventListener("click", () => {
    dialog.close();
    openWeb();
  });
  container.append(dialog);

  return {
    open() {
      appLink.href = androidOverlayIntent(document.location);
      if (!dialog.open) dialog.showModal();
    }
  };
}
