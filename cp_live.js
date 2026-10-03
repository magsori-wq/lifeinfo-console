/* webapp/cp_live.js — CP 공통: 기준 시각 배지 + 선택적 재조회 주기
 * (CP 마이그레이션 3단계, 2026-10-03 — docs/CP_마이그레이션_계획_20261003.md 3단계)
 *
 * 왜: 화면마다 "이 값이 언제 것인가"가 없어서 낡은 화면을 못 알아챘다
 * (adsense.html 이 09-01 상태로 32일 멈춰 있었는데 아무도 몰랐다 — CP_화면지도_20261003.md).
 * approval.html 의 서버 찾기 타임아웃·_userBusy 미루기 패턴(approval.html:506-527)을
 * 공통화해 다른 화면도 쓸 수 있게 했다. 판정 로직을 새로 만들지 않는다 — 이미 있는
 * 파이썬 결과(JSON 의 generated/updated 필드, 또는 bake 때 박아 넣은 meta 태그)를 읽기만 한다.
 *
 * 사용법 (화면마다 <body> 어딘가에 한 줄):
 *   <script src="cp_live.js"></script>
 *   <script>window.CPLive && CPLive.init({ timestamp:{json:'adsense_plan.json', field:'updated'}, staleHours:24 });</script>
 *
 * timestamp 소스 — 하나만 쓴다. 아무것도 안 주면 meta 태그 → 없으면 현재 페이지 Last-Modified.
 *   {meta:'cp-generated'}          — <meta name="cp-generated" content="ISO 시각">
 *   {json:'url', field:'a.b.c'}    — JSON 을 받아 점표기 필드에서 날짜/시각 문자열을 읽는다
 *   {text:'#sel', re:/.../}        — DOM 요소 textContent 에서 정규식 1번째 그룹으로 날짜 추출
 *   {head:'url'}                   — HEAD 요청의 Last-Modified 헤더(기본: 현재 페이지)
 *
 * 🔴 탭을 오래 열어 두면 "1분 전"이 거짓이 된다 — 그래서 첫 읽기 값을 **고정(캐시)**하고,
 * 1분마다는 그 고정값 기준으로 경과시간 문구만 다시 그린다(네트워크 없음). 데이터 소스가
 * 실제로 바뀌었는지는 5분마다 **따로** 재확인해 바뀌었으면 "🔄 새 버전 있음"으로 알린다 —
 * 그 자리에서 몰래 "방금 갱신"으로 보이게 하지 않는다(화면 내용은 그대로인데 배지만 초록이면
 * 그게 더 나쁜 거짓이다).
 *
 * poll (선택) — 화면이 스스로 다시 그릴 수 있으면, 데이터 URL 을 주기적으로 다시 읽어 onData 로
 * 돌려준다. 성공하면 캐시된 기준 시각도 함께 갱신해 "새 버전 있음" 표시를 지운다.
 * 사용자가 입력 중(선택·포커스·최근 45초 안 상호작용)이면 미룬다 — approval.html 과 동일 기준.
 *   CPLive.init({ timestamp:{json:'x.json',field:'baked_at'},
 *                 poll:{ url:'x.json', intervalMs:300000, tsField:'baked_at', onData:function(d){...} } });
 */
(function (global) {
  "use strict";

  function dig(obj, path) {
    if (!obj) return null;
    var parts = String(path || "").split(".");
    var v = obj;
    for (var i = 0; i < parts.length; i++) {
      if (v == null) return null;
      v = v[parts[i]];
    }
    return v;
  }

  // 날짜/시각 문자열을 읽는다. 시각을 지어내지 않는다 —
  //  · "YYYY-MM-DD" (날짜만) → 로컬 자정으로 둔다(UTC 로 읽으면 9시간이 생겨난다 —
  //    2026-10-03 adsense.html 실측: new Date('2026-10-03') 가 "오전 9:00:00"을 지어냈다).
  //  · "YYYY-MM-DD HH:MM:SS" → 공백을 T 로 바꿔 로컬시각으로 확정 파싱(브라우저 관용 파싱에 안 기댐).
  function parseDate(v) {
    if (!v) return null;
    if (v instanceof Date) return isNaN(v.getTime()) ? null : { d: v, dateOnly: false };
    var s = String(v).trim();
    var dOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (dOnly) {
      var d0 = new Date(+dOnly[1], +dOnly[2] - 1, +dOnly[3]);
      return isNaN(d0.getTime()) ? null : { d: d0, dateOnly: true };
    }
    var spaced = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}(:\d{2})?)$/.exec(s);
    if (spaced) s = spaced[1] + "T" + spaced[2];
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : { d: d, dateOnly: false };
  }

  function fmtAgo(ms) {
    if (ms < 0) ms = 0;
    var h = ms / 3600000;
    if (h < 1) return Math.max(1, Math.round(ms / 60000)) + "분 전";
    if (h < 48) return Math.round(h) + "시간 전";
    return Math.round(h / 24) + "일 전";
  }

  // 배지 글자는 늘 "절대 시각 + 상대 시각"을 함께 보인다(title 은 pointer-events:none 때문에
  // 호버가 안 먹는다 — 폰에서는 애초에 호버가 없다. 보이는 글자에 적는다).
  function fmtBadgeMain(parsed, ageMs) {
    var ts = parsed.d;
    if (parsed.dateOnly) {
      var md = (ts.getMonth() + 1) + "-" + String(ts.getDate()).padStart(2, "0");
      if (ageMs < 86400000) return md + " 기준(오늘)";
      return md + " 기준 · " + Math.round(ageMs / 86400000) + "일 전";
    }
    var hhmm = ts.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
    return hhmm + " 기준 · " + fmtAgo(ageMs);
  }

  // ---- 기준 시각 읽기 — 소스 하나만 본다(우선순위: meta > json > text > head) ----
  function readTimestamp(cfg) {
    cfg = cfg || {};
    try {
      if (cfg.meta) {
        var m = document.querySelector('meta[name="' + cfg.meta + '"]');
        var p1 = m ? parseDate(m.getAttribute("content")) : null;
        return Promise.resolve({ parsed: p1, src: "meta:" + cfg.meta });
      }
      if (cfg.json) {
        var url = cfg.json + (cfg.json.indexOf("?") >= 0 ? "&" : "?") + "t=" + Date.now();
        return fetch(url)
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (!d) return { parsed: null, src: "json-fail:" + cfg.json };
            var raw = cfg.field ? dig(d, cfg.field) : (d.generated || d.updated || d.at || d.baked_at);
            return { parsed: parseDate(raw), src: "json:" + cfg.json };
          })
          .catch(function () { return { parsed: null, src: "json-error:" + cfg.json }; });
      }
      if (cfg.text) {
        var el = document.querySelector(cfg.text);
        if (!el) return Promise.resolve({ parsed: null, src: "text-missing:" + cfg.text });
        var re = cfg.re || /(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?|\d{4}-\d{2}-\d{2})/;
        var mm = re.exec(el.textContent || "");
        return Promise.resolve({ parsed: mm ? parseDate(mm[1]) : null, src: "text:" + cfg.text });
      }
      var metaDefault = document.querySelector('meta[name="cp-generated"]');
      if (metaDefault) {
        return Promise.resolve({ parsed: parseDate(metaDefault.getAttribute("content")), src: "meta:cp-generated(auto)" });
      }
      var headUrl = cfg.head || location.href;
      return fetch(headUrl, { method: "HEAD", cache: "no-store" })
        .then(function (r) {
          var lm = r.headers.get("Last-Modified");
          return { parsed: lm ? { d: new Date(lm), dateOnly: false } : null, src: "head:" + headUrl };
        })
        .catch(function () { return { parsed: null, src: "head-error:" + headUrl }; });
    } catch (e) {
      return Promise.resolve({ parsed: null, src: "error" });
    }
  }

  // 🔴 "데이터가 바뀌었는가"를 다시 묻는 소스는 첫 읽기 소스와 다를 수 있다.
  //    meta·text 는 DOM 에 박힌 값이라 새로고침 전엔 **절대 안 바뀐다** — 그걸로
  //    재확인하면 영원히 "안 바뀜"만 나온다. 그래서 재확인은 "이 파일 자체가
  //    다시 구워졌는가"(HEAD의 Last-Modified)로 한다. json 소스만 같은 엔드포인트를
  //    다시 불러 재확인한다(그게 더 정확하고, 이미 네트워크 요청이니 공짜다).
  function recheckCfg(tsCfg) {
    if (tsCfg.json) return { json: tsCfg.json, field: tsCfg.field };
    return { head: tsCfg.head || location.href };
  }

  // ---- 다크/라이트 판정 — 배지가 어느 화면에서도 읽히게 ----
  function isDarkBg() {
    try {
      var c = getComputedStyle(document.body).backgroundColor || "";
      var m = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(c);
      if (!m) return false;
      var r = +m[1], g = +m[2], b = +m[3];
      return (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.5;
    } catch (e) {
      return false;
    }
  }

  // ---- 배지 엘리먼트 ----
  function ensureBadgeEl() {
    var el = document.getElementById("cp-live-badge");
    if (el) return el;
    el = document.createElement("div");
    el.id = "cp-live-badge";
    el.style.cssText =
      "position:fixed;top:8px;right:10px;z-index:99999;" +
      'font:12px/1.4 -apple-system,"Malgun Gothic",sans-serif;' +
      "padding:4px 11px;border-radius:20px;font-weight:600;" +
      "box-shadow:0 2px 6px rgba(0,0,0,.25);pointer-events:none;" +
      "transition:opacity .2s;white-space:nowrap;max-width:62vw;overflow:hidden;text-overflow:ellipsis";
    document.body.appendChild(el);
    return el;
  }

  function paint(st) {
    var el = ensureBadgeEl();
    var dark = isDarkBg();
    if (!st.parsed) {
      el.textContent = "⏱ 기준 시각 확인 못 함";
      el.style.background = dark ? "#1b2740" : "#eef1f5";
      el.style.color = dark ? "#9fb0d0" : "#5b6b85";
      el.style.border = "1px solid " + (dark ? "#2a3a5e" : "#d7dde6");
      el.title = "소스: " + (st.src || "-");
      return;
    }
    var ageMs = Date.now() - st.parsed.d.getTime();
    var stale = ageMs > st.staleHours * 3600000;
    var main = fmtBadgeMain(st.parsed, ageMs);
    if (st.newerAvailable) {
      // 데이터는 더 새것이 서버에 있는데 이 화면은 아직 그걸 반영 못 했다 — 가장 강한 신호.
      el.textContent = "🔄 새 버전 있음 · 새로고침 (" + main + ")";
      el.style.background = dark ? "#132a44" : "#e6f0ff";
      el.style.color = dark ? "#7fc1ff" : "#1f5fbf";
      el.style.border = "1px solid " + (dark ? "#1e4a73" : "#bcd7ff");
    } else if (stale) {
      el.textContent = "🟡 낡음 · " + main;
      el.style.background = dark ? "#3a2f12" : "#fff4da";
      el.style.color = dark ? "#f0c75e" : "#8a5a00";
      el.style.border = "1px solid " + (dark ? "#6b5420" : "#eccb7a");
    } else {
      el.textContent = "🕐 " + main;
      el.style.background = dark ? "#16203a" : "#eef6f1";
      el.style.color = dark ? "#8fd6a8" : "#2f7a4f";
      el.style.border = "1px solid " + (dark ? "#2a3a5e" : "#cfe6d8");
    }
    el.title = "기준 시각: " + st.parsed.d.toLocaleString("ko-KR") + " (" + st.src + ")";
  }

  // ---- 사용자 바쁨 판정 (approval.html:514-523 과 동일 기준) ----
  var lastTouch = 0;
  ["scroll", "mousedown", "touchstart", "keydown", "copy", "selectionchange", "wheel"].forEach(function (ev) {
    document.addEventListener(ev, function () { lastTouch = Date.now(); }, { passive: true, capture: true });
  });
  function userBusy() {
    try {
      if (String(window.getSelection() || "").length > 0) return true;
    } catch (e) {}
    var a = document.activeElement;
    if (a && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) return true;
    return Date.now() - lastTouch < 45000;
  }

  var CPLive = {
    _badgeTimer: null,
    _recheckTimer: null,
    _pollTimer: null,
    _state: null,

    init: function (opts) {
      opts = opts || {};
      var tsCfg = opts.timestamp || {};
      var st = { parsed: null, src: "", staleHours: opts.staleHours == null ? 6 : opts.staleHours, newerAvailable: false };
      this._state = st;

      // 첫 읽기 — 이 값을 "화면이 지금 보여주는 내용의 기준 시각"으로 고정한다.
      readTimestamp(tsCfg).then(function (res) {
        st.parsed = res.parsed; st.src = res.src; st.newerAvailable = false;
        paint(st);
      });

      // 1분마다 경과시간 문구만 다시 그린다 — 네트워크 요청 없음(고정값 기준 재계산뿐).
      if (this._badgeTimer) clearInterval(this._badgeTimer);
      this._badgeTimer = setInterval(function () { paint(st); }, 60000);

      // 5분마다 "진짜 바뀌었는지"만 따로 확인한다 — 바뀌었으면 배지만 바꾸고
      // 화면 내용은 그대로 둔다(화면이 스스로 못 그리면 거짓으로 갱신된 척 안 한다).
      var rcfg = recheckCfg(tsCfg);
      if (this._recheckTimer) clearInterval(this._recheckTimer);
      this._recheckTimer = setInterval(function () {
        readTimestamp(rcfg).then(function (res) {
          if (res.parsed && st.parsed && res.parsed.d.getTime() > st.parsed.d.getTime() + 1000) {
            st.newerAvailable = true;
            paint(st);
          }
        });
      }, 5 * 60000);

      if (opts.poll) this.poll(opts.poll, st);
      return this;
    },

    // 데이터 URL 을 주기적으로 다시 읽어 onData 로 돌려준다(화면이 스스로 다시 그릴 수 있을 때만 쓴다).
    // opts.tsField 를 주면 성공할 때마다 배지의 기준 시각도 그 값으로 갱신한다
    // (= "새 버전 있음" 표시가 실제로 반영된 뒤 지워진다 — 거짓 갱신이 아니다).
    // 사용자가 입력/선택 중이면 이번 주기를 건너뛴다.
    poll: function (opts, st) {
      if (!opts || !opts.url || !opts.onData) return;
      var interval = opts.intervalMs || 60000;
      function run() {
        if (userBusy()) return;
        var url = opts.url + (opts.url.indexOf("?") >= 0 ? "&" : "?") + "t=" + Date.now();
        fetch(url)
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (d == null) return;
            opts.onData(d);
            if (opts.tsField && st) {
              var p = parseDate(dig(d, opts.tsField));
              if (p) { st.parsed = p; st.newerAvailable = false; paint(st); }
            }
          })
          .catch(function () {});
      }
      if (this._pollTimer) clearInterval(this._pollTimer);
      this._pollTimer = setInterval(run, interval);
      return this;
    },

    _debug: { readTimestamp: readTimestamp, parseDate: parseDate, userBusy: userBusy, isDarkBg: isDarkBg }
  };

  global.CPLive = CPLive;
})(window);
