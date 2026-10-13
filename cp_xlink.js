/* webapp/cp_xlink.js — 작업지시 ↔ 보고 연결 + 즉시 반영 (2026-10-08 사장님 지시
 * "보고탭과 작업지시탭이 상호 유기적으로 원활하게 반영하고 화면 즉시반영하도록")
 *
 *  CPX.go(tab, bid)      — CP 안에서 다른 탭(orders|reports)으로 넘어가 그 배치 카드로 간다
 *  CPX.live(urls)        — urls(json 등)의 Last-Modified 가 바뀌면 5초 안에 다시 그린다.
 *                          스크롤 위치·펼친 <details> 는 보존한다.
 *  CPX.focus(sel)        — 주소 #b-<bid> 가 있으면 그 카드들을 강조하고 감싼 <details> 를 연다
 * 판정 로직은 없다 — 화면 이동과 새로고침만 한다.
 */
(function () {
  var KEY = 'cpx:' + location.pathname;
  function openIds() {
    var a = [];
    document.querySelectorAll('details[open]').forEach(function (d, i) { a.push(d.dataset.k || ('i' + i)); });
    return a;
  }
  function save() {
    try { sessionStorage.setItem(KEY, JSON.stringify({ y: window.scrollY, open: openIds(),
      cols: Array.prototype.map.call(document.querySelectorAll('.colbody'), function (c) { return c.scrollTop; }) })); } catch (e) {}
  }
  function restore() {
    var s; try { s = JSON.parse(sessionStorage.getItem(KEY) || 'null'); sessionStorage.removeItem(KEY); } catch (e) {}
    if (!s) return;
    var ds = document.querySelectorAll('details');
    ds.forEach(function (d, i) { if (s.open.indexOf(d.dataset.k || ('i' + i)) >= 0) d.open = true; });
    var cs = document.querySelectorAll('.colbody');
    (s.cols || []).forEach(function (y, i) { if (cs[i]) cs[i].scrollTop = y; });
    window.scrollTo(0, s.y || 0);
  }
  // 🔴 지시 상태 판정은 여기 한 곳뿐이다(작업지시·보고 두 화면이 같이 쓴다 — 2026-10-08).
  // 🔴 2026-10-13 사장님 "안읽음·막힘·진행중·완료·끝남을 명확히, 완료는 줄긋기" — 다섯 상태.
  //    완료(done)  = 받는 쪽이 끝냈다고 보고 · 이부장 확인 전  → 줄긋기
  //    끝남(closed) = 이부장이 확인까지 마침(confirmed_at ≥ order_at) → 줄긋기 + 흐리게
  //    막힘 = 항목 blocked 또는 지시 뒤 마지막 보고가 [blocked]·막힘
  //    Aside(배치 하나에 지시가 번호로 쌓임)는 data/aside_orders.json(webapp 사본)의 그 번호 상태로 판정한다.
  function status(b, s, ao) {
    s = s || {}; b = b || {};
    if (b.frozen) return 'frozen';   // 이부장이 중단·통합한 지시(frozen_note 에 이유) — 열린 일이 아니다(2026-10-13 실측 8건)
    var oa = String(b.order_at || '').slice(0, 16);
    var conf = String(b.confirmed_at || '').slice(0, 16);
    var m = String(b.order || '').match(/지시 #(\d{1,3})/);
    if (ao && m && /aside/i.test(String(b.owner || '') + String(b.title || ''))) {
      var o = (ao.orders || {})[m[1]];
      if (!o) return 'unread';
      if (o.state === 'done') return o.confirmed_at ? 'closed' : 'done';
      if (o.state === 'blocked') return 'block';
      return 'doing';
    }
    var items = b.items || [], done = 0, blocked = false;
    items.forEach(function (it) { if (it.state === 'done' || it.state === 'skip') done++; if (it.state === 'blocked') blocked = true; });
    if (items.length && done === items.length) return (conf && conf >= oa) ? 'closed' : 'done';
    var lr = String(s.last_report || '').slice(0, 16);
    if (blocked || (lr && lr >= oa && /\[blocked\]|막힘|⛔/.test(String(s.last_what || '')))) return 'block';
    if ((s.last_read && (!oa || s.last_read >= oa)) || (lr && lr > oa)) return 'doing';
    return 'unread';
  }
  var CHIP = { unread: ['c-unread', '⏳ 안 읽음'], doing: ['c-doing', '👀 진행 중'], block: ['c-block', '⛔ 막힘'],
               done: ['c-done', '✅ 완료(확인 전)'], closed: ['c-closed', '🏁 끝남'], frozen: ['c-closed', '🧊 중단·통합'] };
  var CPX = {
    status: status, CHIP: CHIP,
    go: function (tab, bid) {
      var hash = bid ? '#b-' + encodeURIComponent(bid) : '';
      try {
        var P = parent.document;
        var btn = P.querySelector('nav button[data-t="' + tab + '"]');
        var f = P.getElementById('f_' + tab);
        if (btn) btn.click();
        if (f) {
          var base = f.dataset.base || String(f.getAttribute('data-src') || '').split('?')[0];
          f.src = base + '?t=' + Date.now() + hash;
        }
        if (!btn && !f) throw 0;
      } catch (e) { location.href = (tab === 'orders' ? 'orders.html' : 'reports.html') + hash; }
    },
    live: function (urls, onChange) {
      var tags = {};
      function look() {
        urls.forEach(function (u) {
          fetch(u + '?v=' + Date.now(), { method: 'HEAD', cache: 'no-store' }).then(function (r) {
            if (!r.ok) return;
            var t = (r.headers.get('Last-Modified') || '') + '/' + (r.headers.get('Content-Length') || '');
            if (tags[u] === undefined) { tags[u] = t; return; }
            if (t !== tags[u]) { tags[u] = t; save(); if (onChange) onChange(); else location.reload(); }
          }).catch(function () {});
        });
      }
      look(); setInterval(look, 5000);
    },
    restore: restore,
    focus: function (sel) {
      var m = location.hash.match(/^#b-(.+)$/); if (!m) return;
      var bid = decodeURIComponent(m[1]);
      var hits = document.querySelectorAll(sel + '[data-bid="' + bid.replace(/"/g, '') + '"]');
      hits.forEach(function (el) {
        el.style.outline = '3px solid #ffd479'; el.style.outlineOffset = '2px';
        var p = el.parentElement; while (p) { if (p.tagName === 'DETAILS') p.open = true; p = p.parentElement; }
      });
      if (hits[0]) setTimeout(function () { hits[0].scrollIntoView({ block: 'center' }); }, 60);
    }
  };
  window.CPX = CPX;
})();
