// 🔴 업그레이드 정책 — 사장님 지시 "업그레이드도 가능토록"
//    network-first 다. 새 버전이 배포되면 **다음에 여실 때 바로** 반영된다.
//    (cache-first 로 하면 옛 화면이 계속 떠서 "업데이트가 안 된다" 가 된다)
//    캐시는 오프라인·지하철용 폴백일 뿐이다.
var C = 'lifeinfo-approval-v1';
var SHELL = ['m.html', 'manifest.json', 'approval_m.json'];

self.addEventListener('install', function (e) {
  self.skipWaiting();                       // 새 SW 를 즉시 활성화
  e.waitUntil(caches.open(C).then(function (c) { return c.addAll(SHELL).catch(function(){}); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== C; })
                        .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(function (r) {
      var cp = r.clone();
      caches.open(C).then(function (c) { c.put(e.request, cp); });
      return r;
    }).catch(function () { return caches.match(e.request); })
  );
});
