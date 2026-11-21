function androidIntent(location) {
  const fallback = new URL(location.href);
  fallback.searchParams.set("overlay", "android");
  return "intent://overlay#Intent;scheme=matchindex;package=kr.matchindex.overlay;"
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
    <p id="android-overlay-choice-description">라이브스코어 등 다른 앱 위에 분석창을 띄우려면 매치인덱스 Android 앱을 사용하세요.</p>
    <div class="android-overlay-choice-actions">
      <a class="android-overlay-choice-action primary" data-android-action="app">앱 열기</a>
      <a class="android-overlay-choice-action" href="./downloads/matchindex-overlay-0.1.2-test.apk" download>테스트 APK 다운로드</a>
      <button type="button" class="android-overlay-choice-action" data-android-action="web">웹 미니 보기</button>
    </div>
    <p class="android-overlay-choice-note">웹 미니 보기는 현재 탭 안에서 열립니다.</p>`;

  const appLink = dialog.querySelector('[data-android-action="app"]');
  appLink.href = androidIntent(document.location);
  dialog.querySelector(".android-overlay-choice-close").addEventListener("click", () => dialog.close());
  dialog.querySelector('[data-android-action="web"]').addEventListener("click", () => {
    dialog.close();
    openWeb();
  });
  container.append(dialog);

  return {
    open() {
      appLink.href = androidIntent(document.location);
      if (!dialog.open) dialog.showModal();
    }
  };
}
