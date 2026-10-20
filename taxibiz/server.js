'use strict';
// 택시비즈 클라우드 서버: 의존성 없는 Node http 서버 + JSON 파일 저장.
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = Number(process.env.PORT) || 8080;
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const PASSWORD = process.env.TAXIBIZ_PASSWORD || '';
const SECRET = process.env.TAXIBIZ_SECRET || PASSWORD;
const PUBLIC_DIR = path.join(__dirname, 'public');

if (!PASSWORD && process.env.ALLOW_NO_AUTH !== '1') {
  console.error('TAXIBIZ_PASSWORD 환경변수를 설정하세요. (로컬 테스트만 ALLOW_NO_AUTH=1)');
  process.exit(1);
}

// 컬렉션: sales(일일영업), expenses(지출), charges(가스충전), deposits(통장입금)
const COLLECTIONS = {
  sales: ['date', 'shift', 'calls', 'trips', 'cash', 'card', 'other'],
  expenses: ['date', 'category', 'amount', 'memo', 'personal'],
  charges: ['date', 'unitPrice', 'liters', 'amount'],
  deposits: ['date', 'kind', 'amount', 'memo'],
};
const NUMERIC = new Set(['calls', 'trips', 'cash', 'card', 'other', 'amount', 'unitPrice', 'liters']);
const DEFAULT_SETTINGS = { livingCost: 2500000, monthlyFee: 1610000, workDays: 25, cardFeeRate: 0.01 };

fs.mkdirSync(DATA_DIR, { recursive: true });
const DB_FILE = path.join(DATA_DIR, 'db.json');
let db = { settings: { ...DEFAULT_SETTINGS }, sales: [], expenses: [], charges: [], deposits: [] };
try {
  db = { ...db, ...JSON.parse(fs.readFileSync(DB_FILE, 'utf8')) };
} catch (e) {
  if (e.code !== 'ENOENT') throw e;
}
function save() {
  const tmp = DB_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(db));
  fs.renameSync(tmp, DB_FILE);
}

const sign = (v) => crypto.createHmac('sha256', SECRET).update(v).digest('hex');
function authed(req) {
  if (!PASSWORD) return true;
  const m = /(?:^|;\s*)tb=([^;]+)/.exec(req.headers.cookie || '');
  if (!m) return false;
  const [exp, sig] = m[1].split('.');
  const good = sign(exp);
  return Number(exp) > Date.now() && sig && sig.length === good.length &&
    crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(good));
}

function clean(col, body) {
  const row = {};
  for (const f of COLLECTIONS[col]) {
    let v = body[f];
    if (NUMERIC.has(f)) v = Number(v) || 0;
    else if (f === 'personal') v = !!v;
    else v = String(v == null ? '' : v).slice(0, 200);
    row[f] = v;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(row.date)) throw new Error('날짜 형식은 YYYY-MM-DD 입니다.');
  return row;
}

const sum = (rows, f) => rows.reduce((a, r) => a + (r[f] || 0), 0);

function summarize(month) {
  const inMonth = (r) => r.date.startsWith(month);
  const sales = db.sales.filter(inMonth);
  const expenses = db.expenses.filter(inMonth);
  const charges = db.charges.filter(inMonth);
  const s = { ...DEFAULT_SETTINGS, ...db.settings };
  const cash = sum(sales, 'cash');
  const card = sum(sales, 'card');
  const other = sum(sales, 'other');
  const revenue = cash + card + other;
  const business = expenses.filter((e) => !e.personal);
  const personal = sum(expenses.filter((e) => e.personal), 'amount');
  const byCategory = {};
  for (const e of business) byCategory[e.category] = (byCategory[e.category] || 0) + e.amount;
  const cardFee = Math.round(card * s.cardFeeRate);
  const businessTotal = sum(business, 'amount');
  const profit = revenue - businessTotal - cardFee;
  const days = new Set(sales.map((r) => r.date)).size;
  return {
    month, revenue, cash, card, other, cardFee,
    trips: sum(sales, 'trips'), calls: sum(sales, 'calls'), workedDays: days,
    businessTotal, byCategory, personal,
    gasCharged: sum(charges, 'amount'), gasLiters: sum(charges, 'liters'),
    profit, available: profit - personal,
    // 월말 전망: 생활비는 설정값 한 곳에서만 가져온다.
    projection: days ? Math.round((profit / days) * s.workDays) - s.livingCost : null,
    settings: s,
  };
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let buf = '';
    req.on('data', (c) => { buf += c; if (buf.length > 1e6) { reject(new Error('too large')); req.destroy(); } });
    req.on('end', () => { try { resolve(buf ? JSON.parse(buf) : {}); } catch (e) { reject(e); } });
  });
}
function send(res, code, obj, headers = {}) {
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', ...headers });
  res.end(JSON.stringify(obj));
}

async function api(req, res, url) {
  const parts = url.pathname.split('/').filter(Boolean).slice(1); // /api/...
  if (parts[0] === 'login' && req.method === 'POST') {
    const { password } = await readBody(req);
    const a = Buffer.from(sign(String(password || '')));
    const b = Buffer.from(sign(PASSWORD));
    if (!PASSWORD || !crypto.timingSafeEqual(a, b)) return send(res, 401, { error: '비밀번호가 틀렸습니다.' });
    const exp = String(Date.now() + 30 * 864e5);
    return send(res, 200, { ok: true }, {
      'Set-Cookie': `tb=${exp}.${sign(exp)}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${30 * 86400}${req.headers['x-forwarded-proto'] === 'https' ? '; Secure' : ''}`,
    });
  }
  if (!authed(req)) return send(res, 401, { error: '로그인이 필요합니다.' });

  const [name, id] = parts;
  if (name === 'summary') {
    const month = url.searchParams.get('month') || '';
    if (!/^\d{4}-\d{2}$/.test(month)) return send(res, 400, { error: 'month=YYYY-MM' });
    return send(res, 200, summarize(month));
  }
  if (name === 'settings') {
    if (req.method === 'PUT') {
      const b = await readBody(req);
      for (const k of Object.keys(DEFAULT_SETTINGS)) if (b[k] !== undefined) db.settings[k] = Number(b[k]) || 0;
      save();
    }
    return send(res, 200, { ...DEFAULT_SETTINGS, ...db.settings });
  }
  if (name === 'export') return send(res, 200, db);
  if (name === 'import' && req.method === 'POST') {
    // 엑셀 가져오기: 같은 내용의 행은 건너뛰어 재실행해도 중복되지 않는다.
    const col = id;
    if (!COLLECTIONS[col]) return send(res, 404, { error: 'not found' });
    const { rows } = await readBody(req);
    if (!Array.isArray(rows) || rows.length > 5000) return send(res, 400, { error: 'rows는 5000건 이하 배열' });
    const key = (r) => COLLECTIONS[col].map((f) => r[f]).join('\u0001');
    const seen = new Set(db[col].map(key));
    let added = 0, duplicate = 0, invalid = 0;
    for (const raw of rows) {
      let row;
      try { row = clean(col, raw); } catch { invalid++; continue; }
      if (seen.has(key(row))) { duplicate++; continue; }
      seen.add(key(row));
      db[col].push({ id: crypto.randomUUID(), ...row });
      added++;
    }
    if (added) save();
    return send(res, 200, { added, duplicate, invalid });
  }
  if (!COLLECTIONS[name]) return send(res, 404, { error: 'not found' });

  if (req.method === 'GET') {
    const month = url.searchParams.get('month');
    const rows = db[name].filter((r) => !month || r.date.startsWith(month));
    return send(res, 200, rows.sort((a, b) => a.date.localeCompare(b.date)));
  }
  if (req.method === 'POST') {
    const row = { id: crypto.randomUUID(), ...clean(name, await readBody(req)) };
    db[name].push(row);
    save();
    return send(res, 201, row);
  }
  if (req.method === 'DELETE' && id) {
    const before = db[name].length;
    db[name] = db[name].filter((r) => r.id !== id);
    if (db[name].length === before) return send(res, 404, { error: 'not found' });
    save();
    return send(res, 200, { ok: true });
  }
  return send(res, 405, { error: 'method not allowed' });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  try {
    if (url.pathname === '/healthz') return send(res, 200, { ok: true });
    if (url.pathname.startsWith('/api/')) return await api(req, res, url);
    const file = path.join(PUBLIC_DIR, url.pathname === '/' ? 'index.html' : url.pathname);
    if (!file.startsWith(PUBLIC_DIR + path.sep)) { res.writeHead(403); return res.end(); }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); return res.end('Not found'); }
      const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
      res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
      res.end(data);
    });
  } catch (e) {
    send(res, 400, { error: e.message });
  }
});

if (require.main === module) {
  server.listen(PORT, () => console.log(`택시비즈 서버 시작: http://localhost:${PORT}`));
}
module.exports = { server, summarize };
