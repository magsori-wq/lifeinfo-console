/* cp_clip.js — CP(센트럴포인트) 공용 클립보드 복사 함수 (2026-09-11 신설)
 *
 * 🔴 왜 만들었나 (사장님: "복붙이 안되고")
 *   navigator.clipboard 는 **https 또는 localhost(보안 컨텍스트)** 에서만 존재한다.
 *   그 밖(같은 도메인의 http, file:// 등)에서 열면 navigator.clipboard 자체가
 *   undefined 라 `navigator.clipboard.writeText(...)` 를 그대로 부르면
 *   **동기적으로 TypeError 가 나서 그 클릭 핸들러가 조용히 죽는다.**
 *   오류도 안 뜨고 토스트도 안 뜬다 — 사장님에게는 "복사가 안 된다"로만 보인다.
 *
 *   실측(2026-09-11 이부장): webapp/*.html 10개 화면에서 navigator.clipboard 를
 *   직접 부르는 곳이 38곳, 그중 실패 시 아무것도 안 보여주는 곳(무음 실패)이 대부분.
 *
 * 사용법:
 *   cpCopy(text)                      // 성공/실패 알림은 기본 처리(alert)
 *   cpCopy(text, onOk)                // 성공 시 콜백(토스트 등), 실패는 기본 alert
 *   cpCopy(text, onOk, onFail)        // 실패까지 직접 처리(카드 안내 등)
 *
 * 🔴 onFail 을 넘겨도 **완전히 무음으로 두지 마라** — 이 파일의 기본 onFail 처럼
 *    최소한 alert 한 줄은 띄운다. 그래야 "복사가 왜 안 되지"를 사장님이 직접
 *    겪지 않는다.
 */
(function (global) {
  'use strict';

  function execFallback(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.top = '0';
    ta.style.left = '0';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      ta.setSelectionRange(0, ta.value.length);
    } catch (e) { /* 모바일 일부 브라우저 */ }
    var ok = false;
    try {
      ok = document.execCommand('copy');
    } catch (e) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  function defaultFail() {
    try {
      alert('복사 실패 — 직접 선택해 Ctrl+C(길게 눌러 복사)로 복사해 주세요.');
    } catch (e) { /* alert 도 막힌 임베드 환경 */ }
  }

  /**
   * @param {string} text 복사할 문자열
   * @param {function} [onOk] 성공 콜백
   * @param {function} [onFail] 실패 콜백 — 생략하면 alert 로 알린다(무음 금지)
   */
  global.cpCopy = function cpCopy(text, onOk, onFail) {
    text = text == null ? '' : String(text);
    onOk = typeof onOk === 'function' ? onOk : function () {};
    onFail = typeof onFail === 'function' ? onFail : defaultFail;

    var hasSecureClipboard =
      typeof navigator !== 'undefined' &&
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === 'function' &&
      typeof window !== 'undefined' &&
      window.isSecureContext;

    if (hasSecureClipboard) {
      navigator.clipboard.writeText(text).then(onOk, function () {
        if (execFallback(text)) onOk();
        else onFail();
      });
    } else {
      if (execFallback(text)) onOk();
      else onFail();
    }
  };
})(window);
