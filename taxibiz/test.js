'use strict';
// 실행: TAXIBIZ_PASSWORD=x DATA_DIR=$(mktemp -d) node test.js
const assert = require('assert');
process.env.TAXIBIZ_PASSWORD = process.env.TAXIBIZ_PASSWORD || 'testpw';
process.env.DATA_DIR = process.env.DATA_DIR || require('fs').mkdtempSync(require('os').tmpdir() + '/tb-');
const { server } = require('./server');

(async () => {
  await new Promise((r) => server.listen(0, r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const call = (p, o = {}) => fetch(base + p, { headers: { 'Content-Type': 'application/json', ...(o.headers || {}) }, ...o });

  assert.strictEqual((await call('/api/summary?month=2026-10')).status, 401, '로그인 없이는 401');
  assert.strictEqual((await call('/api/login', { method: 'POST', body: JSON.stringify({ password: 'bad' }) })).status, 401);
  const login = await call('/api/login', { method: 'POST', body: JSON.stringify({ password: process.env.TAXIBIZ_PASSWORD }) });
  assert.strictEqual(login.status, 200);
  const cookie = login.headers.get('set-cookie').split(';')[0];
  const A = (p, method = 'GET', body) => call(p, { method, headers: { cookie }, body: body && JSON.stringify(body) });

  await A('/api/sales', 'POST', { date: '2026-10-01', shift: '주', calls: 10, trips: 12, cash: 100000, card: 200000, other: 0 });
  await A('/api/sales', 'POST', { date: '2026-10-02', shift: '주', calls: 5, trips: 6, cash: 50000, card: 50000, other: 10000 });
  await A('/api/expenses', 'POST', { date: '2026-10-01', category: '가스충전', amount: 60000 });
  await A('/api/expenses', 'POST', { date: '2026-10-01', category: '담배', amount: 9000, personal: true });
  const bad = await A('/api/sales', 'POST', { date: '10/01' });
  assert.strictEqual(bad.status, 400, '잘못된 날짜 거부');

  const s = await (await A('/api/summary?month=2026-10')).json();
  assert.strictEqual(s.revenue, 410000);
  assert.strictEqual(s.cardFee, 2500);          // 카드 250,000 × 1%
  assert.strictEqual(s.businessTotal, 60000);   // 개인지출 제외
  assert.strictEqual(s.personal, 9000);
  assert.strictEqual(s.profit, 410000 - 60000 - 2500);
  assert.strictEqual(s.available, s.profit - 9000);
  assert.strictEqual(s.workedDays, 2);

  const rows = await (await A('/api/sales?month=2026-10')).json();
  assert.strictEqual((await A(`/api/sales/${rows[0].id}`, 'DELETE')).status, 200);
  assert.strictEqual((await (await A('/api/sales?month=2026-10')).json()).length, 1);
  assert.strictEqual((await call('/../server.js')).status, 404, '경로 탈출 차단');

  console.log('모든 테스트 통과');
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
